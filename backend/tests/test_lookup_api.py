import asyncio
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.agent import Draft
from app.ai_work import AIWork
from app.api import get_ai_work, get_family_classifier, get_lookup, get_note_enricher
from app.llm import LookupError
from app.main import create_app
from app.schemas import NoteInput, PerfumeCreate


@pytest.fixture
def client():
    async def _fake_lookup(name: str):
        return Draft(
            perfume=PerfumeCreate(
                name="Aventus",
                house="Creed",
                scent_families=["Chypre"],
                notes=[NoteInput(name="bergamot", tier="top")],
            ),
            confidence="high",
        )

    async def _fake_enrich(names):
        return {
            n: {
                "description": f"{n} smells lovely.",
                "origin": "natural",
                "production": f"{n} is harvested carefully.",
                "compounds": "",
                "sourcing": "Grasse",
                "proprietary_to": "",
                "history": f"{n} has a storied past.",
            }
            for n in names
        }

    async def _fake_classify(name, house, notes):
        return ["Gourmand", "Green"]

    app = create_app("sqlite:///:memory:")
    app.dependency_overrides[get_lookup] = lambda: _fake_lookup
    app.dependency_overrides[get_note_enricher] = lambda: _fake_enrich
    app.dependency_overrides[get_family_classifier] = lambda: _fake_classify
    with TestClient(app) as test_client:
        yield test_client


def test_lookup_returns_draft(client):
    r = client.post("/api/lookup", json={"name": "Aventus"})
    assert r.status_code == HTTPStatus.OK
    body = r.json()
    assert body["confidence"] == "high"
    assert body["perfume"]["name"] == "Aventus"


def test_overloaded_lookup_leaves_health_responsive(client):
    work = AIWork(max_concurrent=1)
    entered = Event()
    release = Event()

    async def lookup(name):
        entered.set()
        await asyncio.to_thread(release.wait, 5)
        return Draft(perfume=PerfumeCreate(name=name))

    client.app.dependency_overrides[get_ai_work] = lambda: work
    client.app.dependency_overrides[get_lookup] = lambda: lookup
    with ThreadPoolExecutor(max_workers=1) as worker:
        pending = worker.submit(client.post, "/api/lookup", json={"name": "A"})
        try:
            assert entered.wait(5)
            response = client.post("/api/lookup", json={"name": "B"})
            assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
            assert response.headers["Retry-After"]
            assert client.get("/api/health").json() == {"status": "ok"}
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    ("path", "dependency"),
    [
        ("/api/notes/enrich-missing", get_note_enricher),
        ("/api/perfumes/reclassify", get_family_classifier),
    ],
)
def test_complete_maintenance_failure_has_a_safe_error(client, path, dependency):
    async def missing_provider(*_args):
        raise LookupError("Set SCENTFOLIO_LLM_API_KEY.")

    client.app.dependency_overrides[dependency] = lambda: missing_provider
    response = client.post(
        "/api/perfumes",
        json={"name": "A", "notes": [{"name": "rose", "tier": "top"}]},
    )
    assert response.status_code == HTTPStatus.CREATED
    response = client.post(path)
    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert response.json() == {"detail": "Set SCENTFOLIO_LLM_API_KEY."}


def test_duplicate_flag_on_create(client):
    client.post(
        "/api/perfumes", json={"name": "Aventus", "house": "Creed", "notes": []}
    )
    r = client.get(
        "/api/perfumes/check-duplicate", params={"name": "Aventus", "house": "Creed"}
    )
    assert r.json()["duplicate"] is True


def test_enrich_missing_notes_fills_and_returns_count(client):
    # Adding a perfume creates the "bergamot" note with blank enrichment.
    client.post(
        "/api/perfumes",
        json={
            "name": "Aventus",
            "house": "Creed",
            "notes": [{"name": "bergamot", "tier": "top"}],
        },
    )
    r = client.post("/api/notes/enrich-missing")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["updated"] == 1
    assert r.json()["remaining"] == 0

    notes = {n["name"]: n for n in client.get("/api/notes").json()}
    assert notes["bergamot"]["description"] == "bergamot smells lovely."
    assert notes["bergamot"]["origin"] == "natural"
    assert notes["bergamot"]["production"] == "bergamot is harvested carefully."
    assert notes["bergamot"]["sourcing"] == "Grasse"
    assert notes["bergamot"]["history"] == "bergamot has a storied past."


def test_reclassify_overwrites_families_and_returns_count(client):
    client.post(
        "/api/perfumes",
        json={
            "name": "Milk",
            "house": "Snif",
            "scent_families": ["Woody"],
            "notes": [{"name": "milk", "tier": "base"}],
        },
    )
    r = client.post("/api/perfumes/reclassify")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["updated"] == 1
    p = client.get("/api/perfumes").json()[0]
    assert p["scent_families"] == ["Gourmand", "Green"]  # from the fake classifier


def test_list_notes_includes_enrichment_fields(client):
    client.post(
        "/api/perfumes",
        json={"name": "X", "house": "Y", "notes": [{"name": "rose", "tier": "heart"}]},
    )
    notes = client.get("/api/notes").json()
    assert all(
        {
            "description",
            "origin",
            "production",
            "compounds",
            "sourcing",
            "proprietary_to",
            "history",
        }
        <= n.keys()
        for n in notes
    )
