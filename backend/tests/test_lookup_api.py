import pytest
from fastapi.testclient import TestClient
from app.main import app, get_session, get_lookup, get_note_describer
from app.db import Base, make_engine, make_sessionmaker
from app.agent import Draft
from app.schemas import PerfumeCreate, NoteInput

@pytest.fixture
def client():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    def _sess():
        with Session() as s:
            yield s
    def _fake_lookup(name: str):
        return Draft(perfume=PerfumeCreate(name="Aventus", house="Creed",
                     scent_family="Chypre",
                     notes=[NoteInput(name="bergamot", tier="top")]),
                     confidence="high")
    def _fake_describe(names):
        return {n: f"{n} smells lovely." for n in names}
    app.dependency_overrides[get_session] = _sess
    app.dependency_overrides[get_lookup] = lambda: _fake_lookup
    app.dependency_overrides[get_note_describer] = lambda: _fake_describe
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_lookup_returns_draft(client):
    r = client.post("/api/lookup", json={"name": "Aventus"})
    assert r.status_code == 200
    body = r.json()
    assert body["confidence"] == "high"
    assert body["perfume"]["name"] == "Aventus"

def test_duplicate_flag_on_create(client):
    client.post("/api/perfumes", json={"name": "Aventus", "house": "Creed", "notes": []})
    r = client.get("/api/perfumes/check-duplicate", params={"name": "Aventus", "house": "Creed"})
    assert r.json()["duplicate"] is True

def test_describe_missing_notes_fills_and_returns_count(client):
    # Adding a perfume creates the "bergamot" note with a blank description.
    client.post("/api/perfumes", json={"name": "Aventus", "house": "Creed",
                "notes": [{"name": "bergamot", "tier": "top"}]})
    r = client.post("/api/notes/describe-missing")
    assert r.status_code == 200
    assert r.json()["updated"] == 1

    notes = {n["name"]: n for n in client.get("/api/notes").json()}
    assert notes["bergamot"]["description"] == "bergamot smells lovely."

def test_list_notes_includes_description_field(client):
    client.post("/api/perfumes", json={"name": "X", "house": "Y",
                "notes": [{"name": "rose", "tier": "heart"}]})
    notes = client.get("/api/notes").json()
    assert all("description" in n for n in notes)
