# ROADMAP & AUDIT FINDINGS — July 2026
**Basis:** fresh audit of repo @ commit f6bed81 (ratio merge) · 242 tests passing · prod live & verified

---

## A. Audit Snapshot — What's HEALTHY ✅

- **Tests:** 242 passing; services, repositories, and routes all covered; guard paths tested.
- **Security:** git history clean of secrets (`.env*`, `*.db`, `*.zip` ignored); auth fail-closed in prod; timing-safe key compare; Gemini key in header not URL; app key already rotated once successfully.
- **Architecture:** clean layering (api → services → repositories → core) consistently followed; env reads at module boundary.
- **Process:** last three releases followed branch → plan-first → verify → PR → deploy — keep this.
- **Docs:** README, ARCHITECTURE, PROJECT, USER_STORIES exist and are substantial.

## B. Audit Findings — What NEEDS FIXING ⚠️ (with priority)

### P0 — Hygiene & risk (do first, ~1 short session)
| # | Finding | Action |
|---|---------|--------|
| H1 | `.env.txt` (318 B) on disk — likely an old key copy. Untracked, but a leak-in-waiting. | Check contents → delete file. If it held a real Gemini key, rotate that key when aistudio access works. |
| H2 | `maker.zip` (1.4 MB) in repo root on disk | Delete (backups don't live in the working tree). |
| H3 | Loose root scripts: `import_syllabus.py`, `seed_large_class.py` | Move to `scripts/` + one-line README each. |
| H4 | Fixture CSVs in root (4 files, one named `…csv.csv`) and git-tracked | Move to `tests/fixtures/` (or `data/`), fix double extension, update any paths. |
| H5 | `master` not protected on GitHub | Enable branch protection: require PR, forbid direct push. |
| H6 | `API_VERSIONING.md` (8 KB) — over-long for current stage | Trim to one paragraph; add small `DECISIONS.md` for future ADRs. |

### P1 — Product robustness (next 1–2 sessions)
| # | Finding | Action |
|---|---------|--------|
| R1 | Prod question bank thin on subjective types | Seed prod: generate short-answer/essay sets per class/subject (guided script or checklist). |
| ~~R2~~ ✅ | ~~Export tests don't assert content (Urdu text, marks, sections)~~ | **DONE (PR #6):** docx content assertions for EN/UR question text, options, total-marks value. Sections deferred — feature not built yet. |
| ~~R3~~ ✅ | ~~Adaptive papers ignore paper_type/ratio — undefined interaction~~ | **DONE (PR #8):** adaptive now honors `paper_type` (mcq/mixed/subjective) via the shared `_PAPER_TYPE_FILTERS`; `custom-ratio` deliberately rejected for adaptive (422 via `_reject_ratio_for_adaptive` validator) — weakness-distribution × ratio-split combo left out of scope. Tested: type filter + custom-ratio rejection. |
| ~~R4~~ ✅ | ~~Provider fallback (Gemini→Anthropic) untested~~ | **DONE (PR #6):** locked actual behavior — selection-by-priority (no runtime fallback exists); mocked-HTTP error-wrapping + no-key-leak tests. |

### P2 — Ops decision (before Railway day ~28)
| # | Finding | Action |
|---|---------|--------|
| O1 | Railway credit expires; card not added (correct) | Pick target (Render free tier suggested) → write MIGRATION.md → dry-run: deploy from GitHub, copy volume DB, set 4 env vars, smoke test → switch. |

## C. Feature Roadmap (after P0/P1)

| Order | Feature | Why | Size |
|-------|---------|-----|------|
| 1 | **Sections mode (A/B/C)** — headings + per-section marks in UI/print/Word | Matches real Pakistani exam format; biggest teacher-visible win | M–L |
| 2 | **Ratio Phase 2** — exact counts per type (3/4/3) | Finer control; builds on ratio v1 | S–M |
| 3 | **Prod seeding tool** — one-click "build starter bank" per class | Removes empty-bank friction for new subjects | S |
| 4 | **Lesson Plan module** — plans linked to topics + coverage report | Your original vision; new module, do after core is polished | L |
| 5 | Per-student adaptive papers | Extends F10; still open after R3 (adaptive is whole-class only) | M |
| 6 | Syllabus PDF auto-extract | Convenience | M |
| 7 | Adaptive × custom-ratio | Deferred by R3 (currently 422-rejected); needs a weakness-distribution × ratio-split design before it's safe to allow | M |

## D. Suggested Session Plan (step-by-step)

```
Session 1  → P0 cleanup (H1–H6) — one branch chore/repo-hygiene, one PR
Session 2  → R2 + R4 tests; decide & implement R3 (adaptive×type)
Session 3  → R1 prod seeding + full prod regression checklist
Session 4  → O1 migration dry-run (MIGRATION.md) — before credit deadline
Session 5+ → Feature roadmap order 1 (Sections mode): plan-first → build
```

## E. Standing Reminders

- Gemini key rotation still pending (aistudio access issue) — retry occasionally.
- Any future key that appears in chat/screenshot = rotate.
- Update this file at the end of every session (it is the living plan).
