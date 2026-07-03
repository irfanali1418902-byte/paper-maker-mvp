"""Orchestrates paper assembly from the question bank."""

import json
import uuid

from app.repositories import papers_repository, questions_repository
from app.schemas.requests import AdaptivePaperRequest, GeneratePaperRequest
from app.services import adaptive_service, bloom_service, dashboard_service, item_analysis_service
from app.services.exceptions import QuestionBankEmpty

# paper_type -> allowed question_type values. None = koi filter nahi (sab types).
# "subjective" ka inclusion-list rakha hai (na ke "not mcq") taake generation ki
# vocabulary controlled rahe; naye subjective type aayein to yahan add karo.
_PAPER_TYPE_FILTERS: dict[str, list[str] | None] = {
    "mcq": ["multiple-choice"],
    "subjective": ["short-answer", "essay"],
    "mixed": None,
}

# custom-ratio ke do groups jinke beech ratio banta hai. MCQ group deliberately
# true-false ko bhi shamil karta hai (objective questions) — ye _PAPER_TYPE_FILTERS
# ke "mcq" (sirf multiple-choice) se alag hai, aur ye jaan-boojh kar hai.
_RATIO_MCQ_GROUP = ["multiple-choice", "true-false"]
_RATIO_SUBJECTIVE_GROUP = ["short-answer", "essay"]


def assemble_balanced_paper(req: GeneratePaperRequest) -> dict | None:
    """Picks Bloom-balanced questions (least-used first), bumps their
    usage_count, persists the paper. Returns the paper dict, or None if no
    questions matched any bucket (caller maps that to 404)."""
    if req.paper_type == "custom-ratio":
        return _assemble_by_ratio(req)

    distribution = bloom_service.calculate_bloom_distribution(
        req.bloom_distribution, req.total_questions
    )
    question_types = _PAPER_TYPE_FILTERS.get(req.paper_type)
    selected_ids, selected_questions = _pick_questions(
        req.subject, distribution, req.difficulty, question_types
    )
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

    question_types = _PAPER_TYPE_FILTERS.get(req.paper_type)
    selected_ids, selected_questions = _pick_questions(
        subject, distribution, req.difficulty, question_types
    )
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


def _assemble_by_ratio(req: GeneratePaperRequest) -> dict | None:
    """custom-ratio: total_questions ko MCQ vs Subjective groups mein mcq_percent
    ke hisaab se baant kar, har group ke andar wahi Bloom distribution laga kar
    questions pick karta hai. Ek group ke liye questions bilkul na milein to
    QuestionBankEmpty (group-named message) raise hoti hai."""
    if req.mcq_percent is None:
        raise ValueError("custom-ratio ke liye mcq_percent (0-100) dena zaroori hai.")

    mcq_count, subj_count = _split_by_ratio(req.total_questions, req.mcq_percent)

    selected_ids: list[str] = []
    selected_questions: list[dict] = []
    for group_count, group_types, group_label in (
        (mcq_count, _RATIO_MCQ_GROUP, "MCQ"),
        (subj_count, _RATIO_SUBJECTIVE_GROUP, "Subjective"),
    ):
        if group_count <= 0:
            continue
        distribution = bloom_service.calculate_bloom_distribution(
            req.bloom_distribution, group_count
        )
        ids, questions = _pick_questions(req.subject, distribution, req.difficulty, group_types)
        if not questions:
            raise QuestionBankEmpty(
                f"Is subject mein {group_label} questions kaafi nahi (chahiye the {group_count}). "
                "Pehle us type ke questions generate karo, ya ratio badlo."
            )
        selected_ids.extend(ids)
        selected_questions.extend(questions)

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


def _split_by_ratio(total: int, mcq_percent: int) -> tuple[int, int]:
    """total ko (mcq_count, subjective_count) mein baanto. Half-up rounding MCQ par;
    subjective = total - mcq taake sum hamesha exact rahe (koi rounding drift nahi)."""
    mcq = int(total * mcq_percent / 100 + 0.5)
    mcq = max(0, min(total, mcq))  # clamp (defensive; percent Pydantic se 0-100 aata hai)
    return mcq, total - mcq


def _pick_questions(
    subject: str,
    distribution: dict,
    difficulty: str | None,
    question_types: list[str] | None = None,
) -> tuple[list[str], list[dict]]:
    """Pick least-used questions per Bloom level for the given distribution,
    bumping each picked question's usage_count. Shared by balanced + adaptive.
    question_types diya jaye to sirf un types se pick hota hai (paper_type filter)."""
    selected_ids: list[str] = []
    selected_questions: list[dict] = []
    for level, count in distribution.items():
        if count <= 0:
            continue
        rows = questions_repository.find_least_used(
            subject=subject,
            bloom_level=level,
            difficulty=difficulty,
            limit=count,
            question_types=question_types,
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
