"""
AII Smart Paper Maker — Phase 1 MVP
Run karne ke liye: uvicorn main:app --reload --port 8000
Phir browser mein: http://localhost:8000
"""
import uuid
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import init_db, get_connection
from bloom_engine import calculate_bloom_distribution, calculate_marks
from ai_generator import generate_questions_from_ai

app = FastAPI(title="AII Smart Paper Maker - Phase 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class GenerateRequest(BaseModel):
    subject: str = ""
    topic: str = ""
    syllabus_topic_id: Optional[str] = None
    total_questions: int = 10
    bloom_distribution: str = "balanced"  # balanced | foundational | advanced
    question_types: List[str] = ["multiple-choice"]
    difficulty: str = "medium"


class PaperRequest(BaseModel):
    subject: str
    class_name: Optional[str] = None
    total_questions: int = 10
    bloom_distribution: str = "balanced"
    difficulty: Optional[str] = None


class SchoolSettings(BaseModel):
    school_name: str = ""
    school_name_ur: str = ""
    address: str = ""
    address_ur: str = ""
    logo_base64: Optional[str] = None
    accent_color: str = "#0e4d3c"


@app.get("/api/school-settings")
def get_school_settings():
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM school_settings WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return SchoolSettings().model_dump()
    return dict(row)


@app.post("/api/school-settings")
def save_school_settings(settings: SchoolSettings):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO school_settings (id, school_name, school_name_ur, address, address_ur, logo_base64, accent_color)
           VALUES (1, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             school_name=excluded.school_name, school_name_ur=excluded.school_name_ur,
             address=excluded.address, address_ur=excluded.address_ur,
             logo_base64=excluded.logo_base64, accent_color=excluded.accent_color""",
        (
            settings.school_name, settings.school_name_ur, settings.address,
            settings.address_ur, settings.logo_base64, settings.accent_color,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}


@app.get("/api/syllabus-grades")
def list_syllabus_grades():
    """Database mein jo bhi subject+grade combinations imported hain, unki list deta hai (dropdown ke liye)."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT subject, grade FROM syllabus_topics ORDER BY subject, grade"
    ).fetchall()
    conn.close()
    return [{"subject": row["subject"], "grade": row["grade"]} for row in rows]


@app.get("/api/syllabus-topics")
def list_syllabus_topics(subject: Optional[str] = None, grade: Optional[str] = None):
    """Real textbook se import kiye gaye topics list karta hai, dropdown ke
    liye. Har topic ke saath suggested difficulty bhi deta hai (book ke apne
    Introduction/Identification/Practice/Review tagging se mapped)."""
    activity_to_difficulty = {
        "Introduction": "easy",
        "Identification": "easy",
        "Practice": "medium",
        "Review": "hard",
    }

    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM syllabus_topics WHERE 1=1"
    params = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if grade:
        query += " AND grade = ?"
        params.append(grade)
    query += " ORDER BY unit_no, page_no"
    rows = cur.execute(query, params).fetchall()
    conn.close()

    topics = []
    for row in rows:
        topic = dict(row)
        topic["suggested_difficulty"] = activity_to_difficulty.get(topic["activity_type"], "medium")
        topics.append(topic)
    return topics


@app.post("/api/generate-questions")
def generate_questions(req: GenerateRequest):
    """Topic dekar AI se Bloom-tagged bilingual questions generate karta hai
    aur question bank (SQLite) mein save karta hai.

    Agar syllabus_topic_id diya jaye, to subject/topic/difficulty usi
    syllabus_topics row se khud-bakhud le liye jaate hain (manual typing
    ki zaroorat nahi)."""
    if req.syllabus_topic_id:
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT * FROM syllabus_topics WHERE id = ?", (req.syllabus_topic_id,)
        ).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="syllabus_topic_id nahi mila.")
        req.subject = row["subject"]
        req.topic = row["subtopic_title"]
        activity_to_difficulty = {
            "Introduction": "easy", "Identification": "easy",
            "Practice": "medium", "Review": "hard",
        }
        req.difficulty = activity_to_difficulty.get(row["activity_type"], req.difficulty)

    if not req.subject or not req.topic:
        raise HTTPException(status_code=400, detail="subject aur topic dono zaroori hain (ya syllabus_topic_id den).")

    distribution = calculate_bloom_distribution(req.bloom_distribution, req.total_questions)
    try:
        ai_questions = generate_questions_from_ai(
            topic=req.topic,
            subject=req.subject,
            bloom_distribution=distribution,
            question_types=req.question_types,
            difficulty=req.difficulty,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI generation fail hui: {e}")

    conn = get_connection()
    cur = conn.cursor()
    saved_ids = []
    try:
        for q in ai_questions:
            qid = str(uuid.uuid4())
            marks = calculate_marks(
                q.get("bloom_level", "UNDERSTAND"), q.get("question_type", "multiple-choice"), req.difficulty
            )
            cur.execute(
                """INSERT INTO questions
                   (id, subject, topic, bloom_level, difficulty, question_type, marks,
                    question_en, question_ur, options_en, options_ur,
                    correct_answer_en, correct_answer_ur, explanation_en, explanation_ur,
                    visual_emoji, visual_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    qid, req.subject, req.topic, q.get("bloom_level"), req.difficulty,
                    q.get("question_type"), marks,
                    q.get("question_en"), q.get("question_ur"),
                    json.dumps(q.get("options_en", [])), json.dumps(q.get("options_ur", [])),
                    q.get("correct_answer_en"), q.get("correct_answer_ur"),
                    q.get("explanation_en"), q.get("explanation_ur"),
                    q.get("visual_emoji"), q.get("visual_count"),
                ),
            )
            saved_ids.append(qid)
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Question save fail hui (DB error): {e}")
    conn.close()

    return {"saved_count": len(saved_ids), "question_ids": saved_ids}


@app.get("/api/questions")
def list_questions(subject: Optional[str] = None, topic: Optional[str] = None):
    """Question bank browse karne ke liye."""
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM questions WHERE 1=1"
    params = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if topic:
        query += " AND topic = ?"
        params.append(topic)
    rows = cur.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/generate-paper")
def generate_paper(req: PaperRequest):
    """Question bank se Bloom + difficulty distribution ke hisaab se balanced
    paper assemble karta hai. Least-used questions ko priority deta hai
    (taake repetition kam ho)."""
    distribution = calculate_bloom_distribution(req.bloom_distribution, req.total_questions)

    conn = get_connection()
    cur = conn.cursor()
    selected_ids = []
    selected_questions = []

    for level, count in distribution.items():
        if count <= 0:
            continue
        query = "SELECT * FROM questions WHERE subject = ? AND bloom_level = ?"
        params = [req.subject, level]
        if req.difficulty:
            query += " AND difficulty = ?"
            params.append(req.difficulty)
        query += " ORDER BY usage_count ASC LIMIT ?"
        params.append(count)
        rows = cur.execute(query, params).fetchall()
        for row in rows:
            selected_ids.append(row["id"])
            selected_questions.append(dict(row))
            cur.execute("UPDATE questions SET usage_count = usage_count + 1 WHERE id = ?", (row["id"],))

    if not selected_questions:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Is subject/Bloom-level ke liye question bank khali hai. Pehle /api/generate-questions se questions banayen.",
        )

    paper_id = str(uuid.uuid4())
    total_marks = sum(q["marks"] for q in selected_questions)
    cur.execute(
        "INSERT INTO papers (id, subject, class_name, total_marks, question_ids) VALUES (?,?,?,?,?)",
        (paper_id, req.subject, req.class_name, total_marks, json.dumps(selected_ids)),
    )
    conn.commit()
    conn.close()

    return {"paper_id": paper_id, "total_marks": total_marks, "questions": selected_questions}


@app.get("/api/paper/{paper_id}")
def get_paper(paper_id: str):
    conn = get_connection()
    cur = conn.cursor()
    paper = cur.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        conn.close()
        raise HTTPException(status_code=404, detail="Paper nahi mila.")
    question_ids = json.loads(paper["question_ids"])
    questions = []
    for qid in question_ids:
        row = cur.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
        if row:
            questions.append(dict(row))
    conn.close()
    return {"paper": dict(paper), "questions": questions}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
