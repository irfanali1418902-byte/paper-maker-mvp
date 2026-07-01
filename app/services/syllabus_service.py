"""Syllabus topic listing + CSV/PDF/ZIP import."""

import csv
import io
import os
import uuid
import zipfile

import fitz
from pypdf import PdfReader

from app.repositories import syllabus_repository
from app.services import ai_service
from app.services.exceptions import AIGenerationFailed, DuplicateSyllabusTopic

_ACTIVITY_TO_DIFFICULTY = {
    "Introduction": "easy",
    "Identification": "easy",
    "Practice": "medium",
    "Review": "hard",
}

# Pypdf se itne characters se kam nikle to maan lo PDF scanned/image-only hai
# (text layer nahi) — phir page-images render karke AI vision (OCR) se padhte hain.
_MIN_PDF_TEXT_CHARS = 40

# Scanned PDF vision fallback: itne pages tak hi render+OCR karte hain. Syllabus
# ka contents/index aam taur par pehle chand pages par hota hai; poori scanned
# kitaab ko page-by-page vision bhejna mehnga aur Gemini quota ke liye khatarnak
# hai. Is se zyada pages ho to baaki skip ho jaate hain (warning print hoti hai).
_MAX_VISION_PAGES = 15

# Scanned page ko itne DPI par render karte hain — OCR ke liye sharp, par
# payload itna bhaari nahi ke vision call slow/expensive ho jaye.
_RENDER_DPI = 200

# ZIP ke andar in image extensions ko AI vision se padhte hain.
_IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


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


def _try_extract_pdf_text(pdf_bytes: bytes) -> str | None:
    """Pulls the text layer out of a PDF. Returns the text, ya None agar PDF
    mein usable text layer na ho (scanned/image-only — caller vision fallback
    use karta hai). ValueError sirf tab jab file readable PDF hi na ho."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise ValueError(f"PDF parh nahi paye — file corrupt ya valid PDF nahi hai: {e}") from e

    if len(text.strip()) < _MIN_PDF_TEXT_CHARS:
        return None
    return text


def _render_pdf_to_images(pdf_bytes: bytes) -> list[tuple[str, bytes]]:
    """Har PDF page ko PNG image (mime_type, bytes) mein render karta hai, AI
    vision (OCR) ke liye. Scanned/image-only PDFs ke liye fallback. _MAX_VISION_
    PAGES se zyada pages ho to baaki skip (warning print). ValueError agar PDF
    open hi na ho."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"PDF parh nahi paye — file corrupt ya valid PDF nahi hai: {e}") from e

    matrix = fitz.Matrix(_RENDER_DPI / 72, _RENDER_DPI / 72)
    page_count = min(doc.page_count, _MAX_VISION_PAGES)
    if doc.page_count > _MAX_VISION_PAGES:
        print(
            f"Scanned PDF mein {doc.page_count} pages — sirf pehle "
            f"{_MAX_VISION_PAGES} vision se padhe gaye, baaki skip."
        )

    images: list[tuple[str, bytes]] = []
    try:
        for i in range(page_count):
            pix = doc[i].get_pixmap(matrix=matrix)
            images.append(("image/png", pix.tobytes("png")))
    finally:
        doc.close()
    return images


def _extract_topics_from_pdf(pdf_bytes: bytes, subject: str, grade: str) -> list:
    """PDF se topics nikalta hai. Pehle text layer try karta hai; text na mile
    (scanned/image-only PDF) to har page ko image mein render karke AI vision
    (OCR) se topics nikalta hai aur sab pages ke topics merge kar deta hai.
    Single-PDF aur ZIP-PDF dono yahi raasta use karte hain."""
    text = _try_extract_pdf_text(pdf_bytes)
    if text is not None:
        return ai_service.extract_topics_from_text(text, subject, grade)

    topics: list = []
    for mime_type, page_png in _render_pdf_to_images(pdf_bytes):
        topics.extend(ai_service.extract_topics_from_image(page_png, mime_type, subject, grade))
    return topics


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _save_topics(topics: list, subject: str, grade: str) -> dict:
    """Inserts AI-extracted topics, skipping blanks and duplicates. Returns
    {inserted, skipped}. Shared by PDF, image, and ZIP imports."""
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
        except DuplicateSyllabusTopic:
            # Same topic already imported, skip.
            skipped += 1
    return {"inserted": inserted, "skipped": skipped}


