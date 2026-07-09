import os
from app.db import Base, make_engine, make_sessionmaker
from app import models  # noqa: F401 — register ORM tables on Base.metadata before create_all

_DB_URL = os.environ.get("SCENTFOLIO_DB_URL", "sqlite:///scentfolio.db")
_engine = make_engine(_DB_URL)
Base.metadata.create_all(_engine)
_Session = make_sessionmaker(_engine)

def get_session():
    with _Session() as s:
        yield s
