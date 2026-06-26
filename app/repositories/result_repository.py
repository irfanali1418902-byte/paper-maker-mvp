"""SQL access for result_uploads and student_question_results.

These two tables are tightly coupled (an upload owns its per-student
per-question rows), so they share one repository module — querying one
without the other doesn't really happen for the analyzer use case.
"""

from typing import Optional

from app.core.database import get_connection

# ---- result_uploads --------------------------------------------------------


def insert_upload(upload_id: str, paper_id: str, filename: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO result_uploads (id, paper_id, filename) VALUES (?,?,?)",
        (upload_id, paper_id, filename),
    )
    conn.commit()
    conn.close()


def find_upload_by_id(upload_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM result_uploads WHERE id = ?", (upload_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_uploads_for_paper(paper_id: str) -> list:
    """Most recent uploads first — analyzer dashboards typically want
    the latest upload for a given paper at the top."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM result_uploads WHERE paper_id = ? ORDER BY uploaded_at DESC",
        (paper_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---- student_question_results ----------------------------------------------


def insert_student_result(
    result_id: str,
    result_upload_id: str,
    roll_no: str,
    student_name: Optional[str],
    question_id: str,
    marks_obtained: int,
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO student_question_results
           (id, result_upload_id, roll_no, student_name, question_id, marks_obtained)
           VALUES (?,?,?,?,?,?)""",
        (result_id, result_upload_id, roll_no, student_name, question_id, marks_obtained),
    )
    conn.commit()
    conn.close()


def list_results_for_upload(upload_id: str) -> list:
    """Every per-student per-question row for one upload — service layer
    aggregates these into per-student totals, per-question averages, etc."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM student_question_results WHERE result_upload_id = ?",
        (upload_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
