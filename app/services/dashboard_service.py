"""Result analyzer dashboard service (Phase 2).

Turns the raw per-student per-question rows that result_service saved into
the aggregates a teacher actually reads off a dashboard:

  - class summary (average %, pass rate, top/bottom)
  - per-student totals with ranking
  - per-question difficulty (which questions the class struggled with)
  - per-Bloom-level breakdown (which cognitive levels are weak)

Everything is read-only. We join across result_repository (the marks),
papers_repository (which questions, in what order) and questions_repository
(each question's max marks + Bloom level) here in the service — repositories
stay single-table.
"""

import json
from typing import Optional

from app.repositories import papers_repository, questions_repository, result_repository
from app.services import item_analysis_service

# KPK board ka standard passing mark 33% hai. Business rule hai, isiliye
# service mein — agar koi school apna threshold chahe to yahin badlega.
PASS_PERCENT_THRESHOLD = 33.0


def list_uploads(paper_id: str) -> Optional[list[dict]]:
    """Uploads for a paper, newest first. Returns None if the paper doesn't
    exist (route maps to 404); an empty list means the paper exists but has
    no results uploaded yet."""
    if papers_repository.find_by_id(paper_id) is None:
        return None
    return result_repository.list_uploads_for_paper(paper_id)


def get_dashboard_for_upload(upload_id: str) -> Optional[dict]:
    """Full dashboard for one specific upload. None if the upload (or its
    paper) doesn't exist — route maps to 404."""
    upload = result_repository.find_upload_by_id(upload_id)
    if upload is None:
        return None
    paper = papers_repository.find_by_id(upload["paper_id"])
    if paper is None:
        return None
    return _build_dashboard(upload, paper)


def get_latest_dashboard_for_paper(paper_id: str) -> Optional[dict]:
    """Dashboard for a paper's most recent upload — the common case where the
    frontend just has a paper_id. None if the paper doesn't exist or has no
    uploads yet (route maps to 404)."""
    if papers_repository.find_by_id(paper_id) is None:
        return None
    uploads = result_repository.list_uploads_for_paper(paper_id)
    if not uploads:
        return None
    return get_dashboard_for_upload(uploads[0]["id"])


def _build_dashboard(upload: dict, paper: dict) -> dict:
    # Questions in paper order — index 1..N matches the Q-columns the teacher
    # filled in, so dashboard labels line up with the printed paper.
    question_ids = json.loads(paper["question_ids"])
    questions: list[dict] = []
    for idx, qid in enumerate(question_ids, start=1):
        q = questions_repository.find_by_id(qid)
        if q is not None:
            questions.append(
                {"index": idx, "id": qid, "marks": q["marks"], "bloom_level": q["bloom_level"]}
            )

    total_marks = sum(q["marks"] for q in questions)

    rows = result_repository.list_results_for_upload(upload["id"])

    students = _aggregate_students(rows, total_marks)
    question_stats = _aggregate_questions(rows, questions, students)
    bloom_breakdown = _aggregate_blooms(question_stats)
    summary = _build_summary(students, total_marks)

    return {
        "upload": upload,
        "summary": summary,
        "students": students,
        "questions": question_stats,
        "bloom_breakdown": bloom_breakdown,
    }


def _aggregate_students(rows: list[dict], total_marks: int) -> list[dict]:
    """Per-student totals + competition ranking (ties share a rank)."""
    by_roll: dict[str, dict] = {}
    for r in rows:
        roll = r["roll_no"]
        student = by_roll.setdefault(
            roll, {"roll_no": roll, "student_name": r.get("student_name"), "marks_obtained": 0}
        )
        student["marks_obtained"] += r["marks_obtained"]

    students = list(by_roll.values())
    for s in students:
        s["total_marks"] = total_marks
        s["percent"] = _percent(s["marks_obtained"], total_marks)

    students.sort(key=lambda s: s["marks_obtained"], reverse=True)

    # Standard competition ranking: 1, 2, 2, 4. Equal marks => equal rank.
    last_marks = None
    last_rank = 0
    for position, s in enumerate(students, start=1):
        if s["marks_obtained"] != last_marks:
            last_rank = position
            last_marks = s["marks_obtained"]
        s["rank"] = last_rank

    return students


