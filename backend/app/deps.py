import os
from app.db import Base, make_engine, make_sessionmaker, ensure_schema
from app import models  # noqa: F401 — register ORM tables on Base.metadata before create_all

_DB_URL = os.environ.get("SCENTFOLIO_DB_URL", "sqlite:///scentfolio.db")
_engine = make_engine(_DB_URL)
Base.metadata.create_all(_engine)
ensure_schema(_engine)  # additively add any columns missing from an older DB file
_Session = make_sessionmaker(_engine)

def get_session():
    with _Session() as s:
        yield s
