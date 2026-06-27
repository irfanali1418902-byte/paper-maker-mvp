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


class PaperQuestion(Question):
    """A Question as it appears inside a paper — DB row plus the Phase A
    item-analysis annotations the paper service derives (not DB columns)."""

    expected_difficulty: Optional[str] = None  # Bloom-derived Easy/Medium/Hard
    difficulty_mismatch: Optional[bool] = None  # stored difficulty != expected


class BalanceBand(BaseModel):
    """One difficulty band's share of a paper."""

    count: int
    percent: float


class PaperBalanceSummary(BaseModel):
    """Phase A: count + percent of questions per expected difficulty band."""

    total_questions: int
    easy: BalanceBand
    medium: BalanceBand
    hard: BalanceBand


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
    questions: List[PaperQuestion]
    balance_summary: PaperBalanceSummary


class PaperResponse(BaseModel):
    """GET /api/paper/{paper_id} ka response: poora paper + sab questions."""

    paper: Paper
    questions: List[PaperQuestion]
    balance_summary: PaperBalanceSummary


class StatusResponse(BaseModel):
    """Generic acknowledgement for write endpoints jo koi domain object
    return nahi karte (e.g. POST /api/school-settings)."""

    status: str


# ---- Result analyzer dashboard (Phase 2) ------------------------------------


class ResultUpload(BaseModel):
    """One row of result_uploads — a single results sheet a teacher uploaded."""

    id: str
    paper_id: str
    filename: str
    uploaded_at: Optional[str] = None


class UploadsResponse(BaseModel):
    """GET /api/paper/{paper_id}/uploads — newest upload first."""

    uploads: List[ResultUpload]


class StudentResult(BaseModel):
    """Per-student total for one upload, with class rank (ties share a rank)."""

    roll_no: str
    student_name: Optional[str] = None
    marks_obtained: int
    total_marks: int
    percent: float
    rank: int


class QuestionStat(BaseModel):
    """Per-question difficulty signal — low average_percent = class struggled."""

    question_index: int
    question_id: str
    bloom_level: str
    max_marks: int
    student_count: int
    average_marks: float
    average_percent: float
    full_marks_count: int


class BloomStat(BaseModel):
    """Per-Bloom-level rollup — which cognitive levels the class is weak on."""

    bloom_level: str
    question_count: int
    max_marks: int
    average_marks: float
    average_percent: float


class DashboardSummary(BaseModel):
    student_count: int
    total_marks: int
    class_average_marks: float
    class_average_percent: float
    highest_percent: float
    lowest_percent: float
    pass_count: int
    pass_percent: float
    pass_threshold_percent: float


class DashboardResponse(BaseModel):
    """Full analyzer dashboard for one upload."""

    upload: ResultUpload
    summary: DashboardSummary
    students: List[StudentResult]
    questions: List[QuestionStat]
    bloom_breakdown: List[BloomStat]
