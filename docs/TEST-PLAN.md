# TEST PLAN — AII Smart Paper Maker
**Version:** 1.0 · **Date:** July 2026 · **Current suite:** 242 passing (pytest), ruff + black clean

---

## 1. Test Levels & Current Coverage

| Level | What | Status |
|-------|------|--------|
| Unit — services | bloom, paper (split/assembly/replace), ai (prompt/provider/sanitize), export, adaptive, item-analysis, result, syllabus | ✅ Strong |
| Unit — repositories | questions, papers, results, settings, syllabus, usage_log | ✅ Strong |
| Route/API | happy paths, auth 401s, guards (404 group-named), validation (400/422), ratio splits | ✅ Strong |
| Live smoke (manual/CLI) | curl on prod: auth, health, ratio, markers in HTML | ✅ Done at each deploy |
| Browser E2E (manual) | key-gate, generate flow, ratio UI, subjective paper, print view | ✅ Done manually |
| Browser E2E (automated) | — | ❌ Not present |
| Load/perf | — | ❌ Not needed at current scale |

## 2. Known Coverage Gaps (prioritized)

1. **Export content assertions:** verify a built Word/PDF actually contains section text, Urdu strings, and correct total marks (currently existence/format checked more than content).
2. **Urdu/RTL rendering regression:** no automated check that Urdu text appears in print.html/export output for each question type.
3. **Frontend JS logic:** `apiClient.js` gate + `buildPaper()` payload verified by node-sim once; no repeatable JS test harness.
4. **CSV round-trip:** results template download → fill → upload → analysis end-to-end as one test.
5. **Adaptive + ratio interaction:** adaptive papers currently ignore paper_type/ratio — define expected behavior and test it.
6. **Provider fallback:** Gemini fail → Anthropic path (when both keys set) untested.

## 3. Manual Regression Checklist (run before every deploy)

```
[ ] pytest -q → all green;  ruff + black clean
[ ] Local: generate MCQ-only, Subjective, Mixed, Custom-ratio 30/70 — each builds
[ ] Local: replace a question — totals update
[ ] Local: Word + PDF export open correctly (Urdu visible)
[ ] Prod after deploy: / → 200; /api/stats no key → 401; with key → 200
[ ] Prod: key-gate appears, correct key unlocks, data loads
[ ] Prod: one AI generation succeeds (watch for 400/403 = key issue)
[ ] EN/اردو toggle: new labels translated, RTL intact
```

## 4. Test Data Strategy

- Unit/route tests: temp SQLite per test (`test_db` fixture) + `make_question` factory — no shared state.
- Local dev DB: throwaway; may be reseeded freely (`seed_large_class.py` → move to `scripts/`).
- **Production DB is separate (Railway volume):** never assume local data exists there; seed subjective questions in prod before demoing subjective/ratio flows.

## 5. Defect Workflow

1. Reproduce with a failing test first (unit if possible, else route).
2. Fix on a feature branch; keep the failing test as regression guard.
3. PR → merge → deploy → tick the manual checklist.

## 6. Next Test Work (recommended order)

| # | Task | Effort |
|---|------|--------|
| T1 | Export content assertions (docx text contains EN+UR + marks) | S |
| T2 | CSV results round-trip test | S |
| T3 | Decide + test adaptive×ratio behavior | M |
| T4 | Provider-fallback test with mocked HTTP | S |
| T5 | Minimal Playwright smoke (login-gate → build mixed paper) — optional, later | M |
