"""Orchestrates paper assembly from the question bank."""

import json
import uuid

from app.models.requests import GeneratePaperRequest
from app.repositories import papers_repository, questions_repository
from app.services import bloom_service, item_analysis_service


def assemble_balanced_paper(req: GeneratePaperRequest) -> dict | None:
    """Picks Bloom-balanced questions (least-used first), bumps their
    usage_count, persists the paper. Returns the paper dict, or None if no
    questions matched any bucket (caller maps that to 404)."""
    distribution = bloom_service.calculate_bloom_distribution(
        req.bloom_distribution, req.total_questions
    )
    selected_ids: list[str] = []
    selected_questions: list[dict] = []

    for level, count in distribution.items():
        if count <= 0:
            continue
        rows = questions_repository.find_least_used(
            subject=req.subject,
            bloom_level=level,
            difficulty=req.difficulty,
            limit=count,
        )
        for row in rows:
            selected_ids.append(row["id"])
            selected_questions.append(row)
            questions_repository.increment_usage_count(row["id"])

    if not selected_questions:
        return None

    _annotate_expected_difficulty(selected_questions)

    paper_id = str(uuid.uuid4())
    total_marks = sum(q["marks"] for q in selected_questions)
    papers_repository.insert(
        paper_id=paper_id,
        subject=req.subject,
        class_name=req.class_name,
        total_marks=total_marks,
        question_ids=selected_ids,
    )
    return {
        "paper_id": paper_id,
        "total_marks": total_marks,
        "questions": selected_questions,
        "balance_summary": item_analysis_service.summarize_paper_balance(selected_questions),
    }


def get_paper_with_questions(paper_id: str) -> dict | None:
    paper = papers_repository.find_by_id(paper_id)
    if not paper:
        return None
    question_ids = json.loads(paper["question_ids"])
    questions: list[dict] = []
    for qid in question_ids:
        q = questions_repository.find_by_id(qid)
        if q:
            questions.append(q)
    _annotate_expected_difficulty(questions)
    return {
        "paper": paper,
        "questions": questions,
        "balance_summary": item_analysis_service.summarize_paper_balance(questions),
    }


def _annotate_expected_difficulty(questions: list[dict]) -> None:
    """Har question dict mein Bloom-derived expected_difficulty aur stored
    difficulty ke saath mismatch flag add karta hai (in-place)."""
    for q in questions:
        q["expected_difficulty"] = item_analysis_service.expected_difficulty(q["bloom_level"])
        q["difficulty_mismatch"] = item_analysis_service.is_difficulty_mismatch(
            q.get("difficulty"), q["bloom_level"]
        )
