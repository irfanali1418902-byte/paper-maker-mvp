"""HTTP-layer (route) tests via FastAPI TestClient.

These exercise the error-handling contract — 200 / 400 / 404 / 422 — that the
service and repository unit tests don't reach. The AI provider is mocked so the
suite stays hermetic and offline; everything else runs against the isolated
temp DB from the `test_db` fixture (DB_PATH is monkeypatched there, and
repositories read it at call time, so every request hits the temp file).
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.repositories import questions_repository

BLOOM_LEVELS = ["REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"]


@pytest.fixture
def client(test_db):
    # Depends on test_db so DB_PATH is already pointed at the temp file before
    # app.main is imported (its module-level init_db then targets the temp DB).
    from app.main import app

    return TestClient(app)


def _insert_question(subject="Mathematics", topic="Fractions", bloom="UNDERSTAND", marks=3):
    qid = str(uuid.uuid4())
    questions_repository.insert(
        {
            "id": qid,
            "subject": subject,
            "topic": topic,
            "bloom_level": bloom,
            "difficulty": "medium",
            "question_type": "multiple-choice",
            "marks": marks,
            "question_en": f"Q-{qid[:4]}",
            "question_ur": "سوال",
            "options_en": json.dumps(["a", "b", "c", "d"]),
            "options_ur": json.dumps(["ا", "ب", "ج", "د"]),
            "correct_answer_en": "a",
            "correct_answer_ur": "ا",
            "explanation_en": "",
            "explanation_ur": "",
            "visual_emoji": None,
            "visual_count": None,
        }
    )
    return qid


def _seed_bank(subject="Mathematics", topic="Fractions"):
    """Two questions per Bloom level so any distribution can be satisfied."""
    return [_insert_question(subject, topic, lvl) for lvl in BLOOM_LEVELS for _ in range(2)]


def _make_paper(client, total=4):
    _seed_bank()
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": total,
            "bloom_distribution": "balanced",
            "difficulty": "medium",
        },
    )
    assert r.status_code == 200
    return r.json()


# ---- /api/stats -------------------------------------------------------------


def test_stats_empty_db(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert r.json() == {
        "total_papers": 0,
        "uploads_this_month": 0,
        "top_subject": None,
        "total_questions": 0,
    }


def test_stats_counts_questions(client):
    _seed_bank()
    assert client.get("/api/stats").json()["total_questions"] == 12


# ---- /api/questions ---------------------------------------------------------


def test_list_questions_empty(client):
    r = client.get("/api/questions")
    assert r.status_code == 200
    assert r.json() == []


def test_list_questions_bloom_filter(client):
    _seed_bank()
    r = client.get("/api/questions", params={"subject": "Mathematics", "bloom_level": "APPLY"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all(q["bloom_level"] == "APPLY" for q in data)


# ---- /api/generate-paper ----------------------------------------------------


def test_generate_paper_empty_bank_404(client):
    r = client.post("/api/generate-paper", json={"subject": "Mathematics", "total_questions": 5})
    assert r.status_code == 404


def test_generate_paper_happy(client):
    body = _make_paper(client, total=6)
    assert body["paper_id"]
    assert body["questions"]
    assert body["total_marks"] == sum(q["marks"] for q in body["questions"])
    assert body["balance_summary"]["total_questions"] == len(body["questions"])


def test_generate_paper_missing_subject_422(client):
    # subject is required on GeneratePaperRequest -> Pydantic 422, not 500.
    r = client.post("/api/generate-paper", json={"total_questions": 5})
    assert r.status_code == 422


# ---- /api/paper/{id} --------------------------------------------------------


def test_get_paper_404(client):
    assert client.get("/api/paper/does-not-exist").status_code == 404


def test_get_paper_happy(client):
    paper = _make_paper(client)
    r = client.get(f"/api/paper/{paper['paper_id']}")
    assert r.status_code == 200
    assert r.json()["paper"]["id"] == paper["paper_id"]


# ---- /api/paper/{id}/replace-question --------------------------------------


def test_replace_question_empty_body_422(client):
    # The exact request that returned 405 on a stale server (route missing ->
    # static-mount fall-through). On a current server it's a real route -> 422.
    paper = _make_paper(client)
    r = client.post(f"/api/paper/{paper['paper_id']}/replace-question", json={})
    assert r.status_code == 422


def test_replace_question_bad_paper_404(client):
    r = client.post(
        "/api/paper/nope/replace-question",
        json={"old_question_id": "a", "new_question_id": "b"},
    )
    assert r.status_code == 404


def test_replace_question_bad_ids_400(client):
    paper = _make_paper(client)
    r = client.post(
        f"/api/paper/{paper['paper_id']}/replace-question",
        json={"old_question_id": "not-in-paper", "new_question_id": "whatever"},
    )
    assert r.status_code == 400


def test_replace_question_happy(client):
    paper = _make_paper(client)
    old_id = paper["questions"][0]["id"]
    in_paper = {q["id"] for q in paper["questions"]}
    bank = client.get("/api/questions", params={"subject": "Mathematics"}).json()
    new_id = next(q["id"] for q in bank if q["id"] not in in_paper)

    r = client.post(
        f"/api/paper/{paper['paper_id']}/replace-question",
        json={"old_question_id": old_id, "new_question_id": new_id},
    )
    assert r.status_code == 200
    ids = {q["id"] for q in r.json()["questions"]}
    assert new_id in ids and old_id not in ids


# ---- /api/paper/{id}/dashboard ---------------------------------------------


def test_dashboard_no_results_404(client):
    paper = _make_paper(client)
    r = client.get(f"/api/paper/{paper['paper_id']}/dashboard")
    assert r.status_code == 404


# ---- /api/school-settings ---------------------------------------------------


def test_school_settings_roundtrip(client):
    r = client.post(
        "/api/school-settings",
        json={"school_name": "GHS Mingora", "school_name_ur": "گورنمنٹ", "address": "Swat"},
    )
    assert r.status_code == 200
    g = client.get("/api/school-settings")
    assert g.status_code == 200
    assert g.json()["school_name"] == "GHS Mingora"


# ---- /api/generate-questions (AI mocked) ------------------------------------


def test_generate_questions_ai_mocked(client, monkeypatch):
    from app.services import ai_service

    fake = [
        {
            "bloom_level": "UNDERSTAND",
            "question_type": "multiple-choice",
            "question_en": "2+2?",
            "question_ur": "؟",
            "options_en": ["3", "4"],
            "options_ur": ["۳", "۴"],
            "correct_answer_en": "4",
            "correct_answer_ur": "۴",
            "explanation_en": "",
            "explanation_ur": "",
            "visual_emoji": None,
            "visual_count": None,
        }
    ]
    monkeypatch.setattr(ai_service, "generate_questions_from_ai", lambda **kw: fake)

    r = client.post(
        "/api/generate-questions",
        json={"subject": "Mathematics", "topic": "Addition", "total_questions": 1},
    )
    assert r.status_code == 200
    assert r.json()["saved_count"] == 1
    assert client.get("/api/stats").json()["total_questions"] == 1


def test_generate_questions_missing_subject_400(client):
    r = client.post("/api/generate-questions", json={"subject": "", "topic": ""})
    assert r.status_code == 400
