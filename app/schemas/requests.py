"""Pydantic request shapes used by the API layer."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class GenerateQuestionsRequest(BaseModel):
    subject: str = ""
    topic: str = ""
    syllabus_topic_id: Optional[str] = None
    total_questions: int = 10
    bloom_distribution: str = "balanced"  # balanced | foundational | advanced
    question_types: List[str] = ["multiple-choice"]
    difficulty: str = "medium"


class GeneratePaperRequest(BaseModel):
    subject: str
    class_name: Optional[str] = None
    total_questions: int = 10
    bloom_distribution: str = "balanced"
    difficulty: Optional[str] = None
    paper_type: str = "mixed"  # mcq | mixed | subjective | custom-ratio
    # Sirf paper_type == "custom-ratio" par relevant. MCQ group ka %; subjective
    # group = 100 - mcq_percent. Range Pydantic level par enforce (0-100).
    mcq_percent: Optional[int] = Field(default=None, ge=0, le=100)


class AdaptivePaperRequest(BaseModel):
    """Phase 3: build a paper weighted toward a class's weak Bloom levels,
    learned from source_paper_id's latest results upload. Subject is taken from
    the source paper, so it can't drift from the weakness signal."""

    source_paper_id: str
    class_name: Optional[str] = None
    total_questions: int = 10
    difficulty: Optional[str] = None
    # Weakness signal (Bloom) aur format choice (type) alag cheezein hain — teacher
    # adaptive follow-up ka format chun sake. custom-ratio jaan-boojh kar allowed
    # nahi: weakness-distribution × ratio-split ka combo abhi scope se bahar hai.
    paper_type: str = "mixed"  # mcq | mixed | subjective

    @field_validator("paper_type")
    @classmethod
    def _reject_ratio_for_adaptive(cls, v: str) -> str:
        allowed = {"mcq", "mixed", "subjective"}
        if v not in allowed:
            raise ValueError(
                "Adaptive paper ke liye paper_type sirf mcq, mixed, ya subjective ho sakta hai "
                "(custom-ratio adaptive mein support nahi)."
            )
        return v


class ReplaceQuestionRequest(BaseModel):
    """Manual question swap in a built paper — replace old_question_id with
    new_question_id (both must already exist in the bank/paper)."""

    old_question_id: str
    new_question_id: str


class SchoolSettings(BaseModel):
    """Used for both the POST body and the GET response (singleton id=1)."""

    id: Optional[int] = None
    school_name: str = ""
    school_name_ur: str = ""
    address: str = ""
    address_ur: str = ""
    logo_base64: Optional[str] = None
    accent_color: str = "#0e4d3c"
