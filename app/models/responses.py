"""Pydantic response shapes used by the API layer.

Routes pass these as `response_model=...` so FastAPI:
  - validates that the dict we return matches the declared shape
  - generates accurate OpenAPI / Swagger docs at /docs
  - strips fields not in the model (defensive against leaking internals)

If the DB row diverges from the model, a 500 will fire — in that case the
fix is to add the new column to the model below, not to widen the route
return type. Keep these in sync with the actual columns under
`app/core/database.py`.
"""
from typing import List, Optional
from pydantic import BaseModel


# ---- Domain shapes (reused across endpoints) --------------------------------

class Question(BaseModel):
    """One row of the questions table. options_en / options_ur stay as
    JSON-encoded strings because that's how SQLite stores them — the
    frontend JSON.parses them on receipt."""
    id: str
    subject: str
    topic: str
    bloom_level: str
    difficulty: str
    question_type: str
    marks: int
    question_en: Optional[str] = None
    question_ur: Optional[str] = None
    options_en: Optional[str] = None
    options_ur: Optional[str] = None
    correct_answer_en: Optional[str] = None
    correct_answer_ur: Optional[str] = None
    explanation_en: Optional[str] = None
    explanation_ur: Optional[str] = None
    visual_emoji: Optional[str] = None
    visual_count: Optional[int] = None
    usage_count: int = 0
    created_at: Optional[str] = None


class Paper(BaseModel):
    """One row of the papers table. question_ids stays as JSON-encoded
    string (matches DB storage)."""
    id: str
    subject: str
    class_name: Optional[str] = None
    total_marks: int
    question_ids: str
    created_at: Optional[str] = None


class SyllabusTopic(BaseModel):
    """syllabus_topics row, plus a derived 'suggested_difficulty' annotation
    that the service layer adds."""
    id: str
    subject: str
    grade: Optional[str] = None
    unit_no: int
    unit_title: str
    page_range: Optional[str] = None
    subtopic_title: str
    activity_type: str
    page_no: Optional[int] = None
    learning_outcome: Optional[str] = None
    suggested_difficulty: str


class SubjectGrade(BaseModel):
    """Used by /api/syllabus-grades dropdown — distinct (subject, grade) pairs."""
    subject: str
    grade: Optional[str] = None


# ---- Endpoint-specific responses --------------------------------------------

class GenerateQuestionsResponse(BaseModel):
    saved_count: int
    question_ids: List[str]


class GeneratePaperResponse(BaseModel):
    paper_id: str
    total_marks: int
    questions: List[Question]


class PaperResponse(BaseModel):
    """GET /api/paper/{paper_id} ka response: poora paper + sab questions."""
    paper: Paper
    questions: List[Question]


class StatusResponse(BaseModel):
    """Generic acknowledgement for write endpoints jo koi domain object
    return nahi karte (e.g. POST /api/school-settings)."""
    status: str
