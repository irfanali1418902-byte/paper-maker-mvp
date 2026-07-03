# SRS — Software Requirements Specification
**System:** AII Smart Paper Maker · **Version:** 1.0 · **Date:** July 2026

---

## 1. System Overview

Layered FastAPI application:

```
static/ (HTML/JS UI, apiClient.js key-gate)
   ↓ X-API-Key
app/api/        → routes (papers, questions, dashboard, export, syllabus, settings, stats, auth)
app/services/   → business logic (paper, bloom, ai, export, adaptive, item-analysis, result…)
app/repositories/ → SQLite access (questions, papers, results, syllabus, settings, usage_log)
app/core/       → database init
app/schemas/    → pydantic request/response models
```

Rule: env reads at module boundary; API keys never in URLs; secrets never logged.

## 2. Functional Requirements (key)

**FR-1 Generation:** POST `/api/generate-questions` accepts subject, topic, count, difficulty, bloom distribution, `question_types[]` (multiple-choice, short-answer, essay, true-false, fill-blank); returns bilingual questions with Bloom tags; provider = Gemini (default) or Anthropic (if key set).
**FR-2 Bank:** questions persisted with usage_count; selection = least-used first per (subject, bloom, difficulty, type-group).
**FR-3 Assembly:** POST `/api/generate-paper` with `paper_type ∈ {mixed, mcq, subjective, custom-ratio}`; when custom-ratio, `mcq_percent ∈ [0,100]`; split = half-up rounding, `subjective = total − mcq` (no drift); per-group Bloom distribution reuses `calculate_bloom_distribution`.
**FR-4 Guards:** empty/insufficient bank per group → 404 with group-named message (`QuestionBankEmpty`); invalid percent → 400/422. Never crash.
**FR-5 Replace:** swap one question on a paper preserving position; totals recomputed; usage bumped; ValueError on unknown question.
**FR-6 Export:** Word (python-docx) and PDF (LibreOffice soffice, path auto-discovered or `SOFFICE_PATH`); print.html view.
**FR-7 Results & analysis:** CSV upload → per-question P-value, D-index, bad-question flags; dashboard summaries.
**FR-8 Adaptive:** build paper targeting weakest Bloom levels from class results.
**FR-9 Auth:** if `PAPER_MAKER_API_KEY` set → all `/api/*` require matching `X-API-Key` (401 otherwise); static mount `/` always open; frontend stores key (localStorage) and gates on 401.
**FR-10 CORS:** origins from `PAPER_MAKER_ALLOWED_ORIGINS` (comma list); no wildcard default.
**FR-11 i18n:** every UI label EN + Urdu; RTL layout in Urdu mode.

## 3. Non-Functional Requirements

| NFR | Requirement | Current status |
|-----|-------------|----------------|
| Security | Keys via env only; timing-safe compare; no secrets in logs/URLs | ✅ implemented |
| Reliability | Graceful degradation: auth off when key unset (dev); type-aware 404s | ✅ implemented |
| Performance | Paper build < 2s on small bank; AI generation bounded by provider | ✅ adequate |
| Portability | Runs on Windows (dev) and Linux (Railway); SQLite file on volume | ✅; migration doc pending |
| Maintainability | Layering rule enforced; pre-commit ruff+black; 242 tests | ✅ |
| Usability | Bilingual, preset-first UI; guard messages human-readable | ✅ |
| Cost | Free-tier AI; hosting ≤ $5/mo or free tier | ⚠️ hosting decision pending |

## 4. Data Model (core tables)

- **questions**(id, subject, topic, bloom_level, difficulty, question_type, marks, question_en/ur, options_en/ur, correct_answer_en/ur, explanation_en/ur, visual_emoji, visual_count, usage_count)
- **papers**(id, subject, question_ids JSON, total_marks, created_at, …)
- **results**(paper_id, question_id, student, correct/score, …) → item analysis
- **syllabus**(class/grade, topics …), **settings**(school branding), **usage_log**(AI calls)

## 5. External Interfaces

- **Gemini API** — `x-goog-api-key` header; model `gemini-2.5-flash`; errors sanitized via `AIGenerationFailed`.
- **Anthropic API** — optional, priority if key present.
- **LibreOffice** — local binary for docx→pdf.

## 6. Environment Variables (contract)

| Var | Required | Effect |
|-----|----------|--------|
| `GEMINI_API_KEY` | for AI generation | provider auth |
| `ANTHROPIC_API_KEY` | optional | preferred provider if set |
| `PAPER_MAKER_API_KEY` | prod | enables API auth |
| `PAPER_MAKER_ALLOWED_ORIGINS` | prod | CORS allowlist |
| `DB_PATH` | prod | SQLite location (Railway volume) |
| `SOFFICE_PATH` | optional | LibreOffice override |

## 7. Error Handling Conventions

- 400 = invalid input (ValueError), 401 = bad/missing API key, 404 = resource/bank-group empty (named message), 422 = schema validation.
- AI provider failures surface as friendly retry message; keys never echoed.

## 8. Traceability

Each FR maps to test files: FR-3/4/5 → `test_paper_service.py`, `test_api_routes.py`; FR-1 → `test_ai_service.py`; FR-7 → `test_item_analysis_service.py`, `test_result_service.py`; FR-6 → `test_export_service.py`; FR-9/10 → route auth tests. Total: **242 passing**.
