# Architecture

This document describes the architecture of `paper-maker-mvp`: its layering,
folder structure, database schema, HTTP API, how the AI provider is used, and
how paper export works. It is also the **layering contract** that every
contributor (human or AI) must follow when adding or modifying code.

`CLAUDE.md` (coding conventions) sits on top of this document. If the two ever
conflict, **this document wins** — fix `CLAUDE.md`.

---

## 1. The four layers

Dependencies point **downward only**. A lower layer never imports an upper one.

```
        ┌────────────────────────────────────────────┐
        │  HTTP client (browser, curl, frontend JS)  │
        └─────────────────────┬──────────────────────┘
                              │ JSON over HTTP
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │  ROUTES        (app/api/*.py)                            │
   │  FastAPI handlers. Parse, validate, map errors, return   │
   │  JSON. Nothing else.                                     │
   └─────────────────────┬────────────────────────────────────┘
                         │ plain Python args / domain dicts
                         ▼
   ┌──────────────────────────────────────────────────────────┐
   │  SERVICES      (app/services/*.py)                       │
   │  Business rules, orchestration, external API calls (AI). │
   │  Knows repositories, not SQL. Raises domain exceptions.  │
   └─────────────────────┬────────────────────────────────────┘
                         │ plain Python args / domain dicts
                         ▼
   ┌──────────────────────────────────────────────────────────┐
   │  REPOSITORIES  (app/repositories/*.py)                  │
   │  The ONLY place SQL strings live. One repo per table.    │
   │  Returns plain dicts.                                    │
   └─────────────────────┬────────────────────────────────────┘
                         │ sqlite3 connection
                         ▼
   ┌──────────────────────────────────────────────────────────┐
   │  DATABASE      (app/core/database.py)                    │
   │  Connection factory, schema bootstrap, migrations.       │
   │  SQLite today; swappable for Postgres tomorrow.          │
   └──────────────────────────────────────────────────────────┘
```

`app/schemas/` (Pydantic request/response shapes) is a supporting module, not a
layer: imported by routes for validation and sometimes by services for typed
inputs. Schemas carry **shape, not behavior** — no DB access, no AI calls.

### Layer responsibilities

- **Routes** (`app/api/`) — define endpoint paths and methods, validate request
  bodies with Pydantic, call exactly one service, translate domain exceptions to
  `HTTPException` with the right status code, return JSON. No SQL, no AI calls,
  no business math.
- **Services** (`app/services/`) — implement use cases, orchestrate repositories
  and pure helpers, hold business rules (Bloom math, marks, prompt design,
  provider fallback), talk to external systems (Gemini/Claude), and raise domain
  exceptions. No FastAPI imports, no SQL.
- **Repositories** (`app/repositories/`) — own every `SELECT`/`INSERT`/`UPDATE`/
  `DELETE` for one table, return plain dicts, translate `sqlite3.Row` so callers
  never see the driver type. No business rules, no calls to other repos or
  services, no `HTTPException`.
- **Database** (`app/core/database.py`) — provides `get_connection()`, runs
  `init_db()` and idempotent migrations at startup, hides the SQLite-vs-Postgres
  choice.

---

## 2. The Golden Rules (enforce in every review)

These are non-negotiable. If a change violates one, restructure the change —
don't make an exception.

1. **Routes only handle HTTP.** A route body is: validate input → call one
   service → map domain errors to HTTP status → return. No SQL, no
   `requests.post`, no business math.
2. **Business logic lives in services.** Any rule-based decision
   ("foundational distribution puts 40% on REMEMBER") is in a service or a pure
   helper — never a route, never a repository.
3. **DB access only in repositories.** The strings `SELECT `, `INSERT `,
   `UPDATE `, `DELETE ` appear only under `app/repositories/` (and DDL in
   `app/core/database.py`).
4. **No layer skipping.** Routes call services; services call repositories;
   repositories call the database layer. No shortcuts, even for "one quick
   query."
5. **Dependencies point down.** Lower layers never import upper ones.
6. **One service call per route.** If two services must cooperate, that
   orchestration is itself a service — name it and put it in `app/services/`.
7. **CLI scripts obey the same rules.** `import_syllabus.py`, `seed_large_class.py`
   and any future scripts call services, not raw SQL. A CLI is just another
   transport above services.

### Anti-patterns to reject

- A route importing `sqlite3`, `get_connection()`, or a repository.
- A service importing `fastapi` or raising `HTTPException`.
- A repository method with a business verb in its name (`pick_balanced_*`,
  `generate_*`) — repositories *fetch* and *store*, they don't decide.
