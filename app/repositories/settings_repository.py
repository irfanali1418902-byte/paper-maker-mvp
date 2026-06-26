"""SQL access for the school_settings table (single-row id=1 upsert)."""
from typing import Optional

from app.core.database import get_connection


def get() -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM school_settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def upsert(school_name: str, school_name_ur: str, address: str,
           address_ur: str, logo_base64: Optional[str], accent_color: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO school_settings (id, school_name, school_name_ur, address, address_ur, logo_base64, accent_color)
           VALUES (1, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             school_name=excluded.school_name, school_name_ur=excluded.school_name_ur,
             address=excluded.address, address_ur=excluded.address_ur,
             logo_base64=excluded.logo_base64, accent_color=excluded.accent_color""",
        (school_name, school_name_ur, address, address_ur, logo_base64, accent_color),
    )
    conn.commit()
    conn.close()
