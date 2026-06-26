"""SQL access for the usage_log table.

Every successful AI provider call (Gemini or Claude) adds one row. Future
per-school billing will aggregate over (provider, model, total_tokens,
timestamp) — so capture as much as the provider gives us, even when token
counts are missing.
"""
import uuid
from typing import Optional

from app.core.database import get_connection


def insert(provider: str, model: str, status: str,
           input_tokens: Optional[int] = None,
           output_tokens: Optional[int] = None,
           total_tokens: Optional[int] = None) -> str:
    """Records one provider call. Returns the new row id.

    Token counts are nullable because not every provider response shape
    includes them — capture what you have, leave the rest NULL.
    """
    row_id = str(uuid.uuid4())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO usage_log
           (id, provider, model, status, input_tokens, output_tokens, total_tokens)
           VALUES (?,?,?,?,?,?,?)""",
        (row_id, provider, model, status, input_tokens, output_tokens, total_tokens),
    )
    conn.commit()
    conn.close()
    return row_id