- A repository calling another repository or a service.
- A `utils.py` / `helpers.py` / `common.py` kitchen-sink module.
- A CLI opening its own SQLite connection.

---

## 3. Folder structure

```
paper-maker-mvp/
├── app/
│   ├── main.py                 # FastAPI app: CORS, init_db(), mount routers + static
│   ├── api/                    # ROUTES — one module per resource
│   │   ├── questions.py        #   /api/generate-questions, /api/questions
│   │   ├── papers.py           #   paper assembly, adaptive, replace, results upload
│   │   ├── dashboard.py        #   result analyzer read views
│   │   ├── export.py           #   /export.docx, /export.pdf
│   │   ├── syllabus.py         #   syllabus grades/topics + PDF/ZIP import
│   │   ├── school_settings.py  #   letterhead settings (singleton)
│   │   └── stats.py            #   home-screen quick stats
│   ├── services/               # SERVICES — business logic
│   │   ├── ai_service.py       #   AI provider integration + prompt building
│   │   ├── bloom_service.py    #   Bloom distribution + marks (pure)
│   │   ├── question_service.py #   generate + persist + list questions
│   │   ├── paper_service.py    #   balanced/adaptive assembly, replace, fetch
│   │   ├── adaptive_service.py #   weak-Bloom-level weighting (pure)
│   │   ├── item_analysis_service.py  # P-value / D-index / flags (pure)
│   │   ├── result_service.py   #   results template, import, validation
│   │   ├── dashboard_service.py#   rankings + per-question/per-Bloom views
│   │   ├── syllabus_service.py #   PDF/ZIP parse -> AI extract -> save topics
│   │   ├── settings_service.py #   school settings get/save
│   │   ├── stats_service.py    #   quick stats aggregation
│   │   ├── export_service.py   #   .docx render + PDF conversion
│   │   └── exceptions.py       #   domain exceptions (raised by services)
│   ├── repositories/           # REPOSITORIES — the only SQL
│   │   ├── questions_repository.py
│   │   ├── papers_repository.py
│   │   ├── syllabus_repository.py
│   │   ├── settings_repository.py
│   │   ├── result_repository.py
│   │   └── usage_log_repository.py
│   ├── core/
│   │   └── database.py         # DATABASE — connection factory + schema + migrations
│   └── schemas/
│       ├── requests.py         # Pydantic *Request models
│       └── responses.py        # Pydantic *Response models
├── static/
│   ├── index.html              # paper maker + adaptive frontend
│   ├── dashboard.html          # result analyzer dashboard
│   └── print.html              # printable paper layout (mirrored by .docx export)
├── tests/                      # pytest suite (services, repos, HTTP routes)
├── import_syllabus.py          # CLI: import syllabus topics from CSV
├── seed_large_class.py         # CLI: seed engineered >=10-student results
├── requirements.txt
├── railway.toml                # Railway deploy config
├── pyproject.toml              # ruff + black config
├── pytest.ini
├── .python-version             # 3.12
├── .github/workflows/ci.yml    # lint + format + tests
├── ARCHITECTURE.md             # this file — layering contract + reference
├── CLAUDE.md                   # coding conventions
├── PROJECT.md                  # phase log + status
└── paper_maker.db              # SQLite database (gitignored, auto-created)
```

`app/main.py` is the composition root: it configures CORS, calls `init_db()`
once at import time, includes every router, and mounts `static/` at `/` (so the
frontend is served from the same origin as the API).

---

## 4. Database schema

SQLite, one file (`paper_maker.db`). Schema is created and migrated in
`app/core/database.py::init_db()`, which runs at startup. Fresh installs get the
full `CREATE TABLE IF NOT EXISTS` set; existing DBs get idempotent
`ALTER TABLE ... ADD COLUMN` migrations (see the `visual_emoji` / `visual_count`
example). Every schema change requires **both** the column in the CREATE block
and an idempotent migration step.

Foreign keys are declared for documentation but not enforced (SQLite has FK
enforcement off by default; no `PRAGMA foreign_keys = ON`).

### `questions` — the question bank

