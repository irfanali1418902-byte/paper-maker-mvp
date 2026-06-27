"""Tests for dashboard_service — aggregation math over uploaded results."""

from app.repositories import papers_repository, questions_repository, result_repository
from app.services import dashboard_service


def _insert_question(qid: str, marks: int, bloom_level: str = "REMEMBER"):
    questions_repository.insert(
        {
            "id": qid,
            "subject": "Math",
            "topic": "T",
            "bloom_level": bloom_level,
            "difficulty": "easy",
            "question_type": "multiple-choice",
            "marks": marks,
            "question_en": None,
            "question_ur": None,
            "options_en": None,
            "options_ur": None,
            "correct_answer_en": None,
            "correct_answer_ur": None,
            "explanation_en": None,
            "explanation_ur": None,
            "visual_emoji": None,
            "visual_count": None,
        }
    )


def _seed_upload(rows: list[dict], question_ids: list[str]) -> str:
    """Creates an upload with the given per-cell rows. Each row dict:
    {roll_no, student_name, marks: {qid: obtained}}. Returns upload_id."""
    upload_id = "u1"
    result_repository.insert_upload(upload_id=upload_id, paper_id="p1", filename="f.csv")
    for r in rows:
        for qid in question_ids:
            result_repository.insert_student_result(
                result_id=f"{r['roll_no']}-{qid}",
                result_upload_id=upload_id,
                roll_no=r["roll_no"],
                student_name=r["student_name"],
                question_id=qid,
                marks_obtained=r["marks"][qid],
            )
    return upload_id


def _setup(test_db):
    """Q1 max=3 (REMEMBER), Q2 max=5 (ANALYZE); paper p1 references both."""
    _insert_question("q1", marks=3, bloom_level="REMEMBER")
    _insert_question("q2", marks=5, bloom_level="ANALYZE")
    papers_repository.insert(
        paper_id="p1", subject="Math", class_name="C1", total_marks=8, question_ids=["q1", "q2"]
    )


def test_unknown_upload_returns_none(test_db):
    assert dashboard_service.get_dashboard_for_upload("nope") is None


def test_list_uploads_unknown_paper_returns_none(test_db):
    assert dashboard_service.list_uploads("nope") is None


def test_list_uploads_empty_for_paper_with_no_results(test_db):
    _setup(test_db)
    assert dashboard_service.list_uploads("p1") == []


def test_student_totals_and_percent(test_db):
    _setup(test_db)
    uid = _seed_upload(
        [
            {"roll_no": "101", "student_name": "Ali", "marks": {"q1": 3, "q2": 5}},  # 8/8 = 100%
            {"roll_no": "102", "student_name": "Bilal", "marks": {"q1": 1, "q2": 1}},  # 2/8 = 25%
        ],
        ["q1", "q2"],
    )
    dash = dashboard_service.get_dashboard_for_upload(uid)
    students = {s["roll_no"]: s for s in dash["students"]}
    assert students["101"]["marks_obtained"] == 8
    assert students["101"]["percent"] == 100.0
    assert students["101"]["total_marks"] == 8
    assert students["102"]["percent"] == 25.0


def test_ranking_is_competition_style_with_ties(test_db):
    _setup(test_db)
    uid = _seed_upload(
        [
            {"roll_no": "101", "student_name": "A", "marks": {"q1": 3, "q2": 5}},  # 8 -> rank 1
            {
                "roll_no": "102",
                "student_name": "B",
                "marks": {"q1": 3, "q2": 5},
            },  # 8 -> rank 1 (tie)
            {"roll_no": "103", "student_name": "C", "marks": {"q1": 0, "q2": 0}},  # 0 -> rank 3
        ],
        ["q1", "q2"],
    )
    dash = dashboard_service.get_dashboard_for_upload(uid)
    ranks = {s["roll_no"]: s["rank"] for s in dash["students"]}
    assert ranks["101"] == 1
    assert ranks["102"] == 1
    assert ranks["103"] == 3  # 1,1,3 not 1,1,2


