from sqlalchemy import text

from app.db import Base, ensure_schema, make_engine, make_sessionmaker


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
