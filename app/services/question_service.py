"""Orchestrates question generation (AI call + persistence)."""
import json
import uuid

from app.models.requests import GenerateQuestionsRequest
from app.repositories import questions_repository
from app.services import ai_service, bloom_service


def generate_for_topic(req: GenerateQuestionsRequest) -> list[dict]:
    """Asks the AI for a batch of questions for this topic, using the
    requested Bloom distribution. Returns the raw AI-generated dicts —
    persistence is a separate step so the route can distinguish AI failure
    (502) from DB failure (500)."""
    distribution = bloom_service.calculate_bloom_distribution(
        req.bloom_distribution, req.total_questions
    )
    return ai_service.generate_questions_from_ai(
        topic=req.topic,
        subject=req.subject,
        bloom_distribution=distribution,
        question_types=req.question_types,
        difficulty=req.difficulty,
    )


def persist_batch(ai_questions: list[dict], req: GenerateQuestionsRequest) -> list[str]:
    """Saves AI-generated questions to the bank. Returns the IDs of inserted
    rows."""
    saved_ids: list[str] = []
    for q in ai_questions:
        qid = str(uuid.uuid4())
        marks = bloom_service.calculate_marks(
            q.get("bloom_level", "UNDERSTAND"),
            q.get("question_type", "multiple-choice"),
            req.difficulty,
        )
        questions_repository.insert({
            "id": qid,
            "subject": req.subject,
            "topic": req.topic,
            "bloom_level": q.get("bloom_level"),
            "difficulty": req.difficulty,
            "question_type": q.get("question_type"),
            "marks": marks,
            "question_en": q.get("question_en"),
            "question_ur": q.get("question_ur"),
            "options_en": json.dumps(q.get("options_en", [])),
            "options_ur": json.dumps(q.get("options_ur", [])),
            "correct_answer_en": q.get("correct_answer_en"),
            "correct_answer_ur": q.get("correct_answer_ur"),
            "explanation_en": q.get("explanation_en"),
            "explanation_ur": q.get("explanation_ur"),
            "visual_emoji": q.get("visual_emoji"),
            "visual_count": q.get("visual_count"),
        })
        saved_ids.append(qid)
    return saved_ids


def list_questions(subject: str | None = None, topic: str | None = None) -> list:
    return questions_repository.list_by_filters(subject=subject, topic=topic)
