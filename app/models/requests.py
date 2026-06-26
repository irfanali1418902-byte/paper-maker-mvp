"""Pydantic request shapes used by the API layer."""

from typing import List, Optional

from pydantic import BaseModel


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


class SchoolSettings(BaseModel):
    """Used for both the POST body and the GET response (singleton id=1)."""

    id: Optional[int] = None
    school_name: str = ""
    school_name_ur: str = ""
    address: str = ""
    address_ur: str = ""
    logo_base64: Optional[str] = None
    accent_color: str = "#0e4d3c"
