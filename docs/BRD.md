# BRD — Business Requirements Document
**Product:** AII Smart Paper Maker (Parcha) · **Version:** 1.0 · **Date:** July 2026
**Owner:** Irfan (Ameen Islamic Institute / Govt. High School Mingora)

---

## 1. Business Purpose

Pakistani school teachers spend hours every term manually writing exam papers, often reusing the same questions, with no visibility into question quality or class weaknesses. AII Smart Paper Maker automates bilingual (English + Urdu) exam paper creation so a teacher can produce a balanced, print-ready paper in minutes instead of hours.

## 2. Business Goals

| # | Goal | Success Measure |
|---|------|-----------------|
| G1 | Cut paper-creation time from hours to under 10 minutes | Teacher can generate + print a paper in one sitting |
| G2 | Improve paper quality (Bloom balance, difficulty mix) | Every paper shows a balance summary; item analysis flags bad questions |
| G3 | Support both objective and subjective assessment styles | MCQ / Subjective / Mixed / Custom-ratio papers all work |
| G4 | Serve Urdu-medium classrooms authentically | All questions render bilingually with correct RTL Nastaliq |
| G5 | Keep running cost near zero for a single school | Free-tier AI (Gemini) + low-cost hosting |

## 3. Stakeholders

| Stakeholder | Interest |
|-------------|----------|
| Teachers (primary users) | Fast, good papers; simple UI; Urdu support |
| School administration (Ameen Islamic Institute) | Consistent paper standards; institutional branding on exports |
| Students (indirect) | Fairer, better-balanced assessment |
| Owner/Developer (Irfan) | Low maintenance burden; low cost; portfolio value |

## 4. Scope

**In scope (current):** AI question generation (bilingual, Bloom-tagged, multi-type), question bank, balanced/typed/ratio paper assembly, manual question replace, Word/PDF export, results upload + item analysis (P-value, D-index), adaptive papers from class weaknesses, quick stats dashboard, API-key security.

**Out of scope (for now):** multi-school tenancy, per-teacher accounts, online student testing, payments, mobile app.

## 5. Constraints & Assumptions

- Single-deployment, single-school usage model (one shared API key).
- Hosting: Railway free credit expires ~28 days from July 2026 → migration to a free tier (e.g., Render) is a pending business decision.
- AI provider: Gemini free tier (rate limits apply); Anthropic key optional for higher quality.
- Data volume is small (hundreds of questions, dozens of papers) — SQLite is sufficient.

## 6. Business Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hosting credit runs out | App goes offline | Plan migration to free tier before day 28 |
| Gemini rate limits / policy change | Generation fails | Provider fallback already coded (Anthropic); retry messaging in UI |
| Single shared key leaks | Unauthorized use | Key rotation procedure (already exercised once) |
| Solo maintainer | Bus factor = 1 | Docs in repo (this package), disciplined git workflow |
