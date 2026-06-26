"""Basic tests for settings_repository (singleton row id=1)."""
from app.core.database import get_connection
from app.repositories import settings_repository


def _save(school_name: str, accent_color: str = "#000") -> None:
    settings_repository.upsert(
        school_name=school_name, school_name_ur="",
        address="", address_ur="",
        logo_base64=None, accent_color=accent_color,
    )


def test_get_returns_none_when_empty(test_db):
    assert settings_repository.get() is None


def test_upsert_creates_row_then_get_returns_it(test_db):
    _save("Test School", accent_color="#abc123")
    saved = settings_repository.get()
    assert saved is not None
    assert saved["school_name"] == "Test School"
    assert saved["accent_color"] == "#abc123"


def test_upsert_updates_existing_row(test_db):
    """ON CONFLICT (id) DO UPDATE — second upsert replaces first."""
    _save("First", "#000")
    _save("Second", "#fff")
    saved = settings_repository.get()
    assert saved["school_name"] == "Second"
    assert saved["accent_color"] == "#fff"


def test_singleton_invariant_only_one_row(test_db):
    """Multiple upserts must keep exactly one row (id=1)."""
    _save("A")
    _save("B")
    _save("C")
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM school_settings").fetchone()[0]
    conn.close()
    assert count == 1
