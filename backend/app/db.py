"""Configure SQLAlchemy connections and apply additive database upgrades."""

import sqlite3

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Share SQLAlchemy's registry and table metadata across the app's models."""


def make_engine(url: str = "sqlite:///scentfolio.db"):
    """Build an engine, sharing a single connection for in-memory SQLite."""
    if url == "sqlite:///:memory:":
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def make_sessionmaker(engine):
    """Build sessions that skip autoflush and keep loaded values after commit."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Columns added to existing tables after their initial creation. `create_all`
# only creates missing tables, never alters existing ones, and there is no
# migration tool — so this idempotent, additive step heals an older SQLite file.
_ADDED_COLUMNS = {
    "perfumes": [("status", "VARCHAR(20) DEFAULT 'collection'")],
    "notes": [
        ("origin", "VARCHAR(20) DEFAULT ''"),
        ("production", "TEXT DEFAULT ''"),
        ("compounds", "TEXT DEFAULT ''"),
        ("sourcing", "TEXT DEFAULT ''"),
        ("proprietary_to", "VARCHAR(80) DEFAULT ''"),
        ("history", "TEXT DEFAULT ''"),
        ("detail_version", "INTEGER DEFAULT 0"),
    ],
}


_MIN_WAL_VERSION = (3, 51, 3)  # SQLite's WAL-reset fix


def _enable_wal(connection: Connection) -> None:
    if sqlite3.sqlite_version_info >= _MIN_WAL_VERSION:
        for _, name, path in connection.exec_driver_sql("PRAGMA database_list"):
            if name == "main" and path:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar_one()
                break


def ensure_schema(engine: Engine, metadata: MetaData | None = None) -> None:
    """Create missing tables when metadata is supplied and upgrade SQLite files.

    SQLite startup serializes schema changes and preserves existing rows.
    """
    if engine.dialect.name != "sqlite":
        if metadata is not None:
            metadata.create_all(engine)
        return
    with engine.begin() as conn:
        _enable_wal(conn)
        # Serialize creation and upgrades even under sqlite3's legacy DDL behavior.
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        if metadata is not None:
            metadata.create_all(conn)
        for table, columns in _ADDED_COLUMNS.items():
            existing = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            if not existing:
                continue  # table doesn't exist yet (create_all handles new tables)
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        if metadata is not None:
            for table_metadata in metadata.tables.values():
                for index in table_metadata.indexes:
                    index.create(conn, checkfirst=True)
