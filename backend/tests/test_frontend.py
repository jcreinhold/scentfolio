from http import HTTPStatus

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.frontend import serve_frontend


@pytest.fixture
def client(tmp_path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Scentfolio</title>")
    (dist / "favicon.svg").write_text("<svg/>")
    (assets / "app.js").write_text("console.log('Scentfolio')")
    outside = tmp_path / "private.txt"
    outside.write_text("Outside dist")
    (assets / "private.txt").symlink_to(outside)

    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/absent-record")
    def absent_record():
        raise HTTPException(HTTPStatus.NOT_FOUND, "No record")

    serve_frontend(app, dist)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/perfume/1", "/note/rose%20absolute%202.0"])
def test_page_refresh_and_head(client, path):
    response = client.get(path)
    assert response.status_code == HTTPStatus.OK
    assert "<title>Scentfolio</title>" in response.text

    head = client.head(path)
    assert head.status_code == HTTPStatus.OK
    assert head.headers["content-type"].startswith("text/html")
    assert head.headers["content-length"] == response.headers["content-length"]
    assert head.content == b""


def test_assets_are_served_from_dist(client):
    assert client.get("/assets/app.js").text == "console.log('Scentfolio')"
    assert client.get("/favicon.svg").text == "<svg/>"
    for path in ("/assets/missing", "/assets/private.txt", "/missing.svg"):
        assert client.get(path).status_code == HTTPStatus.NOT_FOUND


def test_existing_api_routing_has_priority(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert (
        client.get("/api/health/", follow_redirects=False).status_code
        == HTTPStatus.TEMPORARY_REDIRECT
    )
    assert client.post("/api/health").status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert client.get("/api/absent-record").json() == {"detail": "No record"}
    for path in ("/api", "/api/missing"):
        response = client.get(path)
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Not Found"}
