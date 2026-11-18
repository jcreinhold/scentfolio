"""Regression test: the production dependency module must create its tables at
import time. This failed once because `deps` ran create_all() before the models
module was imported, so Base.metadata was empty and no tables were created.

We run in a subprocess so it exercises a fresh import of `app.deps` in isolation
(a same-process test wouldn't catch the ordering bug, since other test modules
import app.models first and register the tables globally)."""

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
