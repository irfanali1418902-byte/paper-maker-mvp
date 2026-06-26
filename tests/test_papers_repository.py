"""Basic tests for papers_repository."""

import json

from app.repositories import papers_repository


def test_insert_then_find_by_id(test_db):
    papers_repository.insert(
        paper_id="p1",
        subject="Mathematics",
        class_name="Grade 1",
        total_marks=42,
        question_ids=["q1", "q2", "q3"],
    )
    paper = papers_repository.find_by_id("p1")
    assert paper is not None
    assert paper["subject"] == "Mathematics"
    assert paper["class_name"] == "Grade 1"
    assert paper["total_marks"] == 42
    # question_ids stored as JSON-encoded string per current contract
    assert json.loads(paper["question_ids"]) == ["q1", "q2", "q3"]


def test_find_by_id_returns_none_when_missing(test_db):
    assert papers_repository.find_by_id("nope") is None


def test_insert_with_null_class_name(test_db):
    papers_repository.insert(
        paper_id="p1",
        subject="English",
        class_name=None,
        total_marks=10,
        question_ids=[],
    )
    paper = papers_repository.find_by_id("p1")
    assert paper["class_name"] is None
    assert json.loads(paper["question_ids"]) == []
