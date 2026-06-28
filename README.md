# AII Smart Paper Maker

AI se Bloom-tagged bilingual (Urdu+English) question generate karna, SQLite
question bank mein save karna, balanced exam paper assemble karna, student
results analyze karna (P-value / D-index item analysis ke saath), aur class ki
kamzoriyon se **adaptive paper** banana.

Phases: ✅ Phase 1 (core engine) · ✅ Phase 2 (dashboard + export) ·
✅ Phase 2.5 (item analysis) · ✅ Phase 3 (adaptive generation). Tafseel
`CLAUDE.md` mein.

## Files

Code layered structure mein hai (routes -> services -> repositories -> core).
Full rules `ARCHITECTURE.md` aur `CLAUDE.md` mein hain.

- `app/main.py` — FastAPI app entry point (routers mount + static + `init_db`)
- `app/api/` — HTTP route handlers (`questions`, `papers`, `dashboard`, `export`,
  `syllabus`, `school_settings`)
- `app/services/` — Business logic: Bloom distribution + marks (`bloom_service`),
  AI provider (`ai_service`), orchestration (`question_service`, `paper_service`,
  `syllabus_service`, `settings_service`), results + analytics (`result_service`,
  `dashboard_service`), item analysis P-value/D-index (`item_analysis_service`),
  adaptive generation (`adaptive_service`), export (`export_service`)
- `app/repositories/` — SQLite access — sirf yahan SQL strings hain
- `app/core/database.py` — Connection factory + schema bootstrap + migrations
- `app/models/` — Pydantic request + response shapes
- `import_syllabus.py` — CSV se syllabus topics import karne wala CLI
- `seed_large_class.py` — engineered ≥10-student results seed (D-index flags test karne ke liye)
- `static/index.html` — paper maker + adaptive frontend
- `static/dashboard.html` — result analyzer dashboard (rankings, P-value, D-index, flags)

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

### PDF export ke liye LibreOffice (sirf Windows par, optional)

Word (.docx) export bina kisi extra install ke chalta hai. **PDF** export ke
liye LibreOffice chahiye — app andar .docx banakar use LibreOffice se PDF mein
convert karti hai.

1. [libreoffice.org/download](https://www.libreoffice.org/download/download-libreoffice/)
   se Windows installer (64-bit) download karen.
2. Installer chalayen, **default settings** ke saath install karen. Ye
   khud-bakhud yahan install hota hai:
   ```
   C:\Program Files\LibreOffice\program\soffice.exe
   ```
3. Kuch karne ki zaroorat nahi — app is default path ko **khud dhoond leti
   hai**. Server restart karen aur PDF export try karen.

Agar tumne LibreOffice kisi **non-default jagah** install kiya hai, to `.env`
mein uska poora path do:
```
SOFFICE_PATH=D:\Apps\LibreOffice\program\soffice.exe
```
(App pehle `SOFFICE_PATH`, phir system `PATH`, phir default install locations
check karti hai.)

> Verify: PowerShell mein `& "C:\Program Files\LibreOffice\program\soffice.exe" --version`
> chala kar dekho — version number aaye to install theek hai.

## Kaise use karen

1. Subject + Topic likhen (e.g. Mathematics / Fractions)
2. "Generate questions (AI)" dabayen — ye Claude/Gemini API se bilingual,
   Bloom-tagged questions banayega aur SQLite mein save karega
3. "Build paper from bank" dabayen — balanced distribution ke hisaab se paper
   assemble hoga (har question par expected difficulty + paper balance summary)
4. Print/PDF ya Word export karen, ya `/dashboard.html` par results upload kar ke
   class performance dekhen (rankings, P-value, D-index, bad-question flags)
5. "Generate adaptive paper" — kisi paper ke uploaded results se class ki weak
   Bloom levels nikaal kar un par focus karta naya paper banata hai

Reproducible test data (D-index flags dekhne ke liye, ≥10 students chahiye):
```
python seed_large_class.py <paper_id>
```

## Agla kaam (jo abhi nahi hai)

- Syllabus PDF upload se topics auto-extract karna
- Per-student adaptive papers (abhi whole-class weakness par based hai)
- Topic-level weakness targeting (abhi Bloom-level par based hai)
- Adaptive: weak level mein question bank khali ho to AI se auto-generate

## Note

`paper_maker.db` file khud-bakhud ban jayegi jab pehli baar server chalayenge
— isse delete kar ke fresh start bhi kar sakte hain.
