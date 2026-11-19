"""Exercise fresh ASGI startup against empty and existing SQLite files."""

import sqlite3
import subprocess
import sys
import textwrap
from contextlib import closing
from pathlib import Path


def test_startup_creates_tables_without_opening_database_on_import(tmp_path):
    db_file = tmp_path / "bootstrap.db"
    script = textwrap.dedent(f"""
        import os
        from pathlib import Path

        os.environ["SCENTFOLIO_DB_URL"] = "sqlite:///{db_file}"
        from fastapi.testclient import TestClient
        from sqlalchemy import inspect
        from app.main import app

        assert not Path("{db_file}").exists()
        with TestClient(app) as client:
            assert client.get("/api/perfumes").json() == []
            with app.state.session_factory() as session:
                names = set(inspect(session.get_bind()).get_table_names())
        assert {{"perfumes", "notes", "perfume_notes"}} <= names, names
    """)
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, check=False, text=True
    )
    assert result.returncode == 0, result.stderr
    assert db_file.is_file()


def test_provider_env_loads_only_provider_settings(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SCENTFOLIO_DB_URL=sqlite:///from-dotenv.db\n"
        "SCENTFOLIO_LLM_MODEL=dotenv-test-model\n"
    )
    for variable in (
        "SCENTFOLIO_DB_URL",
        "SCENTFOLIO_LLM_MODEL",
        "SCENTFOLIO_SERVE_UI",
        "PYTHON_DOTENV_DISABLED",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    script = textwrap.dedent("""
        import os
        from pathlib import Path

        from fastapi.testclient import TestClient
        from app import main

        main.BACKEND_DIR = Path.cwd()
        with TestClient(main.app):
            assert os.environ["SCENTFOLIO_LLM_MODEL"] == "dotenv-test-model"
            assert "SCENTFOLIO_DB_URL" not in os.environ
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "scentfolio.db").is_file()


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
                "notes": [{
                    "id": 7, "name": "cedar", "tier": "base", "family": "Woody"
                }],
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
            [sys.executable, "-c", script], capture_output=True, check=False, text=True
        )
        assert result.returncode == 0, result.stderr
