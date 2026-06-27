# Project conventions — paper-maker-mvp

This file is read automatically by Claude Code when working in this repo. It
defines coding conventions that sit on top of `ARCHITECTURE.md` (which
defines the layering). If anything here ever conflicts with
`ARCHITECTURE.md`, the architecture doc wins — fix this file.

The rules below are not stylistic preferences. Each one exists because we
have either hit the bug it prevents, or are about to.

For project status, completed phases, the API endpoint list, and build
commands, see @PROJECT.md.

---

## 1. Naming

### Files

- snake_case, always. Layer is encoded in the suffix so it's grep-able:
  `questions_repository.py`, `bloom_service.py`, `ai_service.py`,
  `questions.py` (under `routes/`).
- One module per resource or use-case. Don't create `utils.py`,
  `helpers.py`, or `common.py` — those become landfills. If something is
  genuinely shared and stateless, name it for what it does
  (`marks_calculator.py`), not for where you couldn't think to put it.

### Functions and methods

- **Routes:** verb matches the HTTP action — `generate_questions`,
  `list_syllabus_topics`, `get_paper`. Don't prefix with `handle_` or
  `endpoint_`; the decorator already says it's an endpoint.
- **Services:** business-verb methods — `generate_for_topic`,
  `assemble_balanced_paper`, `import_from_csv`. Avoid generic names like
  `process`, `handle`, `do`, `run`. If the verb is generic, the method is
  doing too much.
- **Repositories:** CRUD verbs only — `insert`, `find_by_id`,
  `find_by_subject`, `list_all`, `update_usage_count`, `delete_by_id`. A
  repository method whose name contains a business concept
  (`pick_balanced_questions`, `generate_paper`) is misplaced; that logic
  belongs in a service.

### Classes

- **Pydantic request models:** `*Request` suffix — `GenerateRequest`,
  `PaperRequest`.
- **Pydantic response models:** `*Response` suffix.
- **Domain exceptions:** noun-shaped, descriptive —
  `SyllabusTopicNotFound`, `AIGenerationFailed`, `QuestionBankEmpty`. Never
  `AppError`, `GeneralError`, or other catch-all names.

### Constants

- `UPPER_SNAKE_CASE` at module top.
- Bloom levels are always the canonical upper-case strings:
  `REMEMBER`, `UNDERSTAND`, `APPLY`, `ANALYZE`, `EVALUATE`, `CREATE`.
  Don't introduce lowercase or mixed-case variants — DB rows, prompts, and
  distribution dicts all key off this exact form.

### URLs

- All HTTP routes live under `/api/...` — never serve API JSON from `/`.
  (The `/` mount is for the static frontend.)
- Kebab-case in paths: `/api/generate-questions`, `/api/school-settings`.

---

## 2. Error handling — the canonical pattern

The bug we fixed earlier (`Unexpected token Internal S... is not valid
JSON`) happened because an uncaught exception in a route handler returned
Starlette's plain-text `Internal Server Error` body, which the frontend
then tried to parse as JSON. That class of bug must not recur.

### The rule

Every route handler must produce a JSON response on **every** code path —
success, validation failure, expected domain failure, and unexpected
failure. We achieve this with two layers of discipline:

1. **Services raise domain exceptions**, not `HTTPException`.
2. **Routes wrap every external-boundary call** (DB, AI provider, file IO)
   in `try`/`except`, translate the error to an `HTTPException` with the
   right status code, and put a short, user-facing detail string in it.

### The canonical example (matches what we did to `generate_questions`)

```python
# Route — app/routes/questions.py
@router.post("/api/generate-questions")
def generate_questions(req: GenerateRequest):
    try:
        ai_questions = ai_service.generate(req)
    except AIGenerationFailed as e:
        raise HTTPException(status_code=502, detail=f"AI generation fail hui: {e}")

    try:
        saved = questions_service.persist_batch(ai_questions, req)
    except RepositoryError as e:
        raise HTTPException(status_code=500, detail=f"Question save fail hui (DB error): {e}")

    return {"saved_count": len(saved), "question_ids": saved}
```

Note four things:

- **Two separate `try` blocks**, not one mega-try. Each block catches a
  specific failure mode and maps it to a specific status code. A single
  blanket try around the whole handler hides which step failed.
