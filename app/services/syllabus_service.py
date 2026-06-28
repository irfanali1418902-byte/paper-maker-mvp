"""Syllabus topic listing + CSV/PDF import."""

import csv
import io
import sqlite3
import uuid

from pypdf import PdfReader

from app.repositories import syllabus_repository
from app.services import ai_service

_ACTIVITY_TO_DIFFICULTY = {
    "Introduction": "easy",
    "Identification": "easy",
    "Practice": "medium",
    "Review": "hard",
}

# Pypdf se itne characters se kam nikle to maan lo PDF scanned/image-only hai
# (text layer nahi) — AI ko bhejna bekaar hai, teacher ko saaf batao.
_MIN_PDF_TEXT_CHARS = 40


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


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Pulls the text layer out of a PDF. Raises ValueError if the file is
    not a readable PDF or has no extractable text (scanned/image-only)."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise ValueError(f"PDF parh nahi paye — file corrupt ya valid PDF nahi hai: {e}") from e

    if len(text.strip()) < _MIN_PDF_TEXT_CHARS:
        raise ValueError(
            "Is PDF mein text nahi mila — lagta hai scanned/image-only PDF hai. "
            "Abhi sirf text-wale (digital) PDF support hain. Text-based PDF try karen."
        )
    return text


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def import_from_pdf(pdf_bytes: bytes, subject: str, grade: str) -> dict:
    """Extracts the PDF's text, asks the AI to structure it into topics, and
    saves each as a syllabus_topic. Duplicates (UNIQUE constraint) are skipped.
    Returns counts so the route can report what happened."""
    text = _extract_pdf_text(pdf_bytes)
    topics = ai_service.extract_topics_from_text(text, subject, grade)

    inserted = 0
    skipped = 0
    for topic in topics:
        subtopic_title = (topic.get("subtopic_title") or "").strip()
        if not subtopic_title:
            skipped += 1
            continue
        try:
            syllabus_repository.insert(
                topic_id=str(uuid.uuid4()),
                subject=subject,
                grade=grade,
                unit_no=_coerce_int(topic.get("unit_no")) or 1,
                unit_title=(topic.get("unit_title") or "Untitled Unit").strip(),
                page_range=topic.get("page_range"),
                subtopic_title=subtopic_title,
                activity_type=(topic.get("activity_type") or "Practice").strip(),
                page_no=_coerce_int(topic.get("page_no")),
                learning_outcome=(topic.get("learning_outcome") or "").strip(),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # UNIQUE-constraint duplicate — same topic already imported, skip.
            skipped += 1

    return {"inserted": inserted, "skipped": skipped, "total_found": len(topics)}


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
            except sqlite3.IntegrityError as e:
                # UNIQUE-constraint duplicate row — expected on re-imports, skip
                # quietly and continue. Other failures (missing CSV column,
                # non-int unit_no, etc.) are NOT caught here on purpose: they
                # represent operator-visible CSV problems and should crash
                # loudly so they get fixed rather than silently swallowed.
                print(f"Skipped duplicate row (subtopic: {row.get('subtopic_title')}): {e}")
    return inserted