| Column                | Type    | Notes                                             |
|-----------------------|---------|---------------------------------------------------|
| `id`                  | TEXT PK | UUID string                                       |
| `subject`             | TEXT    | not null                                          |
| `topic`               | TEXT    | not null                                          |
| `bloom_level`         | TEXT    | one of REMEMBER…CREATE (canonical uppercase)      |
| `difficulty`          | TEXT    | easy / medium / hard                              |
| `question_type`       | TEXT    | e.g. multiple-choice                              |
| `marks`               | INTEGER | not null                                          |
| `question_en`         | TEXT    | English question text                             |
| `question_ur`         | TEXT    | Urdu question text                                |
| `options_en`          | TEXT    | JSON array (MCQ options, English)                 |
| `options_ur`          | TEXT    | JSON array (MCQ options, Urdu)                    |
| `correct_answer_en`   | TEXT    |                                                   |
| `correct_answer_ur`   | TEXT    |                                                   |
| `explanation_en`      | TEXT    |                                                   |
| `explanation_ur`      | TEXT    |                                                   |
| `visual_emoji`        | TEXT    | optional emoji for young-learner counting visuals |
| `visual_count`        | INTEGER | how many emojis to render                         |
| `usage_count`         | INTEGER | default 0; incremented when used in a paper       |
| `created_at`          | TEXT    | default CURRENT_TIMESTAMP                          |

### `papers` — assembled papers

| Column         | Type    | Notes                                       |
|----------------|---------|---------------------------------------------|
| `id`           | TEXT PK | UUID string                                 |
| `subject`      | TEXT    | not null                                    |
| `class_name`   | TEXT    | optional                                    |
| `total_marks`  | INTEGER | not null                                    |
| `question_ids` | TEXT    | JSON array of `questions.id`, in paper order|
| `created_at`   | TEXT    | default CURRENT_TIMESTAMP                    |

### `syllabus_topics` — imported curriculum

| Column            | Type    | Notes                                                      |
|-------------------|---------|------------------------------------------------------------|
| `id`              | TEXT PK | UUID string                                                |
| `subject`         | TEXT    | not null                                                   |
| `grade`           | TEXT    |                                                            |
| `unit_no`         | INTEGER | not null                                                   |
| `unit_title`      | TEXT    | not null                                                   |
| `page_range`      | TEXT    |                                                            |
| `subtopic_title`  | TEXT    | not null                                                   |
| `activity_type`   | TEXT    | Introduction / Identification / Practice / Review          |
| `page_no`         | INTEGER |                                                            |
| `learning_outcome`| TEXT    |                                                            |
|                   |         | UNIQUE(subject, grade, unit_no, subtopic_title, page_no)   |

