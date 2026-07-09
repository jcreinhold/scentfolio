from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(url: str = "sqlite:///scentfolio.db"):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)

def make_sessionmaker(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
