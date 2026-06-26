"""Basic tests for result_repository — covers both result_uploads and
student_question_results.

Note: SQLite's REFERENCES clauses are declared on the new tables but
PRAGMA foreign_keys is not turned on by init_db, so we can use synthetic
paper_id / question_id values here without inserting parent rows.
"""

from app.repositories import result_repository

# ---- result_uploads --------------------------------------------------------


def test_insert_upload_then_find_by_id(test_db):
    result_repository.insert_upload(
        upload_id="u1",
        paper_id="paper-1",
        filename="results_class1.csv",
    )
    upload = result_repository.find_upload_by_id("u1")
    assert upload is not None
    assert upload["paper_id"] == "paper-1"
    assert upload["filename"] == "results_class1.csv"
    assert upload["uploaded_at"] is not None  # DEFAULT CURRENT_TIMESTAMP populated


def test_find_upload_by_id_returns_none_when_missing(test_db):
    assert result_repository.find_upload_by_id("nope") is None


def test_list_uploads_for_paper_filters_correctly(test_db):
    result_repository.insert_upload(upload_id="u1", paper_id="p1", filename="a.csv")
    result_repository.insert_upload(upload_id="u2", paper_id="p1", filename="b.csv")
    result_repository.insert_upload(upload_id="u3", paper_id="p2", filename="c.csv")

    p1_uploads = result_repository.list_uploads_for_paper("p1")
    assert len(p1_uploads) == 2
    assert {u["id"] for u in p1_uploads} == {"u1", "u2"}


# ---- student_question_results ----------------------------------------------


def test_insert_student_result_then_list(test_db):
    result_repository.insert_upload(upload_id="u1", paper_id="p1", filename="a.csv")
    result_repository.insert_student_result(
        result_id="r1",
        result_upload_id="u1",
        roll_no="101",
        student_name="Ali",
        question_id="q1",
        marks_obtained=3,
    )
    result_repository.insert_student_result(
        result_id="r2",
        result_upload_id="u1",
        roll_no="101",
        student_name="Ali",
        question_id="q2",
        marks_obtained=5,
    )

    results = result_repository.list_results_for_upload("u1")
    assert len(results) == 2
    assert sum(r["marks_obtained"] for r in results) == 8


def test_list_results_for_upload_returns_empty_for_unknown(test_db):
    assert result_repository.list_results_for_upload("nonexistent") == []
