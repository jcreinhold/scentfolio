import os

from app import models
from app.db import ensure_schema, make_engine, make_sessionmaker

_DB_URL = os.environ.get("SCENTFOLIO_DB_URL", "sqlite:///scentfolio.db")
_engine = make_engine(_DB_URL)
models.Base.metadata.create_all(_engine)
ensure_schema(_engine)  # additively add any columns missing from an older DB file
_Session = make_sessionmaker(_engine)


def get_session():
    with _Session() as s:
        yield s
