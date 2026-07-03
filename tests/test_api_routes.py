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


def _insert_question(
    subject="Mathematics", topic="Fractions", bloom="UNDERSTAND", marks=3, qtype="multiple-choice"
):
    qid = str(uuid.uuid4())
    questions_repository.insert(
        {
            "id": qid,
            "subject": subject,
            "topic": topic,
            "bloom_level": bloom,
            "difficulty": "medium",
            "question_type": qtype,
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


# ---- paper_type filter (MCQ / mixed / subjective) --------------------------


def _seed_subjective(subject="Mathematics"):
    """Two short-answer questions per Bloom level."""
    return [
        _insert_question(subject, "Fractions", lvl, qtype="short-answer")
        for lvl in BLOOM_LEVELS
        for _ in range(2)
    ]


def test_paper_type_mcq_only_picks_mcq(client):
    _seed_bank()  # all multiple-choice
    _seed_subjective()  # add short-answer to the same subject
    r = client.post(
        "/api/generate-paper",
        json={"subject": "Mathematics", "total_questions": 6, "paper_type": "mcq"},
    )
    assert r.status_code == 200
    assert all(q["question_type"] == "multiple-choice" for q in r.json()["questions"])


def test_paper_type_subjective_picks_subjective(client):
    _seed_bank()
    _seed_subjective()
    r = client.post(
        "/api/generate-paper",
        json={"subject": "Mathematics", "total_questions": 6, "paper_type": "subjective"},
    )
    assert r.status_code == 200
    assert all(q["question_type"] == "short-answer" for q in r.json()["questions"])


def test_paper_type_subjective_empty_bank_404(client):
    _seed_bank()  # MCQ-only bank, no subjective questions
    r = client.post(
        "/api/generate-paper",
        json={"subject": "Mathematics", "total_questions": 6, "paper_type": "subjective"},
    )
    assert r.status_code == 404
    assert "subjective" in r.json()["detail"]


def test_paper_type_defaults_to_mixed(client):
    # No paper_type in body -> mixed -> any type, MCQ-only bank still works.
    _seed_bank()
    r = client.post("/api/generate-paper", json={"subject": "Mathematics", "total_questions": 6})
    assert r.status_code == 200


# ---- paper_type == custom-ratio (MCQ vs Subjective %) ----------------------

_MCQ_TYPES = {"multiple-choice", "true-false"}
_SUBJ_TYPES = {"short-answer", "essay"}


def test_custom_ratio_splits_by_percent(client):
    _seed_bank()  # 12 multiple-choice
    _seed_subjective()  # 12 short-answer
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": 6,
            "paper_type": "custom-ratio",
            "mcq_percent": 50,
        },
    )
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 6
    assert sum(1 for q in qs if q["question_type"] in _MCQ_TYPES) == 3
    assert sum(1 for q in qs if q["question_type"] in _SUBJ_TYPES) == 3


def test_custom_ratio_30_70(client):
    _seed_bank()
    _seed_subjective()
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": 10,
            "paper_type": "custom-ratio",
            "mcq_percent": 30,
        },
    )
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert sum(1 for q in qs if q["question_type"] in _MCQ_TYPES) == 3
    assert sum(1 for q in qs if q["question_type"] in _SUBJ_TYPES) == 7


def test_custom_ratio_100_all_mcq(client):
    _seed_bank()  # MCQ only; subjective group not needed at 100%
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": 5,
            "paper_type": "custom-ratio",
            "mcq_percent": 100,
        },
    )
    assert r.status_code == 200
    assert all(q["question_type"] in _MCQ_TYPES for q in r.json()["questions"])


def test_custom_ratio_guard_missing_subjective_404(client):
    _seed_bank()  # MCQ-only bank; 50% needs subjective -> group empty
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": 6,
            "paper_type": "custom-ratio",
            "mcq_percent": 50,
        },
    )
    assert r.status_code == 404
    assert "Subjective" in r.json()["detail"]


def test_custom_ratio_missing_percent_400(client):
    _seed_bank()
    r = client.post(
        "/api/generate-paper",
        json={"subject": "Mathematics", "total_questions": 6, "paper_type": "custom-ratio"},
    )
    assert r.status_code == 400


