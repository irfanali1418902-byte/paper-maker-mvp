# 🏢 START HERE — Software House Package Guide
**Irfan ke liye — Roman Urdu mein**

Yeh package tumhare project ko ek professional software house ki tarah chalane ke liye hai. Maine tumhare **latest code ka poora audit** kiya (242 tests pass, teeno naye features shamil) aur uske results in documents mein daale hain.

---

## 📦 Package mein kya hai (7 files)

| File | Kya hai | Kab kholna |
|------|---------|------------|
| **START-HERE.md** | Yeh file — guide | Abhi |
| **BRD.md** | Business goals — app KYUN hai, kis ke liye | Ek baar padho |
| **PRD.md** | Product features — kya bana hai, kya banna hai (priority ke saath) | Har naye feature se pehle |
| **SRS.md** | Technical specification — system kaise kaam karta hai (API, data, env vars) | Reference ke liye |
| **TEST-PLAN.md** | Testing ki poori tasveer — kya covered, kya gaps, deploy checklist | Har deploy se pehle |
| **SDLC-WORKFLOW.md** | Software house ka process — idea se release tak ke rules | Yaad kar lo — yeh tumhara rulebook hai |
| **ROADMAP.md** | ⭐ Audit findings + agle kaam priority order mein | Har session ke shuru/aakhir mein |
| **CLAUDE-CODE-PROMPTS.md** | ⭐ Ready-made prompts — copy karke Claude Code mein paste karo | Har session |

**Sabse zaroori do: ROADMAP.md aur CLAUDE-CODE-PROMPTS.md** — yeh tumhare rozana kaam ki files hain.

---

## 🔍 Audit ka khulasa (mukhtasar)

**Achha kya hai:** 242 tests pass · git mein koi secret nahi · architecture saaf (layers ka rule follow hua) · pichle 3 releases ka process bilkul professional tha · docs maujood hain.

**Theek karna kya hai (P0 — pehle):**
- `.env.txt` file disk par hai (purani key ho sakti hai) → delete
- `maker.zip` (1.4 MB) root mein → delete
- 2 loose scripts + 4 CSVs root mein bikhri hain → `scripts/` aur `tests/fixtures/` mein
- GitHub par master "protected" nahi → protection lagao
- `API_VERSIONING.md` lamba hai → trim + chhota `DECISIONS.md`

**Product kaam (P1):** prod mein subjective questions seed karo · export ke content tests · adaptive×ratio ka faisla · provider fallback test.

**Ops (P2, deadline wala):** Railway ~28 din — Render.com migration ka plan (MIGRATION.md) pehle se likhwa lo.

**Features (baad mein, order se):** Sections mode (A/B/C) → Ratio Phase 2 → Prod seeding tool → **Lesson Plan module** → per-student adaptive → syllabus PDF extract.

---

## 🪜 Ab kya karna hai — step by step

1. **In 7 files ko apne project mein `docs/` folder mein rakho** (E:\...\paper-maker-mvp\docs\)
2. Claude Code mein `/clear` karo (fresh session)
3. **CLAUDE-CODE-PROMPTS.md kholo → PROMPT 1** copy karke paste karo (full verification audit — koi change nahi, sirf report)
4. Report aaye to mujhe (chat wale Claude ko) screenshot dikhao — main review karunga
5. Phir **PROMPT 2** (hygiene cleanup) → PR → merge
6. Phir 3 → 4 → 5, aur uske baad features

**Rule yaad rakho (SDLC-WORKFLOW se):** har kaam branch par · plan pehle, code baad · tests green + browser check · PR → merge · prod smoke test · docs update. Yehi software house ka tareeqa hai — aur tum pichle 3 features mein yeh kar bhi chuke ho! 👏

---

## 🔐 Standing security rules

- Koi key kabhi chat/screenshot/commit mein nahi
- Jo key screenshot mein aa jaye = leaked = rotate karo
- Gemini key rotation abhi pending hai (aistudio nahi khul raha tha) — jab site khule, kar lena

Allah kaamyabi de. Ab tumhara project sirf ek app nahi — ek professionally-run product hai. 🚀
