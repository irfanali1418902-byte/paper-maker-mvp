# PROJECT: AII Smart Paper Maker
# Developer: Irfan | University of Swat | UOS241012011
# Supervisor: Dr. Sajjad Hussain

## PROJECT OVERVIEW
Yeh ek AI-powered exam paper generator hai jo:
1. Claude AI se Bloom-tagged bilingual (Urdu+English) questions generate karta hai
2. SQLite database mein questions save karta hai
3. Balanced exam paper assemble karta hai (expected difficulty + balance summary ke saath)
4. Student results analyze karta hai (dashboard + P-value/D-index item analysis)
5. Class ki kamzoriyon se adaptive paper banata hai (Phase 3)
6. Word (.docx) aur PDF export karta hai

## TECH STACK
- Backend: Python + FastAPI
- Database: SQLite (paper_maker.db)
- AI: Anthropic Claude API
- Export: python-docx + LibreOffice headless
- Font: Jameel Noori Nastaleeq (Urdu)
- Tests: pytest (128/128 passing)

## PROJECT STRUCTURE
```
paper-maker-mvp/
├── app/
│   ├── main.py          # FastAPI app: routers mount + static + init_db
│   ├── api/             # HTTP routes (questions, papers, dashboard, export, syllabus, school_settings)
│   ├── services/        # Business logic (bloom, ai, paper, question, result,
│   │                    #   dashboard, item_analysis, adaptive, export, syllabus, settings)
│   ├── repositories/    # SQLite access — sirf yahan SQL strings hain
│   ├── core/database.py # Connection factory + schema bootstrap + migrations
│   └── schemas/         # Pydantic request + response shapes
├── static/              # index.html (paper maker + adaptive) + dashboard.html
├── tests/               # pytest suite
├── import_syllabus.py   # CLI: syllabus CSV import
├── seed_large_class.py  # CLI: engineered results seed (D-index flags test)
├── requirements.txt     # Python dependencies
├── ARCHITECTURE.md      # layering contract
├── CLAUDE.md            # coding conventions (Claude Code auto-loads)
└── paper_maker.db       # SQLite database (gitignored)
```

## COMPLETED PHASES
### ✅ Phase 1 — Core Engine
- AI question generation (bilingual Urdu+English)
- Bloom's Taxonomy tagging
- SQLite question bank
- Balanced paper assembly
- Simple frontend UI

### ✅ Phase 2 — Dashboard + Export
- Result analyzer dashboard service
- 3 API endpoints: uploads list, latest dashboard, specific dashboard
- Student ranking (competition-style: 1,1,3)
- Pass threshold: 33% (KPK board standard)
- Dashboard frontend UI (`static/dashboard.html`)
- Word (.docx) export with Jameel Noori Nastaleeq
- PDF export via LibreOffice headless

### ✅ Phase 2.5 — Item Analysis (psychometrics)
- Expected difficulty (Bloom → Easy/Medium/Hard) + paper balance summary at build time
- Difficulty Index (P-value) + Discrimination Index (D) per question
- Bad-question flags: too easy/hard, negative D (mis-keyed) — surfaced in dashboard
- `d_reliable` false for classes <10 students (split not meaningful)
- Logic in `app/services/item_analysis_service.py` (pure, no DB changes)

### ✅ Phase 3 — Adaptive Paper Generation
- Class ki weak Bloom levels se weighted distribution (blended-with-floor)
- `POST /api/generate-adaptive-paper` — source paper ke latest results se seekhta hai
- Response mein `adaptive_summary` (per-level weakness → questions allocated)
- Logic in `app/services/adaptive_service.py` (pure, no DB changes)
- `seed_large_class.py` — reproducible test data (≥10 students) for D-index flags
- 128/128 pytest passing

## NEXT TASKS (Priority Order)
- [ ] LibreOffice install verify karo — PDF end-to-end test
- [ ] Syllabus PDF upload — topics auto-extract
- [ ] README mein LibreOffice install step add karo
- [ ] Per-student adaptive papers (abhi whole-class only)
- [ ] Topic-level weakness targeting (abhi Bloom-level only)
- [ ] Adaptive: weak level mein bank khali ho to AI se auto-generate

## API ENDPOINTS
```
# Questions
POST /api/generate-questions             # AI se bilingual Bloom-tagged questions
GET  /api/questions                      # Question bank list

# Papers
POST /api/generate-paper                 # Balanced paper assemble (+ balance summary)
POST /api/generate-adaptive-paper        # Phase 3: class ki weak Bloom levels se paper
GET  /api/paper/{paper_id}               # Paper + questions (expected difficulty ke saath)
GET  /api/paper/{paper_id}/result-template   # Empty results CSV template
POST /api/paper/{paper_id}/upload-results    # Filled results CSV upload + validate

# Dashboard (Phase 2 + 2.5 analytics: P-value, D-index, flags)
GET  /api/paper/{paper_id}/uploads       # Paper ki uploads list
GET  /api/paper/{paper_id}/dashboard     # Latest upload dashboard
GET  /api/upload/{upload_id}/dashboard   # Specific upload dashboard

# Export
GET  /api/paper/{paper_id}/export.docx   # Word export (Jameel Noori Nastaleeq)
GET  /api/paper/{paper_id}/export.pdf    # PDF export (LibreOffice headless)

# Syllabus + settings
GET  /api/syllabus-grades                # Distinct (subject, grade) pairs
GET  /api/syllabus-topics                # Topics for a subject/grade
GET  /api/school-settings                # Letterhead/logo settings
POST /api/school-settings                # Save settings
```

## STRICT RULES — ALWAYS FOLLOW

### Code Quality
- ALWAYS write comments in English
- EVERY function must have a docstring
- Use meaningful variable names (x, y — KABHI NAHI)
- Maximum function length: 50 lines

### Before ANY file edit
- Pehle existing code padho
- Samjho kya ho raha hai, phir edit karo
- Ek baar mein ek hi cheez badlo

### Testing
- Har naye feature ke liye test likhna ZAROORI hai
- Run: `python -m pytest tests/ -v` before finishing
- Koi bhi test fail ho to ruko — pehle fix karo

### Git Commits
- Clear commit message: "feat(phase3): add adaptive paper"
- `.env` file KABHI commit mat karo
- API keys code mein KABHI mat likho

### File Protection
- `.env` — kabhi mat chho
- `paper_maker.db` — seedha mat badlo, API se karo
- `data/raw/` — original data kabhi mat badlo

## BUILD COMMANDS
```bash
# Dependencies install
pip install -r requirements.txt

# Server chalao
uvicorn app.main:app --reload --port 8000

# Tests chalao
python -m pytest tests/ -v

# Browser mein kholo
http://localhost:8000
```

## IMPORTANT REMINDERS
- Pass threshold = 33% (KPK board) — Swat ka alag ho to batao
- Ranking = competition style (ties: 1, 1, 3)
- Urdu font = Jameel Noori Nastaleeq
- PDF ke liye LibreOffice install hona zaroori hai

## RELATED CONFIG
- Coding conventions: `CLAUDE.md`
- Layering contract: `ARCHITECTURE.md`
- Security + education guardrails: `.claude/rules/` (local Claude Code config, gitignored)