def _aggregate_questions(
    rows: list[dict], questions: list[dict], students: list[dict]
) -> list[dict]:
    """Per-question average + full-marks count, plus the psychometric indices:
    Difficulty Index (P-value) and Discrimination Index (D). D needs each
    student's total score, so we pass `students` (already totalled) in."""
    obtained_by_q: dict[str, list[int]] = {q["id"]: [] for q in questions}
    # Per question, one (student_total, marks_on_this_question) pair per row —
    # the input the discrimination index works on.
    scores_by_q: dict[str, list[tuple[float, float]]] = {q["id"]: [] for q in questions}
    total_by_roll = {s["roll_no"]: s["marks_obtained"] for s in students}

    for r in rows:
        qid = r["question_id"]
        if qid in obtained_by_q:
            obtained_by_q[qid].append(r["marks_obtained"])
            scores_by_q[qid].append((total_by_roll.get(r["roll_no"], 0), r["marks_obtained"]))

    stats: list[dict] = []
    for q in questions:
        marks_list = obtained_by_q[q["id"]]
        attempts = len(marks_list)
        max_marks = q["marks"]
        avg_marks = sum(marks_list) / attempts if attempts else 0.0

        p_value = item_analysis_service.difficulty_index(avg_marks, max_marks)
        d_index = item_analysis_service.discrimination_index(scores_by_q[q["id"]], max_marks)
        d_reliable = item_analysis_service.is_d_reliable(attempts)
        p_band = item_analysis_service.classify_p(p_value)
        d_band = item_analysis_service.classify_d(d_index)

        stats.append(
            {
                "question_index": q["index"],
                "question_id": q["id"],
                "bloom_level": q["bloom_level"],
                "max_marks": max_marks,
                "student_count": attempts,
                "average_marks": round(avg_marks, 2),
                "average_percent": _percent(avg_marks, max_marks),
                "full_marks_count": sum(1 for m in marks_list if m == max_marks),
                "p_value": p_value,
                "p_band": p_band,
                "d_index": d_index,
                "d_band": d_band,
                "d_reliable": d_reliable,
                "flag": item_analysis_service.flag_question(p_band, d_band, d_reliable),
            }
        )
    return stats


def _aggregate_blooms(question_stats: list[dict]) -> list[dict]:
    """Roll per-question averages up to Bloom level — weighted by each
    question's max marks so a 5-mark ANALYZE question counts more than a
    1-mark one."""
    by_bloom: dict[str, dict] = {}
    for q in question_stats:
        level = q["bloom_level"]
        bucket = by_bloom.setdefault(
            level, {"bloom_level": level, "question_count": 0, "max_marks": 0, "obtained": 0.0}
        )
        bucket["question_count"] += 1
        bucket["max_marks"] += q["max_marks"]
        # average_marks is per-student; summing across a level's questions
        # gives the average a student scores on that whole level.
        bucket["obtained"] += q["average_marks"]

    breakdown: list[dict] = []
    for bucket in by_bloom.values():
        breakdown.append(
            {
                "bloom_level": bucket["bloom_level"],
                "question_count": bucket["question_count"],
                "max_marks": bucket["max_marks"],
                "average_marks": round(bucket["obtained"], 2),
                "average_percent": _percent(bucket["obtained"], bucket["max_marks"]),
            }
        )
    return breakdown


def _build_summary(students: list[dict], total_marks: int) -> dict:
    student_count = len(students)
    if student_count == 0:
        return {
            "student_count": 0,
            "total_marks": total_marks,
            "class_average_marks": 0.0,
            "class_average_percent": 0.0,
            "highest_percent": 0.0,
            "lowest_percent": 0.0,
            "pass_count": 0,
            "pass_percent": 0.0,
            "pass_threshold_percent": PASS_PERCENT_THRESHOLD,
        }

    percents = [s["percent"] for s in students]
    avg_marks = sum(s["marks_obtained"] for s in students) / student_count
    pass_count = sum(1 for p in percents if p >= PASS_PERCENT_THRESHOLD)

    return {
        "student_count": student_count,
        "total_marks": total_marks,
        "class_average_marks": round(avg_marks, 2),
        "class_average_percent": _percent(avg_marks, total_marks),
        "highest_percent": max(percents),
        "lowest_percent": min(percents),
        "pass_count": pass_count,
        "pass_percent": _percent(pass_count, student_count),
        "pass_threshold_percent": PASS_PERCENT_THRESHOLD,
    }


def _percent(part: float, whole: float) -> float:
    """Guarded percentage, 1 decimal. whole == 0 (no questions / no students)
    yields 0.0 instead of a ZeroDivisionError."""
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 1)