def test_custom_ratio_percent_out_of_range_422(client):
    r = client.post(
        "/api/generate-paper",
        json={
            "subject": "Mathematics",
            "total_questions": 6,
            "paper_type": "custom-ratio",
            "mcq_percent": 150,
        },
    )
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


def test_generate_subjective_then_build_subjective_paper(client, monkeypatch):
    # Full loop: AI se short-answer questions generate -> subjective paper assemble.
    from app.services import ai_service

    def fake_ai(**kw):
        return [
            {
                "bloom_level": lvl,
                "question_type": "short-answer",
                "question_en": "Explain...",
                "question_ur": "وضاحت کریں",
                "options_en": [],
                "options_ur": [],
                "correct_answer_en": "model answer",
                "correct_answer_ur": "نمونہ جواب",
                "explanation_en": "",
                "explanation_ur": "",
                "visual_emoji": None,
                "visual_count": None,
            }
            for lvl in BLOOM_LEVELS
        ]

    monkeypatch.setattr(ai_service, "generate_questions_from_ai", fake_ai)

    gen = client.post(
        "/api/generate-questions",
        json={
            "subject": "Mathematics",
            "topic": "Fractions",
            "total_questions": 6,
            "question_types": ["short-answer"],
        },
    )
    assert gen.status_code == 200 and gen.json()["saved_count"] == 6

    paper = client.post(
        "/api/generate-paper",
        json={"subject": "Mathematics", "total_questions": 6, "paper_type": "subjective"},
    )
    assert paper.status_code == 200
    assert all(q["question_type"] == "short-answer" for q in paper.json()["questions"])


# ---- /api/generate-adaptive-paper — paper_type filter (R3) ------------------
# Adaptive assembly ka type-filter test karte hain. Poora results-upload pipeline
# drag karne ki bajaye dashboard ko stub karte hain — R3 sirf "type filter apply
# hota hai ya nahi" ke baare mein hai, weakness kaise compute hui uska nahi.

_ADAPTIVE_BREAKDOWN = [
    {"bloom_level": lvl, "average_percent": pct}
    for lvl, pct in zip(BLOOM_LEVELS, [30.0, 45.0, 55.0, 60.0, 70.0, 80.0], strict=True)
]


def _seed_typed(qtype, n=2):
    for lvl in BLOOM_LEVELS:
        for _ in range(n):
            _insert_question(bloom=lvl, qtype=qtype)


def _make_source_paper():
    from app.repositories import papers_repository

    papers_repository.insert(
        paper_id="src-paper",
        subject="Mathematics",
        class_name="Grade 5",
        total_marks=0,
        question_ids=[],
    )
    return "src-paper"


def _stub_dashboard(monkeypatch):
    from app.services import dashboard_service

    monkeypatch.setattr(
        dashboard_service,
        "get_latest_dashboard_for_paper",
        lambda paper_id: {"bloom_breakdown": _ADAPTIVE_BREAKDOWN},
    )


def test_adaptive_paper_type_mcq_only(client, monkeypatch):
    # Bank mein MCQ + subjective dono; mcq filter ke baad sirf MCQ aane chahiye.
    _seed_typed("multiple-choice")
    _seed_typed("short-answer")
    source_id = _make_source_paper()
    _stub_dashboard(monkeypatch)

    r = client.post(
        "/api/generate-adaptive-paper",
        json={"source_paper_id": source_id, "paper_type": "mcq", "total_questions": 6},
    )
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert questions
    assert all(q["question_type"] == "multiple-choice" for q in questions)


def test_adaptive_paper_type_subjective_only(client, monkeypatch):
    _seed_typed("multiple-choice")
    _seed_typed("short-answer")
    source_id = _make_source_paper()
    _stub_dashboard(monkeypatch)

    r = client.post(
        "/api/generate-adaptive-paper",
        json={"source_paper_id": source_id, "paper_type": "subjective", "total_questions": 6},
    )
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert questions
    assert all(q["question_type"] in ("short-answer", "essay") for q in questions)


