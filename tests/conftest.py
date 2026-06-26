"""Shared pytest fixtures.

The `test_db` fixture monkeypatches `app.core.database.DB_PATH` to a fresh
SQLite file under pytest's `tmp_path`, then runs `init_db()` so the schema
is ready. Repositories pick this up automatically because `get_connection()`
looks up `DB_PATH` from its module's namespace at call time.

Each test gets its own DB file — no cross-test contamination.
"""

import pytest

from app.core import database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()
    return test_db_path
