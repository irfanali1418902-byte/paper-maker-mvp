# CLAUDE CODE — MASTER PROMPTS (copy-paste ready)

In prompts ko Claude Code terminal mein order se use karo. Har prompt ek session/kaam hai.
(Pehle `/clear` karna behtar hai — naya kaam, fresh context.)

---

## PROMPT 1 — Full Verification Audit (pehla kaam — sirf report, koi change nahi)

```
Poore project ka ek professional QA audit karo — koi code change NAHI, sirf report:

1. Full pytest chalao + ruff + black. Numbers report karo.
2. Har API route ko live curl se verify karo (local server, auth off): happy path + ek guard case per route. Table banao: route | test | result.
3. Export verify karo: ek mixed paper banao, Word export karo, file kholke check karo ke usme English + Urdu text, sections/marks sahi hain. PDF conversion bhi (agar LibreOffice available).
4. CSV results round-trip: template download → sample fill → upload → item analysis numbers sahi aate hain?
5. Frontend: static/index.html, apiClient.js, print.html ko padh kar list banao — koi dead code, TODO, ya i18n missing labels?
6. Security scan: git history mein koi secret? .env.txt file ka content kya hai (mujhe sirf batao key hai ya nahi, value print MAT karo)? Koi endpoint jo auth bypass karta ho?
7. Aakhir mein ek scorecard do: area | status | issue | severity (P0/P1/P2).

Sirf audit — koi fix abhi mat karo. Report ke baad main batataoonga kya karna hai.
```

## PROMPT 2 — P0 Repo Hygiene (ek branch, ek PR)

```
Branch chore/repo-hygiene banao aur ye P0 cleanup karo (ROADMAP.md section B ke mutabiq):

1. .env.txt — pehle batao usme kya hai (value print mat karo, sirf "key hai/nahi"), phir delete karo.
2. maker.zip root se delete karo (untracked backup hai).
3. import_syllabus.py aur seed_large_class.py ko scripts/ folder mein le jao; har ek ke upar 2-line docstring; koi imports/paths tootein to theek karo.
4. Chaaron fixture CSVs ko tests/fixtures/ mein le jao; syllabus_topics_unit1_sample.csv.csv ka double extension theek karo; jo code inhe use karta hai uske paths update karo.
5. API_VERSIONING.md ko ek chhote paragraph tak trim karo; ek DECISIONS.md banao jisme ab tak ke bade faisle 5-6 bullet mein hon (auth single-key, ratio half-up, SQLite choice, etc.).
6. docs/ folder banao aur ye package files usme rakho: BRD.md, PRD.md, SRS.md, TEST-PLAN.md, SDLC-WORKFLOW.md, ROADMAP.md (main tumhe files dunga / repo root par rakhi hain).
7. Full pytest + ruff + black — sab green ho.
8. Single logical commits mein karo, phir push, aur mujhe PR link do. Merge main khud karunga.
```

## PROMPT 3 — Test Gaps (TEST-PLAN T1, T2, T4)

```
Branch test/coverage-gaps banao. TEST-PLAN.md ke ye gaps close karo:
1. T1: Word export content assertions — ek built paper ke docx mein English question text, Urdu text, total marks assert karo (python-docx se padh kar).
2. T2: Results CSV round-trip — template banao → programmatically fill → upload endpoint → item-analysis values assert.
3. T4: Provider fallback — HTTP mock se Gemini fail karwao, assert Anthropic try hota hai (jab dono keys set hon) aur friendly error jab dono fail.
Full suite green + lint clean. Phir push aur PR link do.
```

## PROMPT 4 — Adaptive × Paper-Type Decision (pehle design, phir code)

```
Adaptive paper generation abhi paper_type/ratio ko ignore karti hai. Pehle mujhe 2-3 options do (respect paper_type? default mixed? ratio allow?) with pros/cons — koi code nahi. Mere faisle ke baad implement karenge.
```

## PROMPT 5 — Migration Dry-Run (Railway → Render) — deadline se pehle

```
MIGRATION.md likho (koi deploy abhi nahi): Render.com free tier par is app ko deploy karne ke exact steps — GitHub connect, start command, env vars (PAPER_MAKER_API_KEY, PAPER_MAKER_ALLOWED_ORIGINS, GEMINI_API_KEY, DB_PATH), SQLite file Railway volume se Render disk par le jaane ka tareeqa (DB_UPLOAD_TOKEN route ya manual), aur post-migration smoke checklist. Risks bhi likho (cold starts, disk persistence).
```

---

### Tarteeb (order):
1 (audit report) → 2 (hygiene) → 3 (tests) → 4 (design decision) → 5 (migration doc) → phir ROADMAP section C features (Sections mode se shuru).
