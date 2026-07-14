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

def _create(client, name="Sauvage", house="Dior", families=("Fresh",)):
    return client.post("/api/perfumes", json={
        "name": name, "house": house, "scent_families": list(families), "formats": ["full"],
        "notes": [{"name": "bergamot", "tier": "top"}]})

def test_create_and_get_perfume(client):
    r = _create(client, families=("Gourmand", "Woody"))
    assert r.status_code == 201
    pid = r.json()["id"]
    got = client.get(f"/api/perfumes/{pid}")
    assert got.json()["notes"][0]["name"] == "bergamot"
    assert got.json()["scent_families"] == ["Gourmand", "Woody"]

def test_search_by_note(client):
    _create(client)
    r = client.get("/api/perfumes", params={"q": "bergamot"})
    assert [p["name"] for p in r.json()] == ["Sauvage"]

def test_status_filter_and_move(client):
    _create(client, name="Owned")
    client.post("/api/perfumes", json={"name": "Wanted", "house": "H", "status": "saved",
                "notes": [{"name": "bergamot", "tier": "top"}]})
    coll = client.get("/api/perfumes", params={"status": "collection"}).json()
    saved = client.get("/api/perfumes", params={"status": "saved"}).json()
    assert [p["name"] for p in coll] == ["Owned"]
    assert [p["name"] for p in saved] == ["Wanted"]

    # Move the saved one into the collection.
    wid = saved[0]["id"]
    r = client.patch(f"/api/perfumes/{wid}", json={"status": "collection"})
    assert r.json()["status"] == "collection"
    assert client.get("/api/perfumes", params={"status": "saved"}).json() == []

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

def test_delete_perfume(client):
    pid = _create(client).json()["id"]
    r = client.delete(f"/api/perfumes/{pid}")
    assert r.status_code == 204
    assert client.get(f"/api/perfumes/{pid}").status_code == 404

def test_delete_missing_perfume_returns_404(client):
    assert client.delete("/api/perfumes/999").status_code == 404
