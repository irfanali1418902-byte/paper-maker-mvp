"""Tests for result_service — CSV template generation + results import."""

import io

import pandas as pd
import pytest

from app.repositories import papers_repository, questions_repository, result_repository
from app.services import result_service
from app.services.exceptions import ResultsValidationError


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


# ---- import_results --------------------------------------------------------


def _setup_paper_with_two_questions(test_db_fixture):
    """Two questions (Q1 max=3, Q2 max=5) and a paper that references them."""
    _insert_question("q1", marks=3)
    _insert_question("q2", marks=5)
    papers_repository.insert(
        paper_id="p1",
        subject="Math",
        class_name="C1",
        total_marks=8,
        question_ids=["q1", "q2"],
    )


def test_import_valid_csv_saves_per_cell_rows(test_db):
    _setup_paper_with_two_questions(test_db)
    csv = b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n" b"101,Ali,2,4\n" b"102,Bilal,3,5\n"
    result = result_service.import_results("p1", "results.csv", csv)
    # 2 students x 2 questions = 4 per-cell rows
    assert result["rows_saved"] == 4
    saved = result_repository.list_results_for_upload(result["upload_id"])
    assert len(saved) == 4
    assert {r["roll_no"] for r in saved} == {"101", "102"}
    # One Ali, Q1, marks_obtained=2 row should exist
    ali_q1 = [r for r in saved if r["roll_no"] == "101" and r["question_id"] == "q1"]
    assert len(ali_q1) == 1
    assert ali_q1[0]["marks_obtained"] == 2


def test_marks_exceeding_max_raises_validation_error(test_db):
    _setup_paper_with_two_questions(test_db)
    csv = b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n101,Ali,5,4\n"
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0]["row"] == 2  # spreadsheet row 2 = first data row
    assert "exceed max" in errors[0]["issue"]


def test_missing_roll_no_reported_with_row_number(test_db):
    _setup_paper_with_two_questions(test_db)
    csv = b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n" b",Ali,2,4\n" b"102,Bilal,3,5\n"
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    errors = exc_info.value.errors
    assert any(e["row"] == 2 and "roll_no" in e["issue"] for e in errors)


def test_all_errors_collected_in_one_pass(test_db):
    """Don't stop on first error — give the teacher every problem at once."""
    _setup_paper_with_two_questions(test_db)
    csv = (
        b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n"
        b",Ali,5,2\n"  # row 2: missing roll_no + Q1 exceeds max
        b"102,,2,4\n"  # row 3: missing student_name
        b"103,Bilal,-1,4\n"  # row 4: Q1 negative
    )
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    errors = exc_info.value.errors
    rows_with_errors = {e["row"] for e in errors}
    assert {2, 3, 4} <= rows_with_errors


def test_column_count_mismatch_reports_structural_error(test_db):
    _setup_paper_with_two_questions(test_db)
    # Missing the Q2 column entirely
    csv = b"roll_no,student_name,Q1 (marks: 3)\n101,Ali,2\n"
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    assert "Column count mismatch" in exc_info.value.errors[0]["issue"]


def test_first_two_columns_must_be_roll_no_and_student_name(test_db):
    _setup_paper_with_two_questions(test_db)
    csv = b"name,id,Q1 (marks: 3),Q2 (marks: 5)\nAli,101,2,4\n"
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    assert "First two columns" in exc_info.value.errors[0]["issue"]


def test_decimal_marks_rejected_as_non_whole(test_db):
    """Schema is INTEGER — a half-mark must not be silently truncated."""
    _setup_paper_with_two_questions(test_db)
    csv = b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n101,Ali,2.5,4\n"
    with pytest.raises(ResultsValidationError) as exc_info:
        result_service.import_results("p1", "r.csv", csv)
    assert any("whole number" in e["issue"] for e in exc_info.value.errors)


def test_unknown_paper_returns_none(test_db):
    csv = b"roll_no,student_name\n101,Ali\n"
    assert result_service.import_results("nope", "r.csv", csv) is None


def test_unsupported_extension_raises_value_error(test_db):
    _setup_paper_with_two_questions(test_db)
    with pytest.raises(ValueError, match="Unsupported file type"):
        result_service.import_results("p1", "r.txt", b"whatever")


def test_xlsx_path_parses_and_saves(test_db):
    """openpyxl wired up correctly — round-trip a DataFrame through xlsx bytes."""
    _setup_paper_with_two_questions(test_db)
    df = pd.DataFrame(
        {
            "roll_no": ["101", "102"],
            "student_name": ["Ali", "Bilal"],
            "Q1 (marks: 3)": [2, 3],
            "Q2 (marks: 5)": [4, 5],
        }
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    result = result_service.import_results("p1", "results.xlsx", buf.getvalue())
    assert result["rows_saved"] == 4


def test_validation_failure_writes_nothing_to_db(test_db):
    """All-or-nothing: even one bad row aborts the whole upload."""
    _setup_paper_with_two_questions(test_db)
    csv = (
        b"roll_no,student_name,Q1 (marks: 3),Q2 (marks: 5)\n"
        b"101,Ali,2,4\n"  # valid
        b"102,Bilal,99,5\n"  # Q1 exceeds max
    )
    with pytest.raises(ResultsValidationError):
        result_service.import_results("p1", "r.csv", csv)
    # No upload row should have been created for this paper
    assert result_repository.list_uploads_for_paper("p1") == []
