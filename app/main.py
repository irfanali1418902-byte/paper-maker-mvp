"""
AII Smart Paper Maker — Phase 1 MVP, layered.
Run karne ke liye: uvicorn app.main:app --reload --port 8000
Phir browser mein: http://localhost:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import dashboard, export, papers, questions, school_settings, stats, syllabus
from app.core.database import init_db

app = FastAPI(title="AII Smart Paper Maker - Phase 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(questions.router)
app.include_router(papers.router)
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(syllabus.router)
app.include_router(school_settings.router)
app.include_router(stats.router)

# Static frontend ka absolute path lete hain taake uvicorn kahin se bhi
# launch ho, file resolve ho jaye.
_STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
