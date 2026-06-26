"""HTTP routes for syllabus topic listing."""

from typing import List, Optional

from fastapi import APIRouter

from app.models.responses import SubjectGrade, SyllabusTopic
from app.services import syllabus_service

router = APIRouter()


@router.get("/api/syllabus-grades", response_model=List[SubjectGrade])
def list_syllabus_grades():
    """Database mein jo bhi subject+grade combinations imported hain, unki list deta hai (dropdown ke liye)."""
    return syllabus_service.list_grades()


@router.get("/api/syllabus-topics", response_model=List[SyllabusTopic])
def list_syllabus_topics(subject: Optional[str] = None, grade: Optional[str] = None):
    """Real textbook se import kiye gaye topics list karta hai, dropdown ke
    liye. Har topic ke saath suggested difficulty bhi deta hai (book ke apne
    Introduction/Identification/Practice/Review tagging se mapped)."""
    return syllabus_service.list_topics(subject=subject, grade=grade)