- **502 for upstream AI failure, 500 for our own DB failure.** Status code
  encodes whose fault it is.
- **Detail string is short, actionable, Hinglish-OK.** The frontend
  surfaces it directly to the user (Swat school teachers), so write it the
  way you would write a UI string, not the way you would write a stack
  trace.
- **No bare `except:`.** Always name the exception class. If you genuinely
  don't know what could go wrong, the answer is "find out," not "catch
  Exception."

### Status code map

| Status | When |
|---|---|
| 400 | Request shape is valid but business validation fails ("subject aur topic dono zaroori hain"). |
| 404 | A referenced resource doesn't exist (`syllabus_topic_id nahi mila`). |
| 422 | Pydantic-level validation failed — FastAPI does this for you, don't reinvent it. |
| 500 | Our code broke (DB error, our bug). |
| 502 | An upstream provider broke (Gemini, Claude API). |

### Domain exceptions

Defined in `app/services/exceptions.py` (single file, easy to import). One
class per failure mode that a route needs to distinguish:

```python
class SyllabusTopicNotFound(Exception): pass
class AIGenerationFailed(Exception): pass
class QuestionBankEmpty(Exception): pass
class RepositoryError(Exception): pass
```

Services raise these. Routes catch them. Repositories raise
`RepositoryError` (wrapping the original `sqlite3.OperationalError` etc.)
so callers don't have to know we use SQLite.

---

## 3. Pydantic models

### Location

- Request models: `app/models/requests.py`
- Response models: `app/models/responses.py`
- Shared domain models (rare): `app/models/domain.py`

Routes import from `requests`/`responses`. Services may import from
`requests` (to type their inputs). Repositories never import models —
they speak in plain `dict`.

### Version

Pydantic v2 only (`requirements.txt` pins `pydantic>=2.9`). Use
`model_dump()`, not the v1 `.dict()`. Use `Field(default=...)`, not
mutable default values.

### Style

- Defaults are visible in the model — that's what shows up in `/docs`:

  ```python
  class GenerateRequest(BaseModel):
      subject: str = ""
      total_questions: int = 10
      bloom_distribution: str = "balanced"
      question_types: List[str] = ["multiple-choice"]
      difficulty: str = "medium"
  ```

- `Optional[T]` only when `None` is a meaningful value (e.g.
  `syllabus_topic_id: Optional[str] = None` means "user didn't pick one").
  Don't use `Optional` as a lazy way to make a field non-required.

- **Models are shape, not behavior.** No methods that hit the DB, call AI,
  or compute Bloom distributions. If you find yourself adding a method,
  the logic belongs in a service.

---

## 4. What is not allowed

These are hard rules. If you find yourself wanting to violate one, the
right move is to restructure, not to make an exception.

- **`import sqlite3` or `from database import get_connection` in
  `app/routes/`.** Routes never touch the DB directly. Hitting this rule
  during a code change means you skipped the service layer.

- **SQL strings outside `app/repositories/`.** Grep for `SELECT `,
  `INSERT `, `UPDATE `, `DELETE ` — they must only match files under
  `app/repositories/` (and `app/database/schema.py` for DDL).

- **`from fastapi import ...` in `app/services/` or `app/repositories/`.**
  Lower layers don't know HTTP exists.

- **`HTTPException` raised from a service or repository.** Services raise
  domain exceptions; routes map them.

- **Layer skipping.** A route may not call a repository. A service may not
  call `get_connection()`. CLIs (under `scripts/`) call services, not raw
  SQL. (See `ARCHITECTURE.md` §4 rule 4.)

- **Bare `except:` or `except Exception:` in production code paths.** The
  only exception (no pun intended) is the import-syllabus row loop, where
  we deliberately skip duplicate rows and continue — and even there, the
  exception type should be narrowed once we know which one we're seeing.

- **`os.environ.get()` for API keys outside `app/services/ai_service.py`
  (or wherever the provider boundary is).** Secrets are read once, at the
  module that owns them. Don't sprinkle env reads across the codebase.

- **Committing `.env` or any `.env.*` file.** Already covered by
  `.gitignore`. If you need to share a key, share it out-of-band; if you
  need a sample, commit `.env.example` with placeholder values.

- **Mutable global state.** No module-level lists/dicts that handlers
  append to. Each request stands on its own.

