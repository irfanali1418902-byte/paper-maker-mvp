"""TEMPORARY ops helper — local paper_maker.db ko deployed instance ke
DB_PATH (Railway volume: /data/paper_maker.db) par restore karne ke liye.

Token-gated (DB_UPLOAD_TOKEN env). Kaam ho jaane ke baad ye file, app/api/admin.py,
aur main.py ka admin include — teeno hata dein, aur DB_UPLOAD_TOKEN env unset
kar dein. Ye production DB ko OVERWRITE karta hai, isliye permanent nahi rehna
chahiye.
"""

import os
import tempfile
from pathlib import Path

from app.core.database import DB_PATH, init_db

# SQLite file ka pehla 16-byte header — isse confirm karte hain ke jo bheja gaya
# woh waqai SQLite db hai (garbage overwrite na ho jaye).
_SQLITE_MAGIC = b"SQLite format 3\x00"


def upload_token() -> str | None:
    """DB_UPLOAD_TOKEN env. Set na ho to endpoint inert (caller 403 deta hai)."""
    return os.environ.get("DB_UPLOAD_TOKEN")


def restore_db(data: bytes) -> dict:
    """Uploaded bytes ko DB_PATH par atomically likhta hai (temp + os.replace).
    ValueError agar file valid SQLite na ho. Likhne ke baad init_db() chala kar
    schema current karta hai aur file readability confirm karta hai."""
    if not data.startswith(_SQLITE_MAGIC):
        raise ValueError("File valid SQLite database nahi lagti (SQLite header missing).")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: usi directory mein temp file likho phir rename — adhoori
    # write se live DB corrupt na ho.
    fd, tmp_name = tempfile.mkstemp(dir=str(DB_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_name, DB_PATH)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    # Schema migrations idempotently apply ho jaayein; agar file valid sqlite na
    # hoti to yahan sqlite3 error uthta (caller 500 map karta hai).
    init_db()
    return {"written_bytes": len(data), "db_path": str(DB_PATH)}
