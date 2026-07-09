import pytest
from fastapi.testclient import TestClient
from app.main import app, get_session
from app.db import Base, make_engine, make_sessionmaker

@pytest.fixture
def client():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    def _override():
        with Session() as s:
            yield s
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()

def _create(client, name="Sauvage", house="Dior", family="Fresh"):
    return client.post("/api/perfumes", json={
        "name": name, "house": house, "scent_family": family, "formats": ["full"],
        "notes": [{"name": "bergamot", "tier": "top"}]})

def test_create_and_get_perfume(client):
    r = _create(client)
    assert r.status_code == 201
    pid = r.json()["id"]
    got = client.get(f"/api/perfumes/{pid}")
    assert got.json()["notes"][0]["name"] == "bergamot"

def test_search_by_note(client):
    _create(client)
    r = client.get("/api/perfumes", params={"q": "bergamot"})
    assert [p["name"] for p in r.json()] == ["Sauvage"]

def test_note_detail_lists_perfumes(client):
    _create(client)
    r = client.get("/api/notes/bergamot")
    assert r.status_code == 200
    assert [p["name"] for p in r.json()["perfumes"]] == ["Sauvage"]

def test_insights_endpoints(client):
    _create(client)
    assert client.get("/api/insights/notes").status_code == 200
    assert client.get("/api/insights/families").status_code == 200
    assert client.get("/api/insights/similar").status_code == 200

def test_update_impressions(client):
    pid = _create(client).json()["id"]
    r = client.patch(f"/api/perfumes/{pid}", json={"my_impressions": "Great!"})
    assert r.json()["my_impressions"] == "Great!"
