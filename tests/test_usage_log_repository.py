"""Basic tests for usage_log_repository."""

from app.core.database import get_connection
from app.repositories import usage_log_repository


def _fetch_all():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM usage_log").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def test_insert_records_one_row(test_db):
    row_id = usage_log_repository.insert(
        provider="gemini",
        model="gemini-2.5-flash",
        status="success",
        input_tokens=100,
        output_tokens=500,
        total_tokens=600,
    )
    assert row_id

    rows = _fetch_all()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == row_id
    assert row["provider"] == "gemini"
    assert row["model"] == "gemini-2.5-flash"
    assert row["status"] == "success"
    assert row["input_tokens"] == 100
    assert row["output_tokens"] == 500
    assert row["total_tokens"] == 600


def test_insert_with_null_token_counts(test_db):
    """Provider response may omit usage data; nullable columns must accept that."""
    usage_log_repository.insert(
        provider="claude",
        model="claude-sonnet-4-6",
        status="success",
    )
    row = _fetch_all()[0]
    assert row["input_tokens"] is None
    assert row["output_tokens"] is None
    assert row["total_tokens"] is None


def test_timestamp_auto_populated(test_db):
    """DEFAULT CURRENT_TIMESTAMP must fill the timestamp without us passing it."""
    usage_log_repository.insert(provider="gemini", model="m", status="success")
    row = _fetch_all()[0]
    assert row["timestamp"] is not None


def test_multiple_inserts_each_get_unique_ids(test_db):
    id_a = usage_log_repository.insert(provider="gemini", model="m", status="success")
    id_b = usage_log_repository.insert(provider="gemini", model="m", status="success")
    assert id_a != id_b
    assert len(_fetch_all()) == 2
