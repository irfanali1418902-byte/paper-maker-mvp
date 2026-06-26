"""SQL access for the papers table."""
import json
from typing import Optional

from app.core.database import get_connection


def insert(paper_id: str, subject: str, class_name: Optional[str],
           total_marks: int, question_ids: list) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO papers (id, subject, class_name, total_marks, question_ids) VALUES (?,?,?,?,?)",
        (paper_id, subject, class_name, total_marks, json.dumps(question_ids)),
    )
    conn.commit()
    conn.close()


def find_by_id(paper_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
