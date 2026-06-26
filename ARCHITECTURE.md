# Architecture

This document defines the target layered architecture for `paper-maker-mvp`
and the rules every contributor (human or AI) must follow when adding or
modifying code.

It exists because the current Phase 1 MVP is intentionally monolithic
(`main.py` does HTTP routing, business logic, AND direct SQL), and we are
about to refactor toward something we can grow without rewriting. This doc
is the contract that refactor will land against.

---

## 1. Current state (Phase 1 MVP) — what is here today

| File | What it actually does today |
|---|---|
| `main.py` | FastAPI app object, CORS middleware, Pydantic request models, **all** route handlers. Each handler does its own SQL via `get_connection()`, calls `bloom_engine`, calls `ai_generator`, and returns the JSON. Routes own everything. |
| `database.py` | SQLite connection factory + `init_db()` schema bootstrap (with an idempotent `ALTER TABLE` migration for the `visual_emoji`/`visual_count` columns). |
| `bloom_engine.py` | Pure functions: `calculate_bloom_distribution`, `calculate_marks`. No IO. Already shaped like a service. |
| `ai_generator.py` | External provider integration (Gemini / Claude). Prompt building + HTTP calls + JSON extraction. Already shaped like a service. |
| `import_syllabus.py` | CLI utility that reads CSV and writes directly to `syllabus_topics`. Also bypasses the layering (CLI → SQL). |

The MVP works — the checkpoint commit (`ddd1c59`) proves it end-to-end. But
the boundaries are blurred: a route handler can today do anything, which
means tomorrow a route handler will do anything. Hence this doc.

---

## 2. Target architecture — the four layers

```
            ┌────────────────────────────────────────────┐
            │  HTTP client (browser, curl, frontend JS)  │
            └─────────────────────┬──────────────────────┘
                                  │ JSON over HTTP
                                  ▼
   ┌────────────────────────────────────────────────────────────┐
   │  ROUTES        (app/api/*.py)                              │
   │  FastAPI handlers. Parse, validate, return JSON. Nothing   │
   │  else.                                                     │
   └─────────────────────┬──────────────────────────────────────┘
                         │ plain Python args / domain dicts
                         ▼
   ┌────────────────────────────────────────────────────────────┐
   │  SERVICES      (app/services/*.py)                         │
   │  Business rules, orchestration, external API calls (AI).   │
   │  Pure-ish Python. Knows about repositories, not SQL.       │
   └─────────────────────┬──────────────────────────────────────┘
                         │ plain Python args / domain dicts
                         ▼
   ┌────────────────────────────────────────────────────────────┐
   │  REPOSITORIES  (app/repositories/*.py)                     │
   │  The ONLY place SQL strings live. One repository per       │
   │  table/aggregate. Returns dicts / domain objects.          │
   └─────────────────────┬──────────────────────────────────────┘
                         │ sqlite3 connection
                         ▼
   ┌────────────────────────────────────────────────────────────┐
   │  DATABASE      (app/core/*.py)                             │
   │  Connection factory, schema bootstrap, migrations. SQLite  │
   │  today; swappable for Postgres tomorrow without touching   │
   │  routes or services.                                       │
   └────────────────────────────────────────────────────────────┘
```

Dependencies point **downward only**. A repository must never import a
service. A service must never import a route. The database layer must
never import anything from the project — it stands alone at the bottom.

---

## 3. Layer responsibilities — what each layer does and does NOT do

### 3.1 Routes (`app/api/`)

**Does:**
- Define FastAPI endpoint paths and HTTP methods.
- Validate request bodies with Pydantic models (defined under `app/models/`).
- Call exactly one service method per route (orchestration belongs to the
  service, not the route).
- Translate domain exceptions into `HTTPException` with the right status code.
- Return JSON-serializable values.

**Does NOT:**
- Import `sqlite3`, `get_connection()`, or any repository directly.
- Write business rules ("if difficulty is hard, add 2 marks" — no, that's a
  service or pure helper).