---

## 5. Database and migrations

The other bug we fixed (`table questions has no column named
visual_emoji`) happened because `init_db()` used
`CREATE TABLE IF NOT EXISTS` only — which silently does nothing if the
table already exists from an older schema. The fix was an idempotent
`ALTER TABLE ... ADD COLUMN` check after the CREATE.

### The rule

Every schema change requires both:

1. The new column / table in the `CREATE TABLE IF NOT EXISTS` block (for
   fresh installs).
2. An idempotent migration step after the CREATE (for existing DBs):

   ```python
   existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(questions)").fetchall()}
   if "new_column" not in existing_cols:
       cur.execute("ALTER TABLE questions ADD COLUMN new_column TEXT")
   ```

Both lives in `app/database/schema.py`. The route, service, and
repository layers are unaware migrations exist — `init_db()` runs at
startup and the rest of the app assumes the schema is current.

### Connection lifecycle

- One connection per request (or per repository method, in the simple
  case). Open, use, close. No long-lived connections.
- Always `conn.commit()` before `conn.close()` on writes.
- If a write block can raise, use `try`/`except`/`finally` (or a context
  manager) so the connection still closes — a leaked connection on Windows
  locks the DB file.

---

## 6. AI provider conventions (`ai_service.py`)

- **`.env` + `load_dotenv()` always.** No hardcoded keys, ever. The
  `load_dotenv()` call must run before any `os.environ.get()` at module
  scope; if you move things around, preserve that order.
- **Prompt building is a separate function** from the HTTP call.
  `build_prompt(...)` returns a string; `_generate_with_gemini(prompt)`
  takes it. This lets us unit-test the prompt without hitting the network.
- **Both providers (Gemini, Claude) return the same shape** — a `list[dict]`
  with the agreed-on keys. The calling service must not need to know which
  provider answered.
- **Provider priority is fixed in code, not config**: Anthropic key wins
  over Gemini key. Don't add a third "balancer" or "router" until we have
  a real reason.
- **Truncated-JSON errors get a user-friendly message**, not the raw
  traceback. The existing `_extract_json` is the template — match its
  tone.

---

## 7. Comments and docstrings

- **Default to no comment.** Identifiers should carry the meaning.
- **WHY, not WHAT.** A comment that re-states the code is noise.
- **Hinglish narrative is allowed** — it's the project's voice and matches
  the existing comments. Identifiers stay English.
- **No multi-paragraph docstrings.** One short line, max. If a function
  needs more explanation than that, it's doing too much.
- **Never reference the current task or PR in code comments.** "Fix for
  the JSON parse bug" belongs in the commit message, not in
  `main.py`.

---

## 8. Imports

- Standard order: stdlib → third-party → local. One blank line between
  groups.
- No `from x import *`.
- No conditional imports inside functions to "avoid circular imports" —
  that's a layering smell. Fix the layering.

---

## 9. Testing and verification before claiming "done"

A change is not done when it compiles. A change is done when:

- For HTTP changes: you hit the endpoint with `curl` (or via the
  frontend) and confirmed both the happy-path JSON shape and at least one
  failure-path JSON shape. "It should work" doesn't count.
- For DB schema changes: you ran `init_db()` against the **existing**
  `paper_maker.db` (not a fresh one) and confirmed `PRAGMA table_info(...)`
  shows the new columns.
- For env / config changes: you actually restarted uvicorn and re-triggered
  the affected path. `--reload` doesn't always pick up module-level
  constants; when in doubt, hard-restart.
- For frontend changes: you opened the page in a browser and clicked the
  button. Type-checking is not the same as use-checking.

If you can't verify the change for some reason (e.g. no display
available), say so explicitly. Don't claim success on faith.

---

## 10. Git hygiene

- Commit messages: present-tense imperative, lowercase first letter, short
  subject — match the existing log style (`checkpoint: working MVP before
  architecture refactor`, `ignore .claude tooling dir`).
- One logical change per commit. A refactor and a bug fix in the same
  commit makes both impossible to review.
- Never commit secrets. `.gitignore` covers `.env` and `.env.*`; if you
  add a new secrets file, add its pattern to `.gitignore` in the same
  commit.
- Never use `--no-verify` to bypass hooks. If a hook fails, fix the
  failure.
