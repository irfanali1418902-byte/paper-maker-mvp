"""
AII Smart Paper Maker — Phase 1 MVP, layered.
Run karne ke liye: uvicorn app.main:app --reload --port 8000
Phir browser mein: http://localhost:8000
"""

import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import dashboard, export, papers, questions, school_settings, stats, syllabus
from app.api.auth import require_api_key
from app.core.database import init_db

app = FastAPI(title="AII Smart Paper Maker - Phase 1")

# Cross-origin origins env se (comma-separated). Frontend same-origin (`/`) se
# serve hota hai, is liye default `*` kisi ko todta nahi — par production mein
# PAPER_MAKER_ALLOWED_ORIGINS set karke isse apni school domain tak lock karo.
_origins_env = os.environ.get("PAPER_MAKER_ALLOWED_ORIGINS", "").strip()
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Har /api router API-key auth ke peeche. Static `/` mount (neeche) khula rehta
# hai taake frontend HTML/JS bina key ke load ho sake.
_api_auth = [Depends(require_api_key)]
app.include_router(questions.router, dependencies=_api_auth)
app.include_router(papers.router, dependencies=_api_auth)
app.include_router(dashboard.router, dependencies=_api_auth)
app.include_router(export.router, dependencies=_api_auth)
app.include_router(syllabus.router, dependencies=_api_auth)
app.include_router(school_settings.router, dependencies=_api_auth)
app.include_router(stats.router, dependencies=_api_auth)

# Static frontend ka absolute path lete hain taake uvicorn kahin se bhi
# launch ho, file resolve ho jaye.
_STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
