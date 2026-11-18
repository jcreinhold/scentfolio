"""Regression test: the production dependency module must create its tables at
import time. This failed once because `deps` ran create_all() before the models
module was imported, so Base.metadata was empty and no tables were created.

We run in a subprocess so it exercises a fresh import of `app.deps` in isolation
(a same-process test wouldn't catch the ordering bug, since other test modules
import app.models first and register the tables globally)."""

from contextlib import closing
import sqlite3
import subprocess
import sys
import textwrap


def test_prod_engine_creates_tables_on_fresh_import(tmp_path):
    db_file = tmp_path / "bootstrap.db"
    script = textwrap.dedent(f"""
        import os
        os.environ["SCENTFOLIO_DB_URL"] = "sqlite:///{db_file}"
        from sqlalchemy import inspect
        from app.deps import _engine
        names = set(inspect(_engine).get_table_names())
        assert {{"perfumes", "notes", "perfume_notes"}} <= names, names
        print("OK", sorted(names))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_app_boot_upgrades_initial_sqlite_schema_in_place(tmp_path, monkeypatch):
    db_file = tmp_path / "scentfolio.db"
    # The original tables before Saved and note enrichment.
    with closing(sqlite3.connect(db_file)) as conn:
        conn.executescript("""
            CREATE TABLE perfumes (
                id INTEGER PRIMARY KEY, name VARCHAR(200) NOT NULL,
                house VARCHAR(200) NOT NULL, perfumer VARCHAR(200), year INTEGER,
                scent_family VARCHAR(50), description TEXT NOT NULL,
                my_impressions TEXT NOT NULL, formats VARCHAR(50) NOT NULL,
                source_urls TEXT NOT NULL, created_at DATETIME NOT NULL
            );
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE,
                family VARCHAR(50), description TEXT NOT NULL
            );
            CREATE TABLE perfume_notes (
                perfume_id INTEGER NOT NULL REFERENCES perfumes(id),
                note_id INTEGER NOT NULL REFERENCES notes(id),
                tier VARCHAR(10) NOT NULL,
                PRIMARY KEY (perfume_id, note_id, tier)
            );
            INSERT INTO perfumes VALUES (
                21, 'Woodland', 'Example House', 'Example Perfumer', 2020,
                'Woody', 'A cedar fragrance', 'Sampled in winter',
                'travel,sample', 'https://example.com/woodland', '2026-07-09 10:00:00'
            );
            INSERT INTO notes VALUES (7, 'cedar', 'Woody', 'Dry wood');
            INSERT INTO perfume_notes VALUES (21, 7, 'base');
        """)

    monkeypatch.setenv("SCENTFOLIO_DB_URL", f"sqlite:///{db_file}")
    script = textwrap.dedent("""
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            collection = client.get("/api/perfumes", params={"status": "collection"})
            collection.raise_for_status()
            [perfume] = collection.json()
            assert perfume == {
                "id": 21, "name": "Woodland", "house": "Example House",
                "perfumer": "Example Perfumer", "year": 2020,
                "status": "collection", "scent_families": ["Woody"],
                "description": "A cedar fragrance",
                "my_impressions": "Sampled in winter",
                "formats": ["travel", "sample"],
                "source_urls": ["https://example.com/woodland"],
                "notes": [{"id": 7, "name": "cedar", "tier": "base", "family": "Woody"}],
            }
            note = client.get("/api/notes/cedar")
            note.raise_for_status()
            assert note.json()["description"] == "Dry wood"
            assert note.json()["origin"] == ""
            assert note.json()["perfumes"] == [
                {"id": 21, "name": "Woodland", "house": "Example House"}
            ]
    """)

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
