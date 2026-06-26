"""HTTP routes for question generation and listing."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models.requests import GenerateRequest
from app.services import question_service, syllabus_service

router = APIRouter()


@router.post("/api/generate-questions")
def generate_questions(req: GenerateRequest):
    """Topic dekar AI se Bloom-tagged bilingual questions generate karta hai
    aur question bank (SQLite) mein save karta hai.

    Agar syllabus_topic_id diya jaye, to subject/topic/difficulty usi
    syllabus_topics row se khud-bakhud le liye jaate hain (manual typing
    ki zaroorat nahi)."""
    if req.syllabus_topic_id:
        topic = syllabus_service.get_topic(req.syllabus_topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="syllabus_topic_id nahi mila.")
        req.subject = topic["subject"]
        req.topic = topic["subtopic_title"]
        req.difficulty = topic["suggested_difficulty"]

    if not req.subject or not req.topic:
        raise HTTPException(
            status_code=400,
            detail="subject aur topic dono zaroori hain (ya syllabus_topic_id den).",
        )

    try:
        ai_questions = question_service.generate_for_topic(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI generation fail hui: {e}")

    try:
        saved_ids = question_service.persist_batch(ai_questions, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question save fail hui (DB error): {e}")

    return {"saved_count": len(saved_ids), "question_ids": saved_ids}


@router.get("/api/questions")
def list_questions(subject: Optional[str] = None, topic: Optional[str] = None):
    """Question bank browse karne ke liye."""
    return question_service.list_questions(subject=subject, topic=topic)
