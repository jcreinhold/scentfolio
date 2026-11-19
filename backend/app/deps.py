"""Open the database at startup and expose the session factory to routes."""

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.db import ensure_schema, make_engine, make_sessionmaker


def open_database(url: str) -> tuple[Engine, sessionmaker[Session]]:
    """Return an engine and session factory after the schema is ready."""
    engine = make_engine(url)
    try:
        ensure_schema(engine, models.Base.metadata)
        return engine, make_sessionmaker(engine)
    except BaseException:
        engine.dispose()
        raise


async def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Return the app's factory so each handler can open its own short session."""
    return request.app.state.session_factory
