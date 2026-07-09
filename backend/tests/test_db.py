from sqlalchemy import text
from app.db import Base, make_engine, make_sessionmaker

def test_engine_creates_tables_and_session_queries():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    with Session() as s:
        assert s.execute(text("SELECT 1")).scalar() == 1
