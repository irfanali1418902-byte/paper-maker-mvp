"""Tests for syllabus_service PDF/ZIP import (AI call mocked)."""

import io
import zipfile

import pytest
from pypdf import PdfWriter

from app.repositories import syllabus_repository
from app.services import syllabus_service
from app.services.exceptions import AIGenerationFailed


def _zip_bytes(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


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


def test_try_extract_pdf_text_rejects_non_pdf():
    with pytest.raises(ValueError, match="valid PDF nahi"):
        syllabus_service._try_extract_pdf_text(b"this is not a pdf")


def test_try_extract_pdf_text_returns_none_for_image_only_pdf():
    # Blank page has no text layer — reads as scanned/image-only, so the text
    # extractor returns None and the caller falls back to AI vision.
    assert syllabus_service._try_extract_pdf_text(_blank_pdf_bytes()) is None


def test_render_pdf_to_images_renders_pages():
    # A real (blank) PDF should render to one PNG per page for the vision path.
    images = syllabus_service._render_pdf_to_images(_blank_pdf_bytes())
    assert len(images) == 1
    mime, data = images[0]
    assert mime == "image/png"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_import_from_pdf_falls_back_to_vision_for_scanned(test_db, monkeypatch):
    # No text layer -> _try_extract_pdf_text returns None -> vision path runs
    # on each rendered page and its topics get saved.
    monkeypatch.setattr(syllabus_service, "_try_extract_pdf_text", lambda b: None)
    monkeypatch.setattr(
        syllabus_service,
        "_render_pdf_to_images",
        lambda b: [("image/png", b"page1"), ("image/png", b"page2")],
    )
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_image",
        lambda data, mime, subject, grade: [
            {"unit_no": 1, "unit_title": "Scanned", "subtopic_title": f"Topic {data!r}"}
        ],
    )

    result = syllabus_service.import_from_pdf(b"%PDF-scanned", "Mathematics", "Grade 1")

    # One topic per rendered page, both saved.
    assert result["total_found"] == 2
    assert result["inserted"] == 2
    titles = {r["subtopic_title"] for r in syllabus_repository.list_by_filters()}
    assert titles == {"Topic b'page1'", "Topic b'page2'"}


def test_import_from_pdf_inserts_topics(test_db, monkeypatch):
    monkeypatch.setattr(syllabus_service, "_try_extract_pdf_text", lambda b: "dummy text")
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
    monkeypatch.setattr(syllabus_service, "_try_extract_pdf_text", lambda b: "dummy text")
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


def test_import_from_zip_handles_pdf_image_and_unsupported(test_db, monkeypatch):
    monkeypatch.setattr(syllabus_service, "_try_extract_pdf_text", lambda data: "pdf text")
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_text",
        lambda text, subject, grade: [
            {"unit_no": 1, "unit_title": "U1", "subtopic_title": "From PDF", "page_no": 1}
        ],
    )
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_image",
        lambda data, mime, subject, grade: [
            {"unit_no": 2, "unit_title": "U2", "subtopic_title": "From Image", "page_no": 2}
        ],
    )

    zip_bytes = _zip_bytes(
        {
            "math.pdf": b"fake-pdf",
            "shapes.png": b"fake-png",
            "notes.txt": b"ignore me",
            "__MACOSX/junk": b"junk",
        }
    )
    result = syllabus_service.import_from_zip(zip_bytes, "Mathematics", "Grade 1")

    assert result["total_found"] == 2
    assert result["inserted"] == 2
    # Per-file breakdown: pdf ok, image ok, txt skipped (macosx ignored entirely).
    by_name = {f["name"]: f for f in result["files"]}
    assert by_name["math.pdf"]["status"] == "ok" and by_name["math.pdf"]["kind"] == "pdf"
    assert by_name["shapes.png"]["status"] == "ok" and by_name["shapes.png"]["kind"] == "image"
    assert by_name["notes.txt"]["status"] == "skipped"
    assert "junk" not in by_name

    titles = {r["subtopic_title"] for r in syllabus_repository.list_by_filters()}
    assert titles == {"From PDF", "From Image"}


def test_import_from_zip_records_per_file_error(test_db, monkeypatch):
    monkeypatch.setattr(syllabus_service, "_try_extract_pdf_text", lambda data: "pdf text")
    monkeypatch.setattr(
        syllabus_service.ai_service,
        "extract_topics_from_text",
        lambda text, subject, grade: [
            {"unit_no": 1, "unit_title": "U1", "subtopic_title": "Good", "page_no": 1}
        ],
    )

    def _boom(data, mime, subject, grade):
        raise AIGenerationFailed("Gemini abhi busy hai (HTTP 503).")

    monkeypatch.setattr(syllabus_service.ai_service, "extract_topics_from_image", _boom)

    zip_bytes = _zip_bytes({"ok.pdf": b"x", "bad.png": b"y"})
    result = syllabus_service.import_from_zip(zip_bytes, "Mathematics", "Grade 1")

    by_name = {f["name"]: f for f in result["files"]}
    assert by_name["ok.pdf"]["status"] == "ok"
    assert by_name["bad.png"]["status"] == "error"
    assert "503" in by_name["bad.png"]["message"]
    assert result["inserted"] == 1  # the good PDF still saved


def test_import_from_zip_bad_zip_raises():
    with pytest.raises(ValueError, match="ZIP file kharab"):
        syllabus_service.import_from_zip(b"not a zip", "Math", "Grade 1")


def test_import_from_zip_no_supported_files_raises():
    zip_bytes = _zip_bytes({"readme.txt": b"hi", "data.csv": b"a,b"})
    with pytest.raises(ValueError, match="koi PDF/JPG/PNG"):
        syllabus_service.import_from_zip(zip_bytes, "Math", "Grade 1")
