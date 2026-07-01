"""HTTP routes for syllabus topic listing + PDF import."""

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.responses import (
    SubjectGrade,
    SyllabusImportResponse,
    SyllabusTopic,
    SyllabusZipImportResponse,
)
from app.services import syllabus_service
from app.services.exceptions import AIGenerationFailed

router = APIRouter()


@router.get("/api/syllabus-grades", response_model=List[SubjectGrade])
def list_syllabus_grades():
    """Database mein jo bhi subject+grade combinations imported hain, unki list deta hai (dropdown ke liye)."""
    try:
        return syllabus_service.list_grades()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Syllabus grades fetch fail hui (DB error): {e}"
        ) from e


@router.post("/api/syllabus/upload-pdf", response_model=SyllabusImportResponse)
def upload_syllabus_pdf(
    subject: str = Form(...),
    grade: str = Form(...),
    file: UploadFile = File(...),
):
    """Teacher ek syllabus/textbook PDF upload karta hai; app text nikaal kar
    AI se topics structure karwati hai aur syllabus_topics mein save karti hai.
    Duplicate topics skip ho jaate hain."""
    if not subject.strip() or not grade.strip():
        raise HTTPException(status_code=400, detail="subject aur grade dono zaroori hain.")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sirf .pdf file upload karen.")

    pdf_bytes = file.file.read()

    try:
        result = syllabus_service.import_from_pdf(pdf_bytes, subject.strip(), grade.strip())
    except ValueError as e:
        # Bad/scanned/unreadable PDF — well-formed request, unusable content.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIGenerationFailed as e:
        raise HTTPException(status_code=502, detail=f"AI extraction fail hui: {e}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Syllabus PDF save fail hui (DB error): {e}"
        ) from e

    return {"subject": subject.strip(), "grade": grade.strip(), **result}


@router.post("/api/syllabus/upload-zip", response_model=SyllabusZipImportResponse)
def upload_syllabus_zip(
    subject: str = Form(...),
    grade: str = Form(...),
    file: UploadFile = File(...),
):
    """Teacher ek ZIP upload karta hai jisme multiple syllabus PDFs aur/ya
    images (JPG/PNG) hoti hain; har file se AI topics nikaal kar save karti
    hai. Har file ka natija alag-alag wapas aata hai (ek file fail ho to
    baaki chalti rehti hain)."""
    if not subject.strip() or not grade.strip():
        raise HTTPException(status_code=400, detail="subject aur grade dono zaroori hain.")
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Sirf .zip file upload karen.")

    zip_bytes = file.file.read()

    try:
        result = syllabus_service.import_from_zip(zip_bytes, subject.strip(), grade.strip())
    except ValueError as e:
        # Bad/empty ZIP — well-formed request, unusable content.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Syllabus ZIP save fail hui (DB error): {e}"
        ) from e

    return {"subject": subject.strip(), "grade": grade.strip(), **result}


@router.get("/api/syllabus-topics", response_model=List[SyllabusTopic])
def list_syllabus_topics(subject: Optional[str] = None, grade: Optional[str] = None):
    """Real textbook se import kiye gaye topics list karta hai, dropdown ke
    liye. Har topic ke saath suggested difficulty bhi deta hai (book ke apne
    Introduction/Identification/Practice/Review tagging se mapped)."""
    try:
        return syllabus_service.list_topics(subject=subject, grade=grade)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Syllabus topics fetch fail hui (DB error): {e}"
        ) from e
