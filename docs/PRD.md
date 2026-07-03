# PRD — Product Requirements Document
**Product:** AII Smart Paper Maker (Parcha) · **Version:** 1.0 · **Date:** July 2026

---

## 1. Product Summary

A FastAPI + SQLite web app that lets a teacher generate bilingual (EN + Urdu), Bloom-taxonomy-tagged exam questions with AI, curate them in a question bank, assemble balanced papers (objective / subjective / mixed / custom ratio), export to Word/PDF, upload student results, and get item-analysis + adaptive re-testing of weak areas.

## 2. Users & Personas

- **P1 — Classroom Teacher (primary):** low technical skill, Urdu-first, wants a paper "ready to print" quickly.
- **P2 — Senior Teacher / Coordinator:** cares about paper standards, Bloom balance, and question quality over time.

## 3. Current Feature Set (shipped, production)

| ID | Feature | Status |
|----|---------|--------|
| F1 | AI bilingual question generation (Gemini/Claude), Bloom-tagged | ✅ Live |
| F2 | Question types at generation: MCQ, short-answer, essay (+true-false, fill-blank in schema) | ✅ Live |
| F3 | Question bank with least-used-first selection & usage counts | ✅ Live |
| F4 | Balanced paper assembly (Bloom distribution: balanced/foundational/etc.) | ✅ Live |
| F5 | Paper type filter: MCQ-only / Subjective / Mixed | ✅ Live |
| F6 | Custom MCQ-vs-Subjective ratio (presets 20/80…80/20 + custom %) | ✅ Live |
| F7 | Manual question replace on a built paper | ✅ Live |
| F8 | Word export + PDF via LibreOffice; print view | ✅ Live |
| F9 | Results CSV upload → item analysis (P-value, D-index, flags) | ✅ Live |
| F10 | Adaptive paper generation targeting weak Bloom levels | ✅ Live |
| F11 | Syllabus upload → topic dropdown | ✅ Live |
| F12 | Quick stats dashboard; EN/اردو full UI toggle | ✅ Live |
| F13 | API-key auth (X-API-Key) + CORS allowlist; key-entry gate in UI | ✅ Live |

## 4. Requirements for Next Releases (prioritized)

### P0 — Must do next (stability/ops)
- **R1. Hosting migration plan:** Render.com (or equal) free-tier deployment with DB file migration, before Railway credit ends.
- **R2. Repo hygiene:** move loose scripts (`import_syllabus.py`, `seed_large_class.py`) to `scripts/`; CSV fixtures to `tests/fixtures/` or `data/`; delete stale `.env.txt` and root `maker.zip` from disk; fix `syllabus_topics_unit1_sample.csv.csv` double extension.
- **R3. GitHub branch protection on `master`** (require PR, block direct push).

### P1 — High-value product work
- **R4. Sections mode:** paper rendered as Section A (MCQ) / B (Short) / C (Essay) with per-section headings and marks, in UI + Word/PDF export.
- **R5. Ratio Phase 2:** exact per-type counts (e.g., 3 MCQ / 4 short / 3 essay) as an alternative to percentage.
- **R6. Production data seeding:** guided flow (or script) to build a healthy production question bank across types/difficulties.

### P2 — New modules (later)
- **R7. Lesson Plan module:** create/store lesson plans linked to topics; report showing paper-vs-plan coverage.
- **R8. Per-student adaptive papers** (currently whole-class only).
- **R9. Syllabus PDF auto-extract** (topics from uploaded PDF).

## 5. Non-Goals (explicitly not now)
Multi-tenant accounts, student-facing portal, payments, mobile apps, LMS integration.

## 6. UX Principles
- Two-click happy path: preset buttons over free-form input wherever possible.
- Every label bilingual (EN + اردو), RTL-correct.
- Never crash on empty data: type-aware, human-readable guard messages (already the pattern).

## 7. Release Criteria (each feature)
1. Unit + route tests green (pytest), lint clean (ruff + black).
2. Live curl verification of new endpoints.
3. Browser click-test of new UI.
4. Feature branch → PR → merge; Railway/host auto-deploy verified.
5. Docs updated (this package + README if user-facing).
