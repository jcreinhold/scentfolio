import sqlite3

from sqlalchemy import inspect, text

from app.db import Base, ensure_schema, make_engine, make_sessionmaker
from app.deps import open_database


def test_engine_creates_tables_and_session_queries():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    with Session() as s:
        assert s.execute(text("SELECT 1")).scalar() == 1


def _note_columns(engine):
    with engine.connect() as conn:
        return {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(notes)")}


def test_ensure_schema_adds_missing_columns_idempotently():
    engine = make_engine("sqlite:///:memory:")
    # Simulate an OLD db: a notes table without origin/production.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, name VARCHAR, "
            "family VARCHAR, description TEXT DEFAULT '')"
        )
    assert "origin" not in _note_columns(engine)

    ensure_schema(engine)
    cols = _note_columns(engine)
    assert "origin" in cols and "production" in cols

    ensure_schema(engine)  # idempotent — must not raise or duplicate
    assert _note_columns(engine) == cols


def test_ensure_schema_adds_status_to_legacy_perfumes_table():
    engine = make_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE perfumes (id INTEGER PRIMARY KEY, name VARCHAR)"
        )
    ensure_schema(engine)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(perfumes)")}
    assert "status" in cols


def test_file_bootstrap_adds_note_lookup_index_and_reopens(tmp_path):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    legacy = make_engine(url)
    with legacy.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE perfume_notes (perfume_id INTEGER NOT NULL, "
            "note_id INTEGER NOT NULL, tier VARCHAR(10) NOT NULL, "
            "PRIMARY KEY (perfume_id, note_id, tier))"
        )
    legacy.dispose()

    for _ in range(2):
        engine, sessions = open_database(url)
        try:
            indexes = inspect(engine).get_indexes("perfume_notes")
            assert any(index["column_names"] == ["note_id"] for index in indexes)
            with sessions() as session:
                mode = session.scalar(text("PRAGMA journal_mode"))
            assert mode == (
                "wal" if sqlite3.sqlite_version_info >= (3, 51, 3) else "delete"
            )
        finally:
            engine.dispose()
