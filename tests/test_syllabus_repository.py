"""Basic tests for syllabus_repository."""
import pytest

from app.repositories import syllabus_repository


def _insert_topic(topic_id="t1", subject="Mathematics", grade="Grade 1",
                  unit_no=1, subtopic_title="Counting 1-5",
                  activity_type="Practice", page_no=10):
    syllabus_repository.insert(
        topic_id=topic_id, subject=subject, grade=grade,
        unit_no=unit_no, unit_title="Numbers", page_range="1-20",
        subtopic_title=subtopic_title, activity_type=activity_type,
        page_no=page_no, learning_outcome="Recognize numbers 1-5",
    )


def test_insert_then_find_by_id(test_db):
    _insert_topic(topic_id="t1")
    topic = syllabus_repository.find_by_id("t1")
    assert topic is not None
    assert topic["subtopic_title"] == "Counting 1-5"
    assert topic["activity_type"] == "Practice"


def test_find_by_id_returns_none_when_missing(test_db):
    assert syllabus_repository.find_by_id("no") is None


def test_list_by_filters_by_subject_and_grade(test_db):
    _insert_topic(topic_id="t1", subject="Mathematics", grade="Grade 1")
    _insert_topic(topic_id="t2", subject="Mathematics", grade="Grade 2",
                  subtopic_title="Counting 1-10", page_no=20)
    _insert_topic(topic_id="t3", subject="English", grade="Grade 1",
                  subtopic_title="Letters", page_no=5)

    math_g1 = syllabus_repository.list_by_filters(subject="Mathematics", grade="Grade 1")
    assert len(math_g1) == 1
    assert math_g1[0]["id"] == "t1"


def test_list_by_filters_no_filter_returns_all(test_db):
    _insert_topic(topic_id="t1", page_no=1)
    _insert_topic(topic_id="t2", page_no=2, subtopic_title="Other")
    assert len(syllabus_repository.list_by_filters()) == 2


def test_list_distinct_subject_grade(test_db):
    _insert_topic(topic_id="t1", subject="Mathematics", grade="Grade 1")
    _insert_topic(topic_id="t2", subject="Mathematics", grade="Grade 1",
                  subtopic_title="Different topic", page_no=99)
    _insert_topic(topic_id="t3", subject="English", grade="Grade 1",
                  subtopic_title="Letters", page_no=5)

    pairs = syllabus_repository.list_distinct_subject_grade()
    # Distinct: (Math, G1), (English, G1) — Math/G1 should collapse despite
    # two rows.
    assert len(pairs) == 2
    assert {"subject": "Mathematics", "grade": "Grade 1"} in pairs
    assert {"subject": "English", "grade": "Grade 1"} in pairs


def test_insert_duplicate_raises(test_db):
    """UNIQUE constraint on (subject, grade, unit_no, subtopic_title, page_no).
    Caller (CSV importer) catches this to skip dupes."""
    _insert_topic(topic_id="t1")
    with pytest.raises(Exception):
        # Same key tuple, different topic_id — should violate the constraint.
        _insert_topic(topic_id="t2")
