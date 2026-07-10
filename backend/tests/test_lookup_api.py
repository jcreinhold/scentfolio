import pytest
from fastapi.testclient import TestClient
from app.main import app, get_session, get_lookup, get_note_enricher, get_family_classifier
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
                     scent_families=["Chypre"],
                     notes=[NoteInput(name="bergamot", tier="top")]),
                     confidence="high")
    def _fake_enrich(names):
        return {n: {"description": f"{n} smells lovely.", "origin": "natural",
                    "production": f"{n} is harvested carefully.",
                    "compounds": "", "sourcing": "Grasse", "proprietary_to": ""} for n in names}
    def _fake_classify(name, house, notes):
        return ["Gourmand", "Green"]
    app.dependency_overrides[get_session] = _sess
    app.dependency_overrides[get_lookup] = lambda: _fake_lookup
    app.dependency_overrides[get_note_enricher] = lambda: _fake_enrich
    app.dependency_overrides[get_family_classifier] = lambda: _fake_classify
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

def test_enrich_missing_notes_fills_and_returns_count(client):
    # Adding a perfume creates the "bergamot" note with blank enrichment.
    client.post("/api/perfumes", json={"name": "Aventus", "house": "Creed",
                "notes": [{"name": "bergamot", "tier": "top"}]})
    r = client.post("/api/notes/enrich-missing")
    assert r.status_code == 200
    assert r.json()["updated"] == 1

    notes = {n["name"]: n for n in client.get("/api/notes").json()}
    assert notes["bergamot"]["description"] == "bergamot smells lovely."
    assert notes["bergamot"]["origin"] == "natural"
    assert notes["bergamot"]["production"] == "bergamot is harvested carefully."
    assert notes["bergamot"]["sourcing"] == "Grasse"

def test_reclassify_overwrites_families_and_returns_count(client):
    client.post("/api/perfumes", json={"name": "Milk", "house": "Snif",
                "scent_families": ["Woody"], "notes": [{"name": "milk", "tier": "base"}]})
    r = client.post("/api/perfumes/reclassify")
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    p = client.get("/api/perfumes").json()[0]
    assert p["scent_families"] == ["Gourmand", "Green"]  # from the fake classifier

def test_list_notes_includes_enrichment_fields(client):
    client.post("/api/perfumes", json={"name": "X", "house": "Y",
                "notes": [{"name": "rose", "tier": "heart"}]})
    notes = client.get("/api/notes").json()
    assert all({"description", "origin", "production", "compounds", "sourcing",
                "proprietary_to"} <= n.keys() for n in notes)
