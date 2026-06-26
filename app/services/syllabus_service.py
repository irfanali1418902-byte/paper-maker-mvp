"""Syllabus topic listing + CSV import."""

import csv
import uuid

from app.repositories import syllabus_repository

_ACTIVITY_TO_DIFFICULTY = {
    "Introduction": "easy",
    "Identification": "easy",
    "Practice": "medium",
    "Review": "hard",
}


def list_grades() -> list:
    return syllabus_repository.list_distinct_subject_grade()


def list_topics(subject: str | None = None, grade: str | None = None) -> list:
    """Lists topics with each row annotated with a 'suggested_difficulty'
    derived from the book's own Introduction/Identification/Practice/Review
    tagging."""
    topics = syllabus_repository.list_by_filters(subject=subject, grade=grade)
    for topic in topics:
        topic["suggested_difficulty"] = _ACTIVITY_TO_DIFFICULTY.get(
            topic["activity_type"], "medium"
        )
    return topics


def get_topic(topic_id: str) -> dict | None:
    """Single-topic lookup with the same 'suggested_difficulty' annotation."""
    topic = syllabus_repository.find_by_id(topic_id)
    if topic:
        topic["suggested_difficulty"] = _ACTIVITY_TO_DIFFICULTY.get(
            topic["activity_type"], "medium"
        )
    return topic


def import_from_csv(csv_path: str, subject: str, grade: str) -> int:
    """Reads a textbook CSV and inserts each row as a syllabus_topic.
    Duplicate (UNIQUE constraint) rows are skipped with a printed warning.
    Returns count of successfully inserted rows."""
    inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic_id = str(uuid.uuid4())
            try:
                syllabus_repository.insert(
                    topic_id=topic_id,
                    subject=subject,
                    grade=grade,
                    unit_no=int(row["unit_no"]),
                    unit_title=row["unit_title"],
                    page_range=row["page_range"],
                    subtopic_title=row["subtopic_title"],
                    activity_type=row["activity_type"],
                    page_no=int(row["page_no"]) if row["page_no"] else None,
                    learning_outcome=row.get("learning_outcome_snippet", ""),
                )
                inserted += 1
            except Exception as e:
                # Duplicate (UNIQUE constraint) ya koi aur row-level issue -- skip kar ke aage badho
                print(f"Skipped row (subtopic: {row.get('subtopic_title')}): {e}")
    return inserted
