"""SQL access for the syllabus_topics table."""

from typing import Optional

from app.core.database import get_connection


def find_by_id(topic_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM syllabus_topics WHERE id = ?", (topic_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_by_filters(subject: Optional[str] = None, grade: Optional[str] = None) -> list:
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM syllabus_topics WHERE 1=1"
    params: list = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if grade:
        query += " AND grade = ?"
        params.append(grade)
    query += " ORDER BY unit_no, page_no"
    rows = cur.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_distinct_subject_grade() -> list:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT subject, grade FROM syllabus_topics ORDER BY subject, grade"
    ).fetchall()
    conn.close()
    return [{"subject": row["subject"], "grade": row["grade"]} for row in rows]


def insert(
    topic_id: str,
    subject: str,
    grade: str,
    unit_no: int,
    unit_title: str,
    page_range: str,
    subtopic_title: str,
    activity_type: str,
    page_no: Optional[int],
    learning_outcome: str,
) -> None:
    """Used by the CSV importer. Raises on UNIQUE constraint violation;
    caller decides what to do with duplicates."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO syllabus_topics
           (id, subject, grade, unit_no, unit_title, page_range,
            subtopic_title, activity_type, page_no, learning_outcome)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            topic_id,
            subject,
            grade,
            unit_no,
            unit_title,
            page_range,
            subtopic_title,
            activity_type,
            page_no,
            learning_outcome,
        ),
    )
    conn.commit()
    conn.close()
