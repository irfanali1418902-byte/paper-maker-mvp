"""SQL access for the questions table. No business logic, no HTTP."""

from typing import Optional

from app.core.database import get_connection


def insert(question_row: dict) -> None:
    """Inserts one fully-formed question. Caller is responsible for
    pre-computing every column value (uuid, marks, JSON-encoded options, etc.)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO questions
           (id, subject, topic, bloom_level, difficulty, question_type, marks,
            question_en, question_ur, options_en, options_ur,
            correct_answer_en, correct_answer_ur, explanation_en, explanation_ur,
            visual_emoji, visual_count)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            question_row["id"],
            question_row["subject"],
            question_row["topic"],
            question_row["bloom_level"],
            question_row["difficulty"],
            question_row["question_type"],
            question_row["marks"],
            question_row["question_en"],
            question_row["question_ur"],
            question_row["options_en"],
            question_row["options_ur"],
            question_row["correct_answer_en"],
            question_row["correct_answer_ur"],
            question_row["explanation_en"],
            question_row["explanation_ur"],
            question_row["visual_emoji"],
            question_row["visual_count"],
        ),
    )
    conn.commit()
    conn.close()


def find_least_used(subject: str, bloom_level: str, difficulty: Optional[str], limit: int) -> list:
    """Returns N matching questions ordered by usage_count ASC (least-used first)."""
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM questions WHERE subject = ? AND bloom_level = ?"
    params: list = [subject, bloom_level]
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    query += " ORDER BY usage_count ASC LIMIT ?"
    params.append(limit)
    rows = cur.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def increment_usage_count(question_id: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE questions SET usage_count = usage_count + 1 WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()


def find_by_id(question_id: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_by_filters(subject: Optional[str] = None, topic: Optional[str] = None) -> list:
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM questions WHERE 1=1"
    params: list = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if topic:
        query += " AND topic = ?"
        params.append(topic)
    rows = cur.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]