def import_from_pdf(pdf_bytes: bytes, subject: str, grade: str) -> dict:
    """Extracts the PDF's text, asks the AI to structure it into topics, and
    saves each as a syllabus_topic. Duplicates (UNIQUE constraint) are skipped.
    Scanned/image-only PDF ho to khud-ba-khud AI vision (OCR) fallback chalta
    hai. Returns counts so the route can report what happened."""
    topics = _extract_topics_from_pdf(pdf_bytes, subject, grade)
    saved = _save_topics(topics, subject, grade)
    return {"total_found": len(topics), **saved}


def _extract_topics_from_entry(name: str, data: bytes, subject: str, grade: str) -> list:
    """One ZIP entry -> topics. PDF se text-extraction, image se AI vision.
    Unsupported extension par ValueError raise karta hai (caller per-file
    handle karta hai)."""
    ext = os.path.splitext(name)[1].lower()
    if ext == ".pdf":
        return _extract_topics_from_pdf(data, subject, grade)
    if ext in _IMAGE_MIME:
        return ai_service.extract_topics_from_image(data, _IMAGE_MIME[ext], subject, grade)
    raise ValueError("PDF/JPG/PNG nahi — skip kiya.")


def import_from_zip(zip_bytes: bytes, subject: str, grade: str) -> dict:
    """Processes a ZIP of syllabus files: each PDF (text) and image (AI vision)
    se topics nikaal kar save karta hai. Har file independently process hoti
    hai — ek file fail ho to baaki chalti rehti hain, aur per-file natija
    'files' list mein wapas aata hai."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise ValueError(f"ZIP file kharab/invalid hai: {e}") from e

    all_topics: list = []
    files: list = []
    saw_supported = False

    for name in archive.namelist():
        base = os.path.basename(name)
        # Directories, macOS junk, aur hidden files skip.
        if name.endswith("/") or "__MACOSX" in name or not base or base.startswith("."):
            continue
        ext = os.path.splitext(name)[1].lower()
        kind = "pdf" if ext == ".pdf" else ("image" if ext in _IMAGE_MIME else "unsupported")

        if kind == "unsupported":
            files.append(
                {
                    "name": base,
                    "kind": kind,
                    "topics_found": 0,
                    "status": "skipped",
                    "message": "PDF/JPG/PNG nahi",
                }
            )
            continue

        saw_supported = True
        try:
            topics = _extract_topics_from_entry(name, archive.read(name), subject, grade)
            all_topics.extend(topics)
            files.append(
                {
                    "name": base,
                    "kind": kind,
                    "topics_found": len(topics),
                    "status": "ok",
                    "message": "",
                }
            )
        except (ValueError, AIGenerationFailed) as e:
            # Bad/scanned file ya AI failure — sirf is file ko error mark karo,
            # baaki batch chalti rahe.
            files.append(
                {
                    "name": base,
                    "kind": kind,
                    "topics_found": 0,
                    "status": "error",
                    "message": str(e),
                }
            )

    if not saw_supported:
        raise ValueError("ZIP mein koi PDF/JPG/PNG file nahi mili.")

    saved = _save_topics(all_topics, subject, grade)
    return {"total_found": len(all_topics), **saved, "files": files}


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
            except DuplicateSyllabusTopic as e:
                # Duplicate row — expected on re-imports, skip quietly and
                # continue. Other failures (missing CSV column, non-int
                # unit_no, etc.) are NOT caught here on purpose: they
                # represent operator-visible CSV problems and should crash
                # loudly so they get fixed rather than silently swallowed.
                print(f"Skipped duplicate row (subtopic: {row.get('subtopic_title')}): {e}")
    return inserted
