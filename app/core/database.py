"""
SQLite database layer. Zero setup, zero cost — koi server install nahi karna,
ek file (paper_maker.db) hi poori database hai. Jab scale badhe to isi schema
ko Supabase/PostgreSQL par seedha migrate kiya ja sakta hai.
"""

import sqlite3
from pathlib import Path

# app/core/database.py se project root tak teen levels upar.
DB_PATH = Path(__file__).parent.parent.parent / "paper_maker.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            bloom_level TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question_type TEXT NOT NULL,
            marks INTEGER NOT NULL,
            question_en TEXT,
            question_ur TEXT,
            options_en TEXT,
            options_ur TEXT,
            correct_answer_en TEXT,
            correct_answer_ur TEXT,
            explanation_en TEXT,
            explanation_ur TEXT,
            visual_emoji TEXT,
            visual_count INTEGER,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # Older DB files (created before the visual_* columns were added) need
    # to be migrated in-place — CREATE TABLE IF NOT EXISTS won't add columns
    # to an existing table.
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(questions)").fetchall()}
    if "visual_emoji" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN visual_emoji TEXT")
    if "visual_count" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN visual_count INTEGER")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            class_name TEXT,
            total_marks INTEGER NOT NULL,
            question_ids TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS syllabus_topics (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            grade TEXT,
            unit_no INTEGER NOT NULL,
            unit_title TEXT NOT NULL,
            page_range TEXT,
            subtopic_title TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            page_no INTEGER,
            learning_outcome TEXT,
            UNIQUE(subject, grade, unit_no, subtopic_title, page_no)
        )
        """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS school_settings (
            id INTEGER PRIMARY KEY,
            school_name TEXT,
            school_name_ur TEXT,
            address TEXT,
            address_ur TEXT,
            logo_base64 TEXT,
            accent_color TEXT
        )
        """)

    # Per-call AI provider usage log. Har successful Gemini/Claude API call
    # ek row likhti hai — yehi future per-school billing ka base banega.
    # IF NOT EXISTS itself is idempotent: fresh installs banayenge, existing
    # DBs untouched chhod denge.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER
        )
        """)

    conn.commit()
    conn.close()