- Format prompts or call external APIs.
- Loop over rows and mutate them.

A route handler should fit on one screen and read like a five-line story:
*parse → call service → map errors → return*.

### 3.2 Services (`app/services/`)

**Does:**
- Implement use cases (`generate_questions_for_topic`, `assemble_balanced_paper`).
- Orchestrate multiple repositories + pure helpers in one transaction-shaped
  unit of work.
- Hold business rules (Bloom distribution math, marks calculation, AI prompt
  design, retry/fallback policy between providers).
- Talk to external systems (Gemini, Claude, future S3, future email).
- Raise domain exceptions (e.g. `SyllabusTopicNotFound`, `AIGenerationFailed`)
  that the route layer translates to HTTP codes.

**Does NOT:**
- Import FastAPI, `Request`, `HTTPException`, or anything HTTP-shaped.
- Write SQL strings or call `get_connection()`.
- Know what status code a failure should map to.

A service should be testable with `pytest` without spinning up a web server.

### 3.3 Repositories (`app/repositories/`)

**Does:**
- Own every `SELECT` / `INSERT` / `UPDATE` / `DELETE` for one table or
  aggregate (`questions_repository.py`, `papers_repository.py`,
  `syllabus_repository.py`, `settings_repository.py`).
- Open a connection via the database layer, run the query, close the
  connection, return plain `dict` rows or a list thereof.
- Translate `sqlite3.Row` into ordinary dicts so callers never depend on the
  driver type.

**Does NOT:**
- Implement business rules. A method called `get_balanced_questions(...)`
  that does Bloom math inside the SQL is doing two jobs — split it.
- Call services or other repositories. Repositories are leaves.
- Raise `HTTPException`. Raise a plain exception or return `None`; let the
  service decide what that means.

If a repository method needs data from another table, the **service** joins
the calls — not the repository.

### 3.4 Database (`app/core/`)

**Does:**
- Provide `get_connection()`.
- Run `init_db()` / migrations at app startup.
- Hide the choice of SQLite vs Postgres behind a tiny interface.

**Does NOT:**
- Know what tables exist for business reasons. Schema DDL lives here, but
  semantics ("a question has a Bloom level") belong upstream.

### 3.5 Models (`app/models/`) — supporting, not a layer

Pydantic request/response models. Imported by routes (for validation) and
sometimes by services (for typed inputs). Models contain **shape**, not
behavior — no methods that hit the DB or call AI.

---

## 4. The Golden Rules (enforce these in every PR review)

These are non-negotiable. If a change violates one of these rules, the right
fix is to restructure the change, not to make an exception.

1. **Routes only handle HTTP.** A route function's body is: validate input,
   call one service, catch domain errors and map to HTTP status, return.
   No SQL, no `requests.post`, no business math.

2. **Business logic lives in services.** If the code makes a decision based
   on a rule ("foundational distribution puts 40% on REMEMBER"), that rule
   is in a service or a pure helper called by a service — never in a route,
   never in a repository.

3. **DB access only in repositories.** The string `"SELECT "` or `"INSERT "`
   appears in exactly one layer: `app/repositories/`. Routes and services
   that need data ask a repository.

4. **No layer skipping.** Routes call services. Services call repositories.
   Repositories call the database layer. A route may not call a repository
   directly. A service may not open a SQLite connection directly. There is
   no shortcut, even for "just one quick query."

5. **Dependencies point down.** Lower layers do not import upper layers.
   `app/repositories/questions_repository.py` may not import anything from
   `app/services/` or `app/api/`. If you feel the urge to do this, you
   have a design problem, not an import problem.

6. **One service call per route.** A route should not orchestrate two
   services. If two services need to cooperate, that orchestration is
   itself a service — give it a name and put it in `app/services/`.

7. **CLI scripts obey the same rules.** `import_syllabus.py` (and any
   future scripts) call services, not raw SQL. The CLI is just another
   transport layer, like HTTP — it sits above services.

---

## 5. Migration map — today's files → tomorrow's layout

