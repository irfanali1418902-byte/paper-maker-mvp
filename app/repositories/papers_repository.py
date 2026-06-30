"""SQL access for the papers table."""

import json
from typing import Optional

from app.core.database import get_connection


def insert(
    paper_id: str, subject: str, class_name: Optional[str], total_marks: int, question_ids: list
) -> None:
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


def count_all() -> int:
    conn = get_connection()
    cur = conn.cursor()
    n = cur.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    conn.close()
    return n


def top_subject() -> Optional[str]:
    """Subject jiske sab se zyada papers bane hain (ties par alphabetical).
    Koi paper na ho to None."""
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT subject FROM papers GROUP BY subject ORDER BY COUNT(*) DESC, subject ASC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row else None


def update_question_ids(paper_id: str, question_ids: list, total_marks: int) -> None:
    """Replace a paper's question set + recomputed total in place — used when a
    teacher manually swaps a question in the preview."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE papers SET question_ids = ?, total_marks = ? WHERE id = ?",
        (json.dumps(question_ids), total_marks, paper_id),
    )
    conn.commit()
    conn.close()