def test_pass_count_uses_33_percent_threshold(test_db):
    _setup(test_db)
    # 3/8 = 37.5% passes; 2/8 = 25% fails.
    uid = _seed_upload(
        [
            {"roll_no": "101", "student_name": "A", "marks": {"q1": 3, "q2": 0}},  # 37.5%
            {"roll_no": "102", "student_name": "B", "marks": {"q1": 2, "q2": 0}},  # 25%
        ],
        ["q1", "q2"],
    )
    summary = dashboard_service.get_dashboard_for_upload(uid)["summary"]
    assert summary["pass_count"] == 1
    assert summary["pass_threshold_percent"] == 33.0
    assert summary["pass_percent"] == 50.0
    assert summary["highest_percent"] == 37.5
    assert summary["lowest_percent"] == 25.0


def test_question_stats_average_and_full_marks_count(test_db):
    _setup(test_db)
    uid = _seed_upload(
        [
            {"roll_no": "101", "student_name": "A", "marks": {"q1": 3, "q2": 2}},
            {"roll_no": "102", "student_name": "B", "marks": {"q1": 1, "q2": 4}},
        ],
        ["q1", "q2"],
    )
    stats = {
        q["question_index"]: q for q in dashboard_service.get_dashboard_for_upload(uid)["questions"]
    }
    # Q1: (3+1)/2 = 2.0 avg, one student got full marks (3)
    assert stats[1]["average_marks"] == 2.0
    assert stats[1]["full_marks_count"] == 1
    assert stats[1]["student_count"] == 2
    # Q2: (2+4)/2 = 3.0 avg out of 5 = 60%
    assert stats[2]["average_marks"] == 3.0
    assert stats[2]["average_percent"] == 60.0


def test_bloom_breakdown_groups_by_level(test_db):
    _setup(test_db)
    uid = _seed_upload(
        [
            {"roll_no": "101", "student_name": "A", "marks": {"q1": 3, "q2": 1}},
            {"roll_no": "102", "student_name": "B", "marks": {"q1": 3, "q2": 1}},
        ],
        ["q1", "q2"],
    )
    blooms = {
        b["bloom_level"]: b
        for b in dashboard_service.get_dashboard_for_upload(uid)["bloom_breakdown"]
    }
    # REMEMBER (Q1, max 3): everyone scored 3 -> 100%
    assert blooms["REMEMBER"]["average_percent"] == 100.0
    assert blooms["REMEMBER"]["max_marks"] == 3
    # ANALYZE (Q2, max 5): everyone scored 1 -> 20%
    assert blooms["ANALYZE"]["average_percent"] == 20.0
    assert blooms["ANALYZE"]["question_count"] == 1


def test_latest_dashboard_picks_most_recent_upload(test_db):
    _setup(test_db)
    # Two uploads; the most recent (by uploaded_at) should win. Insert order
    # alone isn't enough since timestamps can tie, so assert against whatever
    # list_uploads_for_paper returns first.
    result_repository.insert_upload(upload_id="old", paper_id="p1", filename="old.csv")
    result_repository.insert_upload(upload_id="new", paper_id="p1", filename="new.csv")
    for qid, marks in [("q1", 3), ("q2", 5)]:
        result_repository.insert_student_result(
            result_id=f"new-{qid}",
            result_upload_id="new",
            roll_no="101",
            student_name="A",
            question_id=qid,
            marks_obtained=marks,
        )
    latest_upload_id = result_repository.list_uploads_for_paper("p1")[0]["id"]
    dash = dashboard_service.get_latest_dashboard_for_paper("p1")
    assert dash["upload"]["id"] == latest_upload_id


def test_latest_dashboard_none_when_no_uploads(test_db):
    _setup(test_db)
    assert dashboard_service.get_latest_dashboard_for_paper("p1") is None
