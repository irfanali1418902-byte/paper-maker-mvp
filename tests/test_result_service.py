"""Tests for result_service — CSV template generation."""

from app.repositories import papers_repository, questions_repository
from app.services import result_service


def _insert_question(qid: str, marks: int):
    """Minimal valid question row — only the fields we exercise in these tests
    need real values; the rest can be None or placeholders."""
    questions_repository.insert(
        {
            "id": qid,
            "subject": "Math",
            "topic": "T",
            "bloom_level": "REMEMBER",
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


def test_csv_header_has_roll_no_student_name_and_question_columns(test_db):
    _insert_question("q1", marks=2)
    _insert_question("q2", marks=5)
    papers_repository.insert(
        paper_id="p1",
        subject="Math",
        class_name="C1",
        total_marks=7,
        question_ids=["q1", "q2"],
    )

    csv_bytes = result_service.build_result_template_csv("p1")
    assert csv_bytes is not None
    header = csv_bytes.decode("utf-8").splitlines()[0]
    # Columns must be in the documented order: roll_no, student_name, then
    # one Q-column per question with max marks embedded.
    assert header == "roll_no,student_name,Q1 (marks: 2),Q2 (marks: 5)"


def test_csv_is_header_only_no_data_rows(test_db):
    _insert_question("q1", marks=3)
    papers_repository.insert(
        paper_id="p1",
        subject="Math",
        class_name="C1",
        total_marks=3,
        question_ids=["q1"],
    )

    csv_bytes = result_service.build_result_template_csv("p1")
    lines = csv_bytes.decode("utf-8").splitlines()
    # An empty pandas frame with named columns serializes as just the header.
    assert len(lines) == 1


def test_question_order_matches_paper_question_ids_order(test_db):
    """Paper.question_ids is the canonical ordering; columns must follow
    that even if the questions table returns rows in some other order."""
    _insert_question("qA", marks=1)
    _insert_question("qB", marks=10)
    papers_repository.insert(
        paper_id="p1",
        subject="Math",
        class_name="C1",
        total_marks=11,
        question_ids=["qB", "qA"],  # B first, A second
    )

    csv_bytes = result_service.build_result_template_csv("p1")
    header = csv_bytes.decode("utf-8").splitlines()[0]
    # Q1 should map to qB (marks 10), Q2 to qA (marks 1)
    assert "Q1 (marks: 10)" in header
    assert "Q2 (marks: 1)" in header


def test_returns_none_for_unknown_paper(test_db):
    assert result_service.build_result_template_csv("does-not-exist") is None
