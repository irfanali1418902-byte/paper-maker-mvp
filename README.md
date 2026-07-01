# AII Smart Paper Maker

An AI-powered exam paper generator built for a school in Swat, Pakistan. It
generates **bilingual (English + Urdu), Bloom-tagged** questions with AI, stores
them in a local SQLite question bank, assembles balanced exam papers, analyzes
student results with psychometric item analysis (P-value / D-index), and can
build **adaptive papers** that target a class's weakest Bloom levels.

Everything runs from a single Python process and one SQLite file — no external
database server, no cloud dependency beyond the AI provider.

---

## Features

- **AI question generation** — produces questions in both English and proper
  Urdu script, each tagged with a Bloom's Taxonomy level
  (`REMEMBER … CREATE`) and calibrated to a requested difficulty (easy /
  medium / hard). Supports multiple-choice (with 4 bilingual options) and other
  question types, plus optional emoji "visuals" for young-learner counting
  questions.
- **Question bank** — every generated question is saved to SQLite and can be
  browsed and filtered by subject, topic, and Bloom level.
- **Balanced paper assembly** — builds a paper from the bank according to a
  Bloom + difficulty distribution, prioritizing least-used questions to reduce
  repetition, and reports an expected-difficulty balance summary.
- **Manual question replacement** — swap any question in an assembled paper for
  another from the bank; total marks and balance are recomputed.
- **Result analyzer dashboard** — teachers download a CSV template, fill in
  marks offline, upload it back, and get per-student rankings (competition
  style, ties share a rank), pass/fail against the 33% KPK board threshold, and
  per-question / per-Bloom breakdowns.
- **Item analysis (psychometrics)** — Difficulty Index (P-value) and
  Discrimination Index (D) per question, with automatic bad-question flags
  (too easy, too hard, negative discrimination / likely mis-keyed). D is marked
  unreliable for classes under 10 students.
- **Adaptive paper generation** — reads a source paper's latest results,
  derives the class's weak Bloom levels, and weights a new paper toward them.
- **Syllabus import** — upload a text-based PDF, or a ZIP of PDFs and page
  images (JPG/PNG), and the AI extracts structured units/topics (using vision
  for images) so teachers can select topics from a dropdown instead of typing.
- **Export** — download any paper as an editable Word `.docx` (with Urdu RTL /
  Nastaliq support) or as a PDF (rendered from the same `.docx` via headless
  LibreOffice). Papers carry an optional school letterhead (name, address,
  logo, accent color).

---

## Tech stack

| Layer        | Choice                                                        |
|--------------|---------------------------------------------------------------|
| Language     | Python 3.12 (3.10+ supported)                                 |
| Web framework| FastAPI + Uvicorn (ASGI)                                       |
| Data models  | Pydantic v2                                                   |
| Database     | SQLite (single `paper_maker.db` file)                         |
| AI providers | Google Gemini (`gemini-2.5-flash`) or Anthropic Claude (`claude-sonnet-4-6`) |
| HTTP client  | `requests` (to the AI providers)                              |
| PDF parsing  | PyMuPDF (text + page-image extraction for syllabus import)    |
| Spreadsheets | pandas + openpyxl (results template / upload)                 |
| Word export  | python-docx                                                   |
| PDF export   | headless LibreOffice (`soffice --convert-to pdf`)             |
| Frontend     | Static HTML/JS (`static/`) served by FastAPI                  |
| Urdu font    | Jameel Noori Nastaleeq (must be installed on the box that renders PDFs) |
| Tooling      | ruff (lint), black (format), pytest (tests), pre-commit       |
| Deployment   | Railway (Nixpacks) — see `railway.toml`                       |

The codebase follows a strict layered architecture (routes → services →
repositories → database). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full
contract and [`CLAUDE.md`](CLAUDE.md) for coding conventions.

---

## Local setup

### 1. Prerequisites

