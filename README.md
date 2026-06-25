# AII Smart Paper Maker — Phase 1 MVP

Ye Phase 1 ka core engine hai: AI se Bloom-tagged bilingual (Urdu+English)
question generate karna, SQLite question bank mein save karna, aur usse
balanced exam paper assemble karna.

## Files

- `database.py` — SQLite setup (questions + papers tables)
- `bloom_engine.py` — Bloom's Taxonomy distribution % aur marks calculation
- `ai_generator.py` — Claude API se bilingual questions generate karne ka prompt + logic
- `main.py` — FastAPI app (sab API endpoints)
- `static/index.html` — Testing ke liye simple bilingual frontend

## Setup (apne computer/VPS par)

1. Python 3.10+ installed hona chahiye.

2. Dependencies install karen:
   ```
   pip install -r requirements.txt
   ```

3. `.env.example` ko `.env` rename karen.

   **FREE option (Gemini)** — testing ke liye recommended, koi card nahi chahiye:
   - [aistudio.google.com](https://aistudio.google.com) par Google account se login karen
   - "Get API key" par click kar ke key generate karen
   - `.env` file mein `GEMINI_API_KEY=` ke aage paste karen

   **PAID option (Claude)** — jab production/AII deployment ke liye behtar
   quality chahiye ho:
   - console.anthropic.com se key len, `.env` mein `ANTHROPIC_API_KEY=` ke
     aage paste karen
   - Agar ye key bhi set hai to code automatically isi ko use karega
     (Gemini ko ignore kar dega)

   Phir terminal mein jo bhi key use kar rahe hain wo load karen
   (Windows PowerShell):
   ```
   $env:GEMINI_API_KEY="apni-gemini-key"
   ```
   ya
   ```
   $env:ANTHROPIC_API_KEY="sk-ant-..."
   ```

4. Server chalayen:
   ```
   uvicorn main:app --reload --port 8000
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