`activity_type` maps to a suggested difficulty when a topic is used to generate
questions (the book's own cognitive tagging drives the difficulty).

### `school_settings` — letterhead (singleton, `id = 1`)

| Column           | Type       | Notes                          |
|------------------|------------|--------------------------------|
| `id`             | INTEGER PK | singleton row                  |
| `school_name`    | TEXT       | English                        |
| `school_name_ur` | TEXT       | Urdu                           |
| `address`        | TEXT       |                                |
| `address_ur`     | TEXT       |                                |
| `logo_base64`    | TEXT       | raw base64 or a data URL       |
| `accent_color`   | TEXT       | hex, drives letterhead accent  |

### `usage_log` — per-call AI usage (billing base)

| Column          | Type    | Notes                              |
|-----------------|---------|------------------------------------|
| `id`            | TEXT PK | UUID string                        |
| `timestamp`     | TEXT    | default CURRENT_TIMESTAMP          |
| `provider`      | TEXT    | gemini / claude                    |
| `model`         | TEXT    | model id                           |
| `status`        | TEXT    | success                            |
| `input_tokens`  | INTEGER |                                    |
| `output_tokens` | INTEGER |                                    |
| `total_tokens`  | INTEGER |                                    |

One row per successful AI call — written *after* the provider responds (they've
already charged for the tokens) and before any parsing that could raise.

### `result_uploads` — one row per uploaded results sheet

| Column        | Type    | Notes                          |
|---------------|---------|--------------------------------|
| `id`          | TEXT PK | UUID string                    |
| `paper_id`    | TEXT    | → `papers.id`                  |
| `filename`    | TEXT    | not null                       |
| `uploaded_at` | TEXT    | default CURRENT_TIMESTAMP      |

### `student_question_results` — one row per student × question

| Column             | Type    | Notes                          |
|--------------------|---------|--------------------------------|
| `id`               | TEXT PK | UUID string                    |
| `result_upload_id` | TEXT    | → `result_uploads.id`          |
| `roll_no`          | TEXT    | not null                       |
| `student_name`     | TEXT    |                                |
| `question_id`      | TEXT    | → `questions.id`               |
| `marks_obtained`   | INTEGER | not null                       |

---

## 5. API endpoints

All application endpoints live under `/api/…`; `/` serves the static frontend.
Paths use kebab-case. FastAPI serves interactive docs at `/docs`.

### Questions

| Method | Path                       | Purpose                                                     |
|--------|----------------------------|-------------------------------------------------------------|
| POST   | `/api/generate-questions`  | Generate bilingual Bloom-tagged questions via AI and save.  |
| GET    | `/api/questions`           | List/filter the bank by `subject`, `topic`, `bloom_level`.  |

### Papers

| Method | Path                                    | Purpose                                                        |
|--------|-----------------------------------------|----------------------------------------------------------------|
| POST   | `/api/generate-paper`                   | Assemble a balanced paper (Bloom + difficulty distribution).   |
| POST   | `/api/generate-adaptive-paper`          | Assemble a paper weighted toward a class's weak Bloom levels.  |
| POST   | `/api/paper/{paper_id}/replace-question`| Swap a question; recompute marks + balance.                    |
| GET    | `/api/paper/{paper_id}`                 | Fetch a paper with its questions and expected difficulty.      |
| GET    | `/api/paper/{paper_id}/result-template` | Download an empty results CSV template.                        |
| POST   | `/api/paper/{paper_id}/upload-results`  | Upload a filled results CSV/XLSX (validated).                  |

### Dashboard (result analyzer)

| Method | Path                                | Purpose                                            |
|--------|-------------------------------------|----------------------------------------------------|
| GET    | `/api/paper/{paper_id}/uploads`     | List a paper's result uploads (newest first).      |
| GET    | `/api/paper/{paper_id}/dashboard`   | Full dashboard for the paper's latest upload.      |
| GET    | `/api/upload/{upload_id}/dashboard` | Full dashboard for a specific upload.              |

### Export

| Method | Path                              | Purpose                                    |
|--------|-----------------------------------|--------------------------------------------|
| GET    | `/api/paper/{paper_id}/export.docx` | Download the paper as Word (.docx).      |
| GET    | `/api/paper/{paper_id}/export.pdf`  | Download the paper as PDF (via LibreOffice).|

### Syllabus & settings

| Method | Path                          | Purpose                                                |
|--------|-------------------------------|--------------------------------------------------------|
| GET    | `/api/syllabus-grades`        | Distinct (subject, grade) pairs that have been imported.|
| GET    | `/api/syllabus-topics`        | Topics for a `subject`/`grade`, with suggested difficulty.|
| POST   | `/api/syllabus/upload-pdf`    | Import topics from a text-based PDF (multipart form).  |
| POST   | `/api/syllabus/upload-zip`    | Import topics from a ZIP of PDFs + images (per-file results). |
| GET    | `/api/school-settings`        | Read the singleton letterhead settings.                |
| POST   | `/api/school-settings`        | Save letterhead settings.                              |

### Stats

| Method | Path         | Purpose                                                        |
|--------|--------------|----------------------------------------------------------------|
| GET    | `/api/stats` | Home quick stats: paper count, uploads this month, top subject, bank size. |

### Error-handling convention

Every handler returns JSON on **every** path. Services raise domain exceptions
(`app/services/exceptions.py`); routes catch them and map to status codes:

| Status | Meaning                                                            |
|--------|-------------------------------------------------------------------|
| 400    | Valid request shape, failed business validation.                  |
| 404    | Referenced resource doesn't exist.                                |
| 422    | Pydantic validation failed (FastAPI does this automatically).     |
| 500    | Our code / DB broke.                                              |
| 502    | Upstream provider broke (Gemini/Claude, or LibreOffice for PDF).  |

Detail strings are short, user-facing, and Hinglish-OK (the frontend shows them
directly to teachers).

---

## 6. How the AI provider is used (`ai_service.py`)

`app/services/ai_service.py` is the single boundary to the AI providers. It is
the only module that reads the provider API keys.

**Provider selection (fixed in code, not config):**

- If `ANTHROPIC_API_KEY` is set → **Claude** (`claude-sonnet-4-6`) is used.
- Else if `GEMINI_API_KEY` is set → **Gemini** (`gemini-2.5-flash`) is used.
- Else → a `RuntimeError` explaining that a key is needed.

Anthropic wins over Gemini when both are present, so switching to higher quality
is just adding the Anthropic key. Both providers return the **same shape**
(`list[dict]`), so callers never know which one answered.

**Prompt building is separate from the HTTP call** so prompts are unit-testable
without network:

- `build_prompt(...)` — question generation. Encodes the subject, topic,
  requested difficulty, a per-difficulty **calibration guidance** block
  (`DIFFICULTY_GUIDANCE`), the exact Bloom distribution counts, bilingual
  (English + Urdu-script) requirements, MCQ format (4 options each language),
  and the optional `visual_emoji`/`visual_count` fields for young-learner
  counting questions. It demands a strict JSON-only response.
- `build_syllabus_extraction_prompt(...)` / `build_syllabus_image_prompt(...)` —
  syllabus topic extraction from raw text or a page image; both share one set of
  extraction rules and the same JSON output shape.

**The three public entry points:**

- `generate_questions_from_ai(topic, subject, bloom_distribution, question_types, difficulty)`
- `extract_topics_from_text(syllabus_text, subject, grade)`
- `extract_topics_from_image(image_bytes, mime_type, subject, grade)` (vision)

Each builds a prompt, calls `_call_ai(...)`, and parses with `_extract_json(...)`.

**Transport details:**

- `_call_ai` dispatches to `_call_claude` or `_call_gemini`, optionally passing
  an `(mime_type, raw_bytes)` image for vision.
- Gemini receives its key in the **`x-goog-api-key` header** (never in the URL),
  so it can't leak into error messages or logs. Claude uses the `x-api-key`
  header with `anthropic-version: 2023-06-01`.
- Both log token usage to `usage_log` on success, before further parsing.
- Network/HTTP failures are wrapped in `AIGenerationFailed` with a short,
  key-free message (`_provider_error_message` never includes the URL or response
  body). Truncated/invalid JSON produces a user-friendly "try smaller input"
  message via `_extract_json`, not a raw traceback.

---

## 7. Export flow

Export is handled by `app/services/export_service.py`. One layout, two formats:
the PDF is rendered from the exact same `.docx`.

**Word (`.docx`):** `build_paper_docx(paper_id)`

1. `_load_paper` fetches the paper (`papers_repository`), each question
   (`questions_repository`), and the letterhead (`settings_repository`).
   Returns `None` if the paper doesn't exist → the route maps that to 404.
2. `_render_paper` builds the document with python-docx, mirroring
   `static/print.html`: letterhead (logo, school name EN/UR, address, accent
   bottom border), title, meta table (name/class/date/roll/marks/time), a
   bilingual instruction line, then numbered questions.
3. Each question renders the English text with its marks, the Urdu text as a
   right-to-left paragraph, an optional emoji visual row, and MCQ options in a
   two-column grid (or an answer line if none).
4. **Urdu handling:** Urdu runs get the complex-script font
   (`Jameel Noori Nastaleeq` on `w:rFonts w:cs`) plus a `w:rtl` flag, and their
   paragraphs are marked `w:bidi` so Word lays them out right-to-left.
5. Returns the `.docx` as bytes; the route streams it with a `.docx`
   `Content-Disposition`.

**PDF:** `build_paper_pdf(paper_id)`

1. Calls `build_paper_docx` first (same bytes, `None` → 404).
2. `_convert_docx_to_pdf` locates the LibreOffice binary via `_find_soffice`
   (`SOFFICE_PATH` → PATH → common install locations). If not found, raises
   `PdfConversionFailed` → route maps to 502. Word export still works without
   LibreOffice.
3. Writes the `.docx` to a temp dir and runs headless LibreOffice:
   `soffice --headless -env:UserInstallation=<profile> --convert-to pdf --outdir <tmp> <docx>`.
   A **persistent profile** in the system temp dir is reused across calls so
   warm conversions are fast (~13s vs ~50s cold). Timeout is 120s.
4. On non-zero exit / missing output / timeout, raises `PdfConversionFailed`
   with the trimmed LibreOffice stderr. Otherwise returns the PDF bytes.

For faithful Urdu output the **Jameel Noori Nastaleeq** font must be installed
on the machine that runs LibreOffice; otherwise a fallback font is substituted.
The conversion assumes a single concurrent conversion (single-school MVP) — the
LibreOffice profile lock means concurrent calls can clash; async is out of scope
(see §8).

---

## 8. Out of scope (for now)

Not built yet; extend this doc rather than bending the layering when they land:

- Authentication / authorization — single-school MVP, no auth today.
- Background jobs / async — AI calls and PDF conversion are synchronous.
- Multi-tenant data isolation — one school per database.
- Caching / rate-limiting — premature until usage warrants it.
- Per-student adaptive papers, topic-level weakness targeting, and OCR for
  scanned image-only PDFs (see `PROJECT.md`).