- Python 3.10 or newer (3.12 is the pinned version in `.python-version`).
- Git.
- (Optional, for PDF export only) LibreOffice — see
  [PDF export](#pdf-export-libreoffice) below.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Using a virtual environment is recommended:

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and add at least one AI provider key:

```bash
cp .env.example .env
```

Then edit `.env`. The minimum needed to run is one key:

```
GEMINI_API_KEY=your-gemini-api-key-here
```

`python-dotenv` loads `.env` automatically at startup — you don't need to
export anything manually. See [Environment variables](#environment-variables)
for the full list.

### 4. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

The SQLite database (`paper_maker.db`) is created automatically on first start,
and the schema is migrated in-place on every start. Delete the file to start
fresh.

### 5. Open the app

- Paper maker + adaptive UI: <http://localhost:8000>
- Result analyzer dashboard: <http://localhost:8000/dashboard.html>
- Interactive API docs (Swagger): <http://localhost:8000/docs>

---

## Environment variables

All are optional individually, but **at least one AI key is required** for
generation to work. Full descriptions and placeholders are in `.env.example`.

| Variable            | Required?                         | Purpose                                                                 |
|---------------------|-----------------------------------|-------------------------------------------------------------------------|
| `GEMINI_API_KEY`    | One of Gemini/Anthropic           | Google Gemini key (free tier). Used when Anthropic key is absent.       |
| `ANTHROPIC_API_KEY` | One of Gemini/Anthropic           | Anthropic Claude key (paid). **Takes priority** over Gemini if set.     |
| `DB_PATH`           | No (defaults to `paper_maker.db`) | Absolute/relative path to the SQLite file (point at a volume in prod).  |
| `SOFFICE_PATH`      | No (auto-detected)                | Explicit path to the LibreOffice `soffice` binary for PDF export.       |
| `PORT`              | No (deploy only)                  | Port for the deploy start command; Railway injects it automatically.    |

Never commit `.env`. `.gitignore` already ignores `.env` and `.env.*`.

---

## How to use

1. Enter a **Subject** and **Topic** (e.g. Mathematics / Fractions), or pick a
   topic from the syllabus dropdown if you imported one.
2. Click **Generate questions (AI)** — the AI returns bilingual, Bloom-tagged
   questions and saves them to the bank.
3. Click **Build paper from bank** — a balanced paper is assembled (each
   question shows its expected difficulty, plus a paper-level balance summary).
   You can manually replace individual questions from the bank.
4. **Export** the paper as Word or PDF, or print it.
5. Download the **results CSV template**, fill in each student's marks per
   question, and upload it on the dashboard (`/dashboard.html`) to see
   rankings, P-value, D-index, and bad-question flags.
6. Click **Generate adaptive paper** to build a new paper focused on the Bloom
   levels the class scored weakest on in an uploaded result set.

**Syllabus upload (optional):** in the "Syllabus upload" panel, upload a
text-based PDF or a ZIP (multiple PDFs + JPG/PNG images). The AI extracts
units/topics (reading images via vision) and saves them; they then appear in
the topic dropdown.

### Reproducible test data

To exercise the D-index flags you need at least 10 students. Seed an engineered
result set for an existing paper:

```bash
python seed_large_class.py <paper_id>
```

### PDF export (LibreOffice)

Word (`.docx`) export works with no extra install. **PDF** export needs
LibreOffice — the app builds the `.docx` internally and converts it to PDF via
a headless LibreOffice subprocess.

1. Install LibreOffice (64-bit) from
   <https://www.libreoffice.org/download/download-libreoffice/> with default
   settings.
2. The app auto-detects the binary in this order:
   `SOFFICE_PATH` env → system `PATH` → common install locations (e.g.
   `C:\Program Files\LibreOffice\program\soffice.exe`, `/usr/bin/soffice`).
   In most cases you don't need to configure anything.
3. If installed to a non-default location, set `SOFFICE_PATH` in `.env`.

For faithful Urdu rendering in the PDF, the **Jameel Noori Nastaleeq** font must
be installed on the machine that renders the PDF; otherwise LibreOffice
substitutes a fallback font.

---

## Running tests

```bash
python -m pytest tests/ -v
```

or, matching CI:

```bash
pytest -q
```

Tests run against an isolated temporary SQLite database and mock the AI
provider, so **no API keys or network access are required**. The suite covers
services, repositories, and the HTTP routes.

Lint and format checks (also enforced in CI and via pre-commit):

```bash
ruff check .
black --check .
```

To install the git pre-commit hooks locally:

```bash
pre-commit install
```

---

## Deployment

The app is configured for **Railway** (see `railway.toml`):

- **Builder:** Nixpacks — detects `requirements.txt` and installs with pip.
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  (Railway injects `$PORT`; do not use `--reload` in production).
- **Healthcheck:** `GET /` — serves the static frontend, so it returns 200 once
  the app is ready.
- **Restart policy:** on failure, up to 10 retries.

Deployment checklist:

- Set `ANTHROPIC_API_KEY` (or `GEMINI_API_KEY`) in the environment.
- Set `DB_PATH` to a path on a **persistent volume** (e.g.
  `/data/paper_maker.db`) — the container filesystem is ephemeral, so without a
  volume all data is lost on every redeploy.
- For PDF export in production, ensure LibreOffice and the Urdu font are
  installed in the runtime image, or set `SOFFICE_PATH` accordingly. Word export
  works without them.

Any host that can run Python and Uvicorn works the same way — the only
environment-specific pieces are the AI key, `DB_PATH`, and (optionally)
LibreOffice for PDF.

### CI

`.github/workflows/ci.yml` runs on every push to `master` and every pull
request: `ruff check` → `black --check` → `pytest -q`. No secrets are needed
because the AI provider is mocked and tests use a temporary SQLite DB.

---

## Project status

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1   | Core engine — AI generation, Bloom tagging, question bank, balanced paper assembly, frontend | ✅ Complete |
| Phase 2   | Result analyzer dashboard, rankings, Word + PDF export | ✅ Complete |
| Phase 2.5 | Item analysis — P-value, D-index, bad-question flags | ✅ Complete |
| Phase 3   | Adaptive paper generation from class weaknesses | ✅ Complete |

Planned / not yet built: per-student adaptive papers (currently whole-class),
topic-level weakness targeting (currently Bloom-level), auto-generating
questions when the bank is empty for a weak level, and OCR for scanned
image-only PDFs (image-based syllabus pages are handled via the ZIP + vision
path).

See `PROJECT.md` for the detailed phase log and `ARCHITECTURE.md` for the system
design.