| Today | Tomorrow | Notes |
|---|---|---|
| `main.py` (app + routes + SQL) | `app/main.py` (app object only) + `app/api/{questions,papers,syllabus,school_settings}.py` | Routes split by resource. `app/main.py` mounts routers and runs `init_db()`. |
| Pydantic classes inside `main.py` | `app/models/requests.py`, `app/models/responses.py` | Shared between routes and services. |
| `bloom_engine.py` | `app/services/bloom_service.py` | Already pure — moves wholesale. |
| `ai_generator.py` | `app/services/ai_service.py` | Already isolated — moves wholesale. Provider switching stays inside. |
| Inline SQL in `main.py` | `app/repositories/{questions,papers,syllabus,settings}_repository.py` | One repo per table. Each method returns `dict` or `list[dict]`. |
| `database.py` | `app/core/database.py` | Connection factory + schema bootstrap + idempotent migrations in one module (split into separate files when migrations grow non-trivial). |
| `import_syllabus.py` | `scripts/import_syllabus.py` + reuses `app/services/syllabus_service.py` | CLI calls a service; the service calls the repository. No raw SQL in the script. |

---

## 6. Worked example — `/api/generate-questions` after the refactor

**Route** (`app/api/questions.py`) — HTTP only:

```python
@router.post("/api/generate-questions")
def generate_questions(req: GenerateRequest):
    try:
        result = question_service.generate_for_topic(req)
    except SyllabusTopicNotFound:
        raise HTTPException(404, "syllabus_topic_id nahi mila.")
    except AIGenerationFailed as e:
        raise HTTPException(502, f"AI generation fail hui: {e}")
    return result
```

**Service** (`app/services/question_service.py`) — orchestration + rules:

```python
def generate_for_topic(req: GenerateRequest) -> dict:
    if req.syllabus_topic_id:
        topic = syllabus_repository.find_by_id(req.syllabus_topic_id)
        if not topic:
            raise SyllabusTopicNotFound()
        req = _enrich_from_syllabus(req, topic)

    distribution = bloom_service.calculate_distribution(
        req.bloom_distribution, req.total_questions
    )
    ai_questions = ai_service.generate(req, distribution)

    saved_ids = []
    for q in ai_questions:
        q["marks"] = bloom_service.calculate_marks(...)
        saved_ids.append(questions_repository.insert(q, req))
    return {"saved_count": len(saved_ids), "question_ids": saved_ids}
```

**Repository** (`app/repositories/questions_repository.py`) — SQL only:

```python
def insert(question: dict, ctx: GenerateRequest) -> str:
    qid = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO questions (id, subject, topic, ...) VALUES (?, ?, ?, ...)",
            (qid, ctx.subject, ctx.topic, ...),
        )
    return qid
```

Notice:
- The route has no SQL and no business math.
- The service has no `HTTPException` and no `SELECT`.
- The repository has no Bloom logic and no AI calls.
- The 502 mapping lives in the route, where HTTP semantics belong.

---

## 7. Anti-patterns to reject

If a PR contains any of these, send it back:

- A route handler that imports `database` or `sqlite3`.
- A service that imports `fastapi` or raises `HTTPException`.
- A repository method whose name contains a business verb (`pick_balanced_*`,
  `generate_*`). Repositories *fetch* and *store*; they do not decide.
- A repository that calls another repository, or a service.
- A "utility" module that is really a kitchen sink for code that didn't fit
  the layering. If it doesn't fit, the layering is wrong or the code is in
  the wrong place — fix the real problem.
- A CLI script that opens its own SQLite connection. CLIs call services.

---

## 8. What is explicitly out of scope for this doc

- Authentication / authorization — not in Phase 1, will get its own section
  when added.
- Background jobs / async — not needed yet; AI calls are synchronous.
- Multi-tenant data isolation — single-school MVP for now.
- Caching / rate-limiting — premature; revisit when usage warrants.

When any of these land, extend this doc; do not bend the layering to fit
them in.
