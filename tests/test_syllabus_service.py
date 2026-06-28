"""Tests for syllabus_service PDF import (AI call mocked)."""

import io

import pytest
from pypdf import PdfWriter

from app.repositories import syllabus_repository
from app.services import syllabus_service


def _blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_coerce_int_handles_junk():
    assert syllabus_service._coerce_int("5") == 5
    assert syllabus_service._coerce_int(5) == 5
    assert syllabus_service._coerce_int(None) is None
    assert syllabus_service._coerce_int("abc") is None


def test_extract_pdf_text_rejects_non_pdf():
    with pytest.raises(ValueError, match="valid PDF nahi"):
        syllabus_service._extract_pdf_text(b"this is not a pdf")


def test_extract_pdf_text_rejects_image_only_pdf():
    # Blank page has no text layer — should read as scanned/image-only.
    with pytest.raises(ValueError, match="scanned"):
        syllabus_service._extract_pdf_text(_blank_pdf_bytes())


def test_import_from_pdf_inserts_topics(test_db, monkeypatch):
    monkeypatch.setattr(syllabus_service, "_extract_pdf_text", lambda b: "dummy text")
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_text",
        lambda text, subject, grade: [
            {
                "unit_no": 1,
                "unit_title": "Numbers",
                "subtopic_title": "Counting 1-10",
                "activity_type": "Introduction",
                "page_no": 5,
                "page_range": "5-9",
                "learning_outcome": "Count to ten",
            },
            {
                "unit_no": "2",  # string -> coerced to int
                "unit_title": "Shapes",
                "subtopic_title": "Circles",
                "activity_type": "Practice",
                "page_no": None,
                "learning_outcome": "Identify circles",
            },
        ],
    )

    result = syllabus_service.import_from_pdf(b"%PDF-fake", "Mathematics", "Grade 1")

    assert result == {"inserted": 2, "skipped": 0, "total_found": 2}
    rows = syllabus_repository.list_by_filters(subject="Mathematics", grade="Grade 1")
    assert len(rows) == 2
    titles = {r["subtopic_title"] for r in rows}
    assert titles == {"Counting 1-10", "Circles"}


def test_import_from_pdf_skips_blank_subtopic_and_dupes(test_db, monkeypatch):
    monkeypatch.setattr(syllabus_service, "_extract_pdf_text", lambda b: "dummy text")
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_text",
        lambda text, subject, grade: [
            {"unit_no": 1, "unit_title": "U", "subtopic_title": "Counting", "page_no": 1},
            {"unit_no": 1, "unit_title": "U", "subtopic_title": "  ", "page_no": 2},  # blank
            {"unit_no": 1, "unit_title": "U", "subtopic_title": "Counting", "page_no": 1},  # dupe
        ],
    )

    result = syllabus_service.import_from_pdf(b"%PDF-fake", "Mathematics", "Grade 1")

    assert result["inserted"] == 1
    assert result["skipped"] == 2
    assert result["total_found"] == 3
