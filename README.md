# AII Smart Paper Maker — Phase 1 MVP

Ye Phase 1 ka core engine hai: AI se Bloom-tagged bilingual (Urdu+English)
question generate karna, SQLite question bank mein save karna, aur usse
balanced exam paper assemble karna.

## Files

Code layered structure mein hai (routes -> services -> repositories -> core).
Full rules `ARCHITECTURE.md` aur `CLAUDE.md` mein hain.

- `app/main.py` — FastAPI app entry point (routers mount + static + `init_db`)
- `app/api/` — HTTP route handlers (`questions`, `papers`, `syllabus`, `school_settings`)
- `app/services/` — Business logic: Bloom distribution + marks (`bloom_service`),
  AI provider (`ai_service`), orchestration (`question_service`, `paper_service`,
  `syllabus_service`, `settings_service`)
- `app/repositories/` — SQLite access — sirf yahan SQL strings hain
- `app/core/database.py` — Connection factory + schema bootstrap + migrations
- `app/models/requests.py` — Pydantic request shapes
- `import_syllabus.py` — CSV se syllabus topics import karne wala CLI
- `static/index.html` — Testing ke liye simple bilingual frontend

## Setup (apne computer/VPS par)

1. Python 3.10+ installed hona chahiye.

2. Dependencies install karen:
   ```
   pip install -r requirements.txt
   ```

3. Project root mein `.env` file banayen aur ek API key add karen:

   **FREE option (Gemini)** — testing ke liye recommended, koi card nahi chahiye:
   - [aistudio.google.com](https://aistudio.google.com) par Google account se login karen
   - "Get API key" par click kar ke key generate karen
   - `.env` mein ye line dalen:
     ```
     GEMINI_API_KEY=apni-key-yahan
     ```

   **PAID option (Claude)** — jab production/AII deployment ke liye behtar
   quality chahiye ho:
   - console.anthropic.com se key len, `.env` mein dalen:
     ```
     ANTHROPIC_API_KEY=sk-ant-...
     ```
   - Agar ye key bhi set hai to code automatically isi ko use karega
     (Gemini ko ignore kar dega)

   App startup par `python-dotenv` `.env` ko auto-load kar leta hai —
   manually environment variables set karne ki zaroorat nahi.

4. Server chalayen:
   ```
   uvicorn app.main:app --reload --port 8000
   ```

5. Browser mein kholen: http://localhost:8000

## Kaise use karen

1. Subject + Topic likhen (e.g. Mathematics / Fractions)
2. "Generate questions (AI)" dabayen — ye Claude API se bilingual,
   Bloom-tagged questions banayega aur SQLite mein save karega
3. "Build paper from bank" dabayen — ye database se balanced distribution
   ke hisaab se paper assemble karega

## Agla kaam (jo abhi nahi hai)

- Word/PDF export (aapka existing python-docx + Urdu font pipeline yahan
  plug karna hai)
- Syllabus PDF upload se topics auto-extract karna
- Performance analyzer (Phase 2)
- Adaptive paper generation (Phase 3)

## Note

`paper_maker.db` file khud-bakhud ban jayegi jab pehli baar server chalayenge
— isse delete kar ke fresh start bhi kar sakte hain.
