from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app("sqlite:///:memory:")) as test_client:
        yield test_client


def _create(client, name="Sauvage", house="Dior", families=("Fresh",)):
    return client.post(
        "/api/perfumes",
        json={
            "name": name,
            "house": house,
            "scent_families": list(families),
            "formats": ["full"],
            "notes": [{"name": "bergamot", "tier": "top"}],
        },
    )


def test_create_and_get_perfume(client):
    r = _create(client, families=("Gourmand", "Woody"))
    assert r.status_code == HTTPStatus.CREATED
    pid = r.json()["id"]
    got = client.get(f"/api/perfumes/{pid}")
    assert got.json()["notes"][0]["name"] == "bergamot"
    assert got.json()["scent_families"] == ["Gourmand", "Woody"]


def test_search_by_note(client):
    _create(client)
    r = client.get("/api/perfumes", params={"q": "bergamot"})
    assert [p["name"] for p in r.json()] == ["Sauvage"]


def test_collection_paging_reports_matching_count_and_orders_before_slice(client):
    for name in ("Zeta", "Alpha", "Mid"):
        _create(client, name=name)
    _create(client, name="Unmatched", families=("Green",))

    page = client.get(
        "/api/perfumes",
        params={"limit": 1, "offset": 1, "sort": "name", "family": "Fresh"},
    )
    assert page.status_code == HTTPStatus.OK
    assert page.headers["X-Total-Count"] == "3"
    assert [perfume["name"] for perfume in page.json()] == ["Mid"]


def test_unknown_note_returns_not_found(client):
    response = client.get("/api/notes/missing")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Note not found"}


def test_note_name_with_slash_round_trips(client):
    created = client.post(
        "/api/perfumes",
        json={"name": "Accord", "notes": [{"name": "tea/rose", "tier": "heart"}]},
    )
    assert created.status_code == HTTPStatus.CREATED
    response = client.get("/api/notes/tea%2Frose")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "tea/rose"


def test_cross_origin_browser_write_cannot_change_collection(client):
    response = client.post(
        "/api/perfumes",
        headers={"Origin": "https://other.example"},
        json={"name": "Outside the collection"},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert client.get("/api/perfumes").json() == []


def test_export_csv(client):
    _create(client, name="Owned", families=("Fresh", "Woody"))
    client.post(
        "/api/perfumes",
        json={
            "name": "Wanted",
            "house": "H",
            "status": "saved",
            "notes": [{"name": "rose", "tier": "heart"}],
        },
    )
    r = client.get("/api/perfumes/export.csv")
    assert r.status_code == HTTPStatus.OK
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0] == (
        "name,status,house,perfumer,year,families,formats,"
        "top_notes,heart_notes,base_notes,description,impressions"
    )
    assert any(
        row.startswith("Owned,collection,") and "Fresh; Woody" in row
        for row in lines[1:]
    )
    # status filter narrows the export
    saved = client.get("/api/perfumes/export.csv", params={"status": "saved"}).text
    assert "Wanted" in saved and "Owned" not in saved


def test_csv_neutralizes_formula_like_text(client):
    _create(client, name="=1")
    response = client.get("/api/perfumes/export.csv")
    assert response.status_code == HTTPStatus.OK
    assert response.text.splitlines()[1].startswith("'=1,collection,")


def test_status_filter_and_move(client):
    _create(client, name="Owned")
    client.post(
        "/api/perfumes",
        json={
            "name": "Wanted",
            "house": "H",
            "status": "saved",
            "notes": [{"name": "bergamot", "tier": "top"}],
        },
    )
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
    assert r.status_code == HTTPStatus.OK
    assert [p["name"] for p in r.json()["perfumes"]] == ["Sauvage"]


def test_insights_endpoints(client):
    _create(client)
    assert client.get("/api/insights/notes").status_code == HTTPStatus.OK
    assert client.get("/api/insights/families").status_code == HTTPStatus.OK
    assert client.get("/api/insights/similar").status_code == HTTPStatus.OK


def test_update_impressions(client):
    pid = _create(client).json()["id"]
    r = client.patch(f"/api/perfumes/{pid}", json={"my_impressions": "Great!"})
    assert r.json()["my_impressions"] == "Great!"


def test_delete_perfume(client):
    pid = _create(client).json()["id"]
    r = client.delete(f"/api/perfumes/{pid}")
    assert r.status_code == HTTPStatus.NO_CONTENT
    assert client.get(f"/api/perfumes/{pid}").status_code == HTTPStatus.NOT_FOUND


def test_delete_missing_perfume_returns_404(client):
    assert client.delete("/api/perfumes/999").status_code == HTTPStatus.NOT_FOUND
