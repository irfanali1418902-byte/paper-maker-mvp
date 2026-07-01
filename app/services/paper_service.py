"""Orchestrates paper assembly from the question bank."""

import json
import uuid

from app.repositories import papers_repository, questions_repository
from app.schemas.requests import AdaptivePaperRequest, GeneratePaperRequest
from app.services import adaptive_service, bloom_service, dashboard_service, item_analysis_service


def assemble_balanced_paper(req: GeneratePaperRequest) -> dict | None:
    """Picks Bloom-balanced questions (least-used first), bumps their
    usage_count, persists the paper. Returns the paper dict, or None if no
    questions matched any bucket (caller maps that to 404)."""
    distribution = bloom_service.calculate_bloom_distribution(
        req.bloom_distribution, req.total_questions
    )
    selected_ids, selected_questions = _pick_questions(req.subject, distribution, req.difficulty)
    if not selected_questions:
        return None

    paper_id, total_marks = _persist_paper(
        req.subject, req.class_name, selected_ids, selected_questions
    )
    return {
        "paper_id": paper_id,
        "total_marks": total_marks,
        "questions": selected_questions,
        "balance_summary": item_analysis_service.summarize_paper_balance(selected_questions),
    }


def assemble_adaptive_paper(req: AdaptivePaperRequest) -> dict | None:
    """Builds a paper weighted toward the Bloom levels a class scored worst on,
    learned from the source paper's latest results upload. Returns None (caller
    maps to 404) if the source paper/results don't exist or the bank is empty."""
    source_paper = papers_repository.find_by_id(req.source_paper_id)
    if source_paper is None:
        return None
    dashboard = dashboard_service.get_latest_dashboard_for_paper(req.source_paper_id)
    if dashboard is None or not dashboard["bloom_breakdown"]:
        return None

    subject = source_paper["subject"]
    breakdown = dashboard["bloom_breakdown"]
    distribution = adaptive_service.build_adaptive_distribution(breakdown, req.total_questions)

    selected_ids, selected_questions = _pick_questions(subject, distribution, req.difficulty)
    if not selected_questions:
        return None

    paper_id, total_marks = _persist_paper(
        subject, req.class_name, selected_ids, selected_questions
    )
    return {
        "paper_id": paper_id,
        "total_marks": total_marks,
        "questions": selected_questions,
        "balance_summary": item_analysis_service.summarize_paper_balance(selected_questions),
        "adaptive_summary": adaptive_service.summarize(breakdown, distribution),
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


def replace_question(paper_id: str, old_question_id: str, new_question_id: str) -> dict | None:
    """Swap one question in a paper for another from the bank, in place (order
    preserved), recompute total_marks, and persist. Returns the updated paper
    dict (same shape as assemble_balanced_paper), or None if the paper doesn't
    exist (route maps to 404). Raises ValueError for bad question ids (400)."""
    paper = papers_repository.find_by_id(paper_id)
    if paper is None:
        return None

    question_ids = json.loads(paper["question_ids"])
    if old_question_id not in question_ids:
        raise ValueError("Purana question is paper mein nahi hai.")
    if questions_repository.find_by_id(new_question_id) is None:
        raise ValueError("Naya question bank mein nahi mila.")

    question_ids[question_ids.index(old_question_id)] = new_question_id

    questions: list[dict] = []
    for qid in question_ids:
        q = questions_repository.find_by_id(qid)
        if q:
            questions.append(q)
    _annotate_expected_difficulty(questions)
    total_marks = sum(q["marks"] for q in questions)

    papers_repository.update_question_ids(paper_id, question_ids, total_marks)
    questions_repository.increment_usage_count(new_question_id)

    return {
        "paper_id": paper_id,
        "total_marks": total_marks,
        "questions": questions,
        "balance_summary": item_analysis_service.summarize_paper_balance(questions),
    }


def _pick_questions(
    subject: str, distribution: dict, difficulty: str | None
) -> tuple[list[str], list[dict]]:
    """Pick least-used questions per Bloom level for the given distribution,
    bumping each picked question's usage_count. Shared by balanced + adaptive."""
    selected_ids: list[str] = []
    selected_questions: list[dict] = []
    for level, count in distribution.items():
        if count <= 0:
            continue
        rows = questions_repository.find_least_used(
            subject=subject, bloom_level=level, difficulty=difficulty, limit=count
        )
        for row in rows:
            selected_ids.append(row["id"])
            selected_questions.append(row)
            questions_repository.increment_usage_count(row["id"])
    return selected_ids, selected_questions


def _persist_paper(
    subject: str, class_name: str | None, selected_ids: list[str], selected_questions: list[dict]
) -> tuple[str, int]:
    """Annotate expected difficulty, persist the paper row, return (id, marks)."""
    _annotate_expected_difficulty(selected_questions)
    paper_id = str(uuid.uuid4())
    total_marks = sum(q["marks"] for q in selected_questions)
    papers_repository.insert(
        paper_id=paper_id,
        subject=subject,
        class_name=class_name,
        total_marks=total_marks,
        question_ids=selected_ids,
    )
    return paper_id, total_marks


def _annotate_expected_difficulty(questions: list[dict]) -> None:
    """Har question dict mein Bloom-derived expected_difficulty aur stored
    difficulty ke saath mismatch flag add karta hai (in-place)."""
    for q in questions:
        q["expected_difficulty"] = item_analysis_service.expected_difficulty(q["bloom_level"])
        q["difficulty_mismatch"] = item_analysis_service.is_difficulty_mismatch(
            q.get("difficulty"), q["bloom_level"]
        )
