import pytest
from app.db import Base, make_engine, make_sessionmaker

@pytest.fixture
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    with Session() as s:
        yield s