def test_adaptive_default_mixed_allows_all_types(client, monkeypatch):
    # Back-compat: paper_type diye bina purana behavior — koi type filter nahi.
    # Bank sirf subjective; default "mixed" ko wahi laut aane chahiye (agar galti se
    # MCQ-only default hota to bank khali lagta aur 404 milta).
    _seed_typed("short-answer")
    source_id = _make_source_paper()
    _stub_dashboard(monkeypatch)

    r = client.post(
        "/api/generate-adaptive-paper",
        json={"source_paper_id": source_id, "total_questions": 6},
    )
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert questions
    assert all(q["question_type"] == "short-answer" for q in questions)


def test_adaptive_rejects_custom_ratio_422(client):
    r = client.post(
        "/api/generate-adaptive-paper",
        json={"source_paper_id": "whatever", "paper_type": "custom-ratio"},
    )
    assert r.status_code == 422


# ---- API-key auth -----------------------------------------------------------
# Default test env mein PAPER_MAKER_API_KEY unset hai -> auth OFF, is liye upar
# ke saare tests bina header ke pass hote hain. Yahan key set karke enforce-mode
# ka behaviour lock karte hain.


def test_auth_disabled_when_key_unset(client, monkeypatch):
    from app.api import auth

    monkeypatch.setattr(auth, "API_KEY", "")
    assert client.get("/api/stats").status_code == 200


def test_auth_rejects_missing_key(client, monkeypatch):
    from app.api import auth

    monkeypatch.setattr(auth, "API_KEY", "secret-key")
    assert client.get("/api/stats").status_code == 401


def test_auth_rejects_wrong_key(client, monkeypatch):
    from app.api import auth

    monkeypatch.setattr(auth, "API_KEY", "secret-key")
    r = client.get("/api/stats", headers={"x-api-key": "wrong"})
    assert r.status_code == 401


def test_auth_accepts_correct_key(client, monkeypatch):
    from app.api import auth

    monkeypatch.setattr(auth, "API_KEY", "secret-key")
    r = client.get("/api/stats", headers={"x-api-key": "secret-key"})
    assert r.status_code == 200


def test_static_frontend_open_without_key(client, monkeypatch):
    # Frontend HTML bina key ke load hona chahiye, warna UI hi na khule.
    from app.api import auth

    monkeypatch.setattr(auth, "API_KEY", "secret-key")
    assert client.get("/index.html").status_code == 200


# ---- Fail-closed config guard (deploy without a key) ------------------------
# auth_config_error() pure hai — startup par decide karta hai ke deployment par
# key missing hone par app crash kare (silently unprotected chalne ki bajaye).


def test_auth_config_local_dev_no_key_is_ok():
    # Koi deploy signal nahi + key missing = local dev, koi error nahi.
    from app.api import auth

    assert auth.auth_config_error("", {}) is None


def test_auth_config_key_present_always_ok():
    # Key set ho to deployment par bhi sab theek.
    from app.api import auth

    assert auth.auth_config_error("real-key", {"RAILWAY_ENVIRONMENT": "production"}) is None


def test_auth_config_deploy_marker_without_key_fails():
    # Railway marker + key missing = fail-closed (non-None error message).
    from app.api import auth

    assert auth.auth_config_error("", {"RAILWAY_ENVIRONMENT": "production"}) is not None
    assert auth.auth_config_error("", {"RAILWAY_SERVICE_ID": "svc-123"}) is not None


def test_auth_config_explicit_require_flag_without_key_fails():
    # Kisi bhi host par PAPER_MAKER_REQUIRE_API_KEY=1 => key mandatory.
    from app.api import auth

    assert auth.auth_config_error("", {"PAPER_MAKER_REQUIRE_API_KEY": "1"}) is not None
    assert auth.auth_config_error("", {"PAPER_MAKER_REQUIRE_API_KEY": "true"}) is not None


def test_auth_config_require_flag_falsey_is_ok():
    # Flag "0"/"false"/empty ko deploy signal nahi maana jata.
    from app.api import auth

    assert auth.auth_config_error("", {"PAPER_MAKER_REQUIRE_API_KEY": "0"}) is None
    assert auth.auth_config_error("", {"PAPER_MAKER_REQUIRE_API_KEY": "false"}) is None
