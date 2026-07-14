from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

class Base(DeclarativeBase):
    pass

def make_engine(url: str = "sqlite:///scentfolio.db"):
    if url == "sqlite:///:memory:":
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)

def make_sessionmaker(engine):
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

def ensure_schema(engine):
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if not existing:
                continue  # table doesn't exist yet (create_all handles new tables)
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
