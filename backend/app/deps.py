from app.db import Base, make_engine, make_sessionmaker

_engine = make_engine()
Base.metadata.create_all(_engine)
_Session = make_sessionmaker(_engine)

def get_session():
    with _Session() as s:
        yield s
