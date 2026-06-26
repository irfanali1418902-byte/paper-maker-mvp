"""Basic CRUD-shape tests for questions_repository against a temp DB."""

import json

from app.repositories import questions_repository


def _sample_question(
    qid: str = "q1",
    subject: str = "Mathematics",
    topic: str = "Counting",
    bloom_level: str = "REMEMBER",
    difficulty: str = "easy",
) -> dict:
    """Builds a fully-populated question row for insertion."""
    return {
        "id": qid,
        "subject": subject,
        "topic": topic,
        "bloom_level": bloom_level,
        "difficulty": difficulty,
        "question_type": "multiple-choice",
        "marks": 1,
        "question_en": "What is 2+2?",
        "question_ur": "دو جمع دو کتنا ہے؟",
        "options_en": json.dumps(["3", "4", "5", "6"]),
        "options_ur": json.dumps(["3", "4", "5", "6"]),
        "correct_answer_en": "4",
        "correct_answer_ur": "4",
        "explanation_en": "Basic addition",
        "explanation_ur": "بنیادی جمع",
        "visual_emoji": None,
        "visual_count": None,
    }


def test_insert_then_find_by_id(test_db):
    questions_repository.insert(_sample_question(qid="q1"))
    found = questions_repository.find_by_id("q1")
    assert found is not None
    assert found["subject"] == "Mathematics"
    assert found["marks"] == 1
    assert found["usage_count"] == 0  # column default


def test_find_by_id_returns_none_when_missing(test_db):
    assert questions_repository.find_by_id("does-not-exist") is None


def test_list_by_filters_filters_by_subject(test_db):
    questions_repository.insert(_sample_question(qid="q1", subject="Mathematics"))
    questions_repository.insert(_sample_question(qid="q2", subject="English"))

    math_qs = questions_repository.list_by_filters(subject="Mathematics")
    assert len(math_qs) == 1
    assert math_qs[0]["id"] == "q1"


def test_list_by_filters_no_args_returns_all(test_db):
    questions_repository.insert(_sample_question(qid="q1"))
    questions_repository.insert(_sample_question(qid="q2", topic="Shapes"))
    assert len(questions_repository.list_by_filters()) == 2


def test_increment_usage_count(test_db):
    questions_repository.insert(_sample_question(qid="q1"))
    assert questions_repository.find_by_id("q1")["usage_count"] == 0

    questions_repository.increment_usage_count("q1")
    questions_repository.increment_usage_count("q1")
    assert questions_repository.find_by_id("q1")["usage_count"] == 2


def test_find_least_used_orders_by_usage_count_ascending(test_db):
    """Paper assembly's least-used-first contract — q3 (untouched) should
    come before q2 (bumped once) and q1 (bumped twice)."""
    questions_repository.insert(_sample_question(qid="q1"))
    questions_repository.insert(_sample_question(qid="q2"))
    questions_repository.insert(_sample_question(qid="q3"))

    questions_repository.increment_usage_count("q1")
    questions_repository.increment_usage_count("q1")
    questions_repository.increment_usage_count("q2")

    rows = questions_repository.find_least_used(
        subject="Mathematics",
        bloom_level="REMEMBER",
        difficulty="easy",
        limit=3,
    )
    assert [r["id"] for r in rows] == ["q3", "q2", "q1"]


def test_find_least_used_respects_limit(test_db):
    for i in range(5):
        questions_repository.insert(_sample_question(qid=f"q{i}"))
    rows = questions_repository.find_least_used(
        subject="Mathematics",
        bloom_level="REMEMBER",
        difficulty="easy",
        limit=2,
    )
    assert len(rows) == 2


def test_find_least_used_with_none_difficulty_matches_all(test_db):
    questions_repository.insert(_sample_question(qid="q1", difficulty="easy"))
    questions_repository.insert(_sample_question(qid="q2", difficulty="hard"))

    rows = questions_repository.find_least_used(
        subject="Mathematics",
        bloom_level="REMEMBER",
        difficulty=None,
        limit=10,
    )
    assert len(rows) == 2
