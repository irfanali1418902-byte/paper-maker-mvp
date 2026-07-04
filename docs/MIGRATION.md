# MIGRATION PLAN — Railway → Northflank

**Status:** PLAN FINALIZED (decisions locked, §8) — no deploy/code change yet, awaiting
"implement karo".
**Reason:** Railway trial credit ~27 din mein khatam. Card add karke bhi paisa kharch
nahi karna. **Target = Northflank free (Sandbox)** — free limit mein charge zero.
**Author basis:** repo @ `master` (261 tests green) · prod live & verified on Railway.
**Pricing/limits verified:** Northflank docs + pricing, July 2026 (sources at bottom).

> Decisions review ho chuke (§8). Ab "implement karo" ka wait — phir branch → PR → deploy.

---

## 0. Kyun Northflank (aur ek honest caveat)

Requirement thi: **free + persistent SQLite (jo deploy/restart ke baad bache) + zero
code-rewrite.** Poori market research (Render / Fly.io / Koyeb / Northflank) ke baad:

- **Render free** — persistent disk nahi (SQLite har restart par wipe). ❌
- **Fly.io** — free tier hi khatam (trial + card). ❌
- **Koyeb free** — volumes paid; SQLite deploy par reset. ❌
- **Northflank Sandbox (free)** — ✅ **persistent volume + always-on (no cold start)**.
  **Yehi choose kiya.** (Migrate slim/fast; PDF export baad ke PR mein — §2a, gotcha #6.)

**⚠️ Card caveat (accepted):** Northflank ke free Sandbox ke liye bhi **payment method
(card) add karna mandatory hai** — official docs: *"all users must add a payment method
to start creating resources on Northflank, regardless of plan selection"* (identity
verify ke liye). **Free limit ke andar raho to charge ZERO.** Tumne ye trade-off accept
kiya (asal concern paisa tha, card daalna nahi) — is liye Northflank final.

### Northflank free (Sandbox) — verified limits
| | Free Sandbox |
|---|---|
| Compute | **Always-on, no sleep / no cold start** (Render free se behtar) |
| Services | 2 |
| Databases / addons | 1–2 DB, 1 addon, 2 cron jobs |
| RAM / CPU | ~1 GB RAM / ~1 vCPU (shared) |
| Persistent volume | **0.5 GB** (SQLite ke liye bahut zyada — ye DB abhi <50 MB) |
| Cost within free | **$0** (card required, no charge) |
| Beyond free | disk $0.30/GB/mo · egress $0.15/GB |
| Expiry | Koi expiry nahi (docs mein mention nahi) |

---

## 1. Railway par abhi kya hai (source-of-truth snapshot)

Migrate karne se pehle Railway dashboard par ye note/screenshot kar lo (values secret
hain — screen-share band):

### 1a. Build & runtime
- **Builder:** Nixpacks (`railway.toml`), `requirements.txt` se pip install.
- **Python:** 3.12 (`.python-version`).
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Healthcheck:** `/` (static frontend → 200).
- **Deploy trigger:** GitHub auto-deploy on push to `master`.

### 1b. Persistent volume + DB
- Railway volume mounted at (likely) **`/data`**, DB file **`/data/paper_maker.db`**
  (`DB_PATH` env se).
- ⚠️ **Exact mount path + `DB_PATH` value confirm karo** Railway dashboard se — poora
  migration isi file par depend karta hai.

### 1c. Environment variables (Railway → Variables)
| Var | Purpose | Notes |
|---|---|---|
| `PAPER_MAKER_API_KEY` | `/api/*` auth (fail-closed in prod) | long random string |
| `GEMINI_API_KEY` *(or `ANTHROPIC_API_KEY`)* | AI provider | Anthropic key priority > Gemini |
| `PAPER_MAKER_ALLOWED_ORIGINS` | CORS allowlist | comma list; naya Northflank URL add hoga |
| `DB_PATH` | SQLite location | e.g. `/data/paper_maker.db` |
| *(auto)* `RAILWAY_ENVIRONMENT` etc. | Railway-injected | **Northflank par nahi honge** — §5 gotcha #2 |

### 1d. Live data
- Prod `paper_maker.db` mein real questions/results/papers hain — **migrate zaroori**
  (fresh empty DB acceptable nahi).

---

## 2. Northflank par same setup kaisa banega (target architecture)

| Piece | Railway | Northflank (Sandbox, free) |
|---|---|---|
| Unit | Service | **Combined service** (build + deploy) in a **Project** |
| Deploy source | GitHub → master (auto) | GitHub repo → branch `master`, **auto-deploy on push** |
| Build | Nixpacks (auto) | **Slim Dockerfile** (no LibreOffice, migrate-first) — §2a |
| Python | 3.12 | Dockerfile base image `python:3.12-slim` |
| **Port** | `$PORT` injected | **⚠️ `$PORT` inject NAHI hota** — app fixed port (e.g. 8080) par listen kare + Northflank port config mein 8080 declare karo — §2b |
| Start command | `uvicorn ... --port $PORT` | `uvicorn app.main:app --host 0.0.0.0 --port 8080` (Dockerfile `CMD`) |
| Healthcheck | `/` | Health check path `/` (HTTP) |
| Persistent storage | Volume `/data` | **Volume** attached, container mount path **`/data`** |
| DB file | `/data/paper_maker.db` | **`/data/paper_maker.db`** (same `DB_PATH`) |
| Env vars | 4 | same 4 + `PAPER_MAKER_REQUIRE_API_KEY=1` (§5 #2) |

### 2a. Build: slim Dockerfile (migrate-first, no LibreOffice)
Northflank GitHub se Dockerfile ya buildpack se build karta hai. **Slim Dockerfile
chuna** (LibreOffice ke bina) kyunki: start command + port explicit aur reliable
(buildpack ko Procfile/entrypoint guess karna padta). Slim rakhne se image chhoti,
build fast — **jaldi migrate** ka goal (Railway credit khatam ho raha).

Approx `Dockerfile` (repo root) — chhota, standard:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- **PDF export is slim image mein band rahegi** (LibreOffice nahi) — **Word (.docx)
  export chalta rahega**, PDF par app clean `PdfConversionFailed` JSON deti hai (500
  HTML nahi). Ye **jaan-boojh kar deferred** — Northflank settle hone ke baad alag PR
  mein `apt-get install -y libreoffice-writer` add karke PDF wapas (gotcha #6).
- **Local Docker ki zaroorat nahi:** is machine par Docker/WSL installed nahi. Slim
  Python Dockerfile deterministic hai; **Northflank cloud mein build karega** aur hum
  build logs + deployed smoke checklist (§6) se verify karenge — real artifact, real
  env (CLAUDE.md §9 satisfy). *(Local build chahiye to Docker Desktop = WSL2 + reboot,
  fast-migrate ke against — skip.)*

### 2b. Port — sabse zaroori difference
Railway `$PORT` inject karta tha; **Northflank nahi karta.** App ko ek **fixed port**
par listen karna hoga aur wahi port Northflank UI mein declare karna hoga:
- Dockerfile: `EXPOSE 8080` + `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]`
- Northflank → service → Ports: `8080`, HTTP, publicly exposed (Northflank isse 80/443
  par expose karke HTTPS deta hai).
- **`railway.toml` ka `--port $PORT` yahan use NAHI hoga** — Dockerfile `CMD` isko
  supersede karta hai. (`railway.toml` repo mein reh sakta hai, Northflank use nahi karta.)

### 2c. Config-as-code (optional)
Northflank templates (JSON/YAML) + GitHub Actions IaC support karta hai. Chaho to ek
Northflank **template** commit kar sakte ho (`railway.toml` ke barabar). MVP ke liye
optional — pehle UI se set karo, template baad mein.

---

## 3. DB migration — Railway volume se Northflank volume (manual)

Koi built-in DB upload/download route nahi hai → **manual copy** (one-time).

### 3a. Railway se DB safe-copy (download)
Live writes ke beech raw copy corrupt kar sakti hai — hamesha SQLite `.backup` lo:
```bash
railway run "sqlite3 /data/paper_maker.db '.backup /data/backup.db'"
# phir /data/backup.db download karo (Railway shell/CLI / volume browser se)
```
Local par verify:
```bash
sqlite3 backup.db "PRAGMA integrity_check;"   # 'ok' aana chahiye
```

### 3b. Northflank volume par DB daalo (upload)
Direct dashboard upload nahi hai, to Northflank container **shell** (exec) se pull karo:
1. Northflank service create karo (§4) with volume mounted at `/data`.
2. Pehli deploy par app khud fresh empty `paper_maker.db` bana degi (`init_db()` schema +
   migrations) — placeholder, ghabrana nahi.
3. Backup file ko ek **temporary private URL** par rakho (signed GDrive / transfer.sh),
   phir Northflank service → **Shell** kholo:
   ```bash
   cd /data
   curl -L "<temporary-signed-url-to-backup.db>" -o paper_maker.db
   sqlite3 paper_maker.db "PRAGMA integrity_check;"   # ok?
   ```
4. Service **restart** karo taake app naya DB uthaye.
5. ⚠️ Temporary URL turant revoke/delete karo (real data hai).

---

## 4. Step-by-step migration

Sab reversible — **Railway delete mat karo jab tak Northflank 100% verify na ho.**

1. **Backup lo (§3a).** Railway se safe `.backup` + integrity-check. Non-negotiable step 1.
2. **Slim Dockerfile add karo (PR).** Repo root par `Dockerfile` (§2a snippet):
   `python:3.12-slim`, `pip install -r requirements.txt`, `EXPOSE 8080`,
   `CMD uvicorn app.main:app --host 0.0.0.0 --port 8080`. **No LibreOffice** (PDF later).
   Local Docker nahi hai → Northflank cloud build + deployed smoke test se verify (§2a).
3. **Northflank account.** Sign up, **card add** (mandatory; free limit mein charge nahi),
   GitHub connect, `paper-maker-mvp` repo access.
4. **New Project → Combined Service.** GitHub repo, branch `master`, auto-deploy ON.
   - Build: **Dockerfile** (path `./Dockerfile`).
   - Port: **8080**, HTTP, publicly exposed.
   - Health check path: `/`.
5. **Persistent volume add karo.** Service → Volumes → Add:
   - Container mount path: `/data`
   - Size: 0.5 GB (free limit; SQLite ke liye kaafi zyada).
   - Note: volume attach karne par service **single replica** chalegi (SQLite ke liye
     yehi chahiye — single writer) aur deploy "recreate" hoga (chhoti downtime).
6. **Env vars set karo** (service → Environment / runtime variables):
   - `PAPER_MAKER_API_KEY` = **NAYI rotated key** (purani Railway retire — §5 #9).
   - `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` = same as prod.
   - `DB_PATH` = `/data/paper_maker.db`.
   - `PAPER_MAKER_ALLOWED_ORIGINS` = **naya Northflank URL** (transition ke doran purana
     Railway URL bhi comma-separated rakho).
   - `PAPER_MAKER_REQUIRE_API_KEY=1` — **§5 #2, zaroor** (Northflank par deploy-markers
     nahi hote; ye flag akela fail-closed auth ON karta hai).
7. **Pehli deploy chalne do.** Build logs (Docker build + pip install) clean,
   `init_db()` clean, uvicorn 8080 par bind, health check `/` → 200.
8. **DB restore karo (§3b).** Backup ko `/data/paper_maker.db` par, restart, integrity-check.
9. **Smoke test (§6).** Naye Northflank URL par pura checklist.
10. **URL switch.** Jahan Railway URL share tha (mobile app, teachers, bookmarks) → naya
    Northflank URL. Custom domain ho to Northflank par re-point.
11. **Railway abhi delete MAT karo.** ~1 hafta dono (Northflank primary). Confirm hone
    par Railway service band.

---

## 5. Risks / gotchas (ye asli traps hain)

1. **🔴 Card add karna mandatory.** Free Sandbox bhi bina payment method ke resources
   create nahi karne deta. **Free limit mein charge zero**, par card daalna hi padega.
   (Accepted trade-off — §0.) **Mitigation:** free limits (2 services / 0.5 GB volume)
   ke andar raho; billing alerts on karo taake galti se paid resource na ban jaye.

2. **🔴 Fail-closed auth Northflank par silently OFF ho sakti hai.**
   `app/api/auth.py` sirf `RAILWAY_*` markers check karta hai — Northflank par ye nahi
   hote. Agar `PAPER_MAKER_API_KEY` miss ho jaye to app crash nahi karegi, chup-chaap
   `/api` public kar degi (AI tokens + DB khula). **Mitigation:** Northflank env par
   **`PAPER_MAKER_REQUIRE_API_KEY=1` zaroor set karo** — ye flag akela `_is_deployment()`
   ko True deta hai (code se verified), koi code change nahi chahiye. *(Optional future:
   agar Northflank ka koi reliable env marker mile to `_DEPLOY_ENV_MARKERS` mein add —
   par flag primary aur kaafi hai.)*

3. **🟠 `$PORT` inject nahi hota.** (Detail §2b.) App fixed port (8080) par listen kare
   aur wahi Northflank port config mein ho — warna health check fail + app unreachable.
   Dockerfile `CMD` mein hardcode + `EXPOSE 8080`. `--port $PORT` yahan mat use karo.

4. **🟠 SQLite raw-copy corruption.** Live DB ka raw copy while writing = corrupt.
   Hamesha `.backup` + integrity-check (§3a).

5. **🟠 Volume-attached service = single replica + recreate deploy.** SQLite ke liye ye
   sahi hai (single writer chahiye), par har deploy par chhoti downtime hogi (naya
   instance purane ko replace karega, zero-downtime nahi). School hours ke bahar deploy
   karo.

6. **🟠 PDF export band rahega — Word (.docx) chalega. (deferred, alag PR).** Slim
   Dockerfile mein LibreOffice nahi, to `_find_soffice()` None → app clean
   `PdfConversionFailed` JSON deti hai (500 HTML nahi). Word export bina LibreOffice
   ke chalta hai. **Follow-up PR (Northflank settle hone ke baad):** Dockerfile mein
   `apt-get install -y libreoffice-writer` add → PDF wapas (image bada + RAM zyada, is
   liye migration ke saath nahi). ROADMAP §C follow-up entry banega.

7. **🟡 CORS lockout.** `PAPER_MAKER_ALLOWED_ORIGINS` mein naya Northflank origin add nahi
   kiya to frontend CORS par fail. Deploy ke waqt set karo; transition mein dono origins.

8. **🟡 Free-tier resource limits.** 0.5 GB volume + ~1 GB RAM. SQLite DB (<50 MB) +
   FastAPI + docx export ke liye kaafi (light). *(Note: jab future PR mein LibreOffice
   add ho, PDF conversion RAM-hungry hai — tab is limit par nazar rakhni hogi; abhi slim
   image mein wo issue nahi.)*

9. **🟢 Secret hygiene + key rotation (rotate).** Nayi `PAPER_MAKER_API_KEY` generate,
   Railway purani rollback-window (~1 hafta) tak zinda, phir retire. Screen-share band,
   temporary DB URLs turant revoke.

---

## 6. Post-migration smoke checklist (naye Northflank URL par)

Deploy "done" tabhi jab ye sab pass ho (CLAUDE.md §9 — live verify, not faith):

- [ ] `GET /` → 200, static frontend load.
- [ ] `GET /api/...` **bina** key → **401** (fail-closed auth ON — gotcha #2 confirm).
- [ ] `GET /api/...` **sahi** key ke saath → 200.
- [ ] Question bank: prod ka **purana data dikh raha hai** (restore success — empty nahi).
- [ ] Ek paper generate (MCQ/mixed) → questions aayein.
- [ ] Adaptive paper generate → paper_type honor ho (R3 feature).
- [ ] Word (.docx) export → valid file download (EN + UR text sahi).
- [ ] **PDF export → clean `PdfConversionFailed` JSON** (500 HTML nahi) — expected,
      slim image mein LibreOffice nahi (PDF deferred to later PR).
- [ ] Ek naya question add → **redeploy trigger (dummy commit) → restart ke baad question
      abhi bhi hai** (persistent volume confirm — sabse important test).
- [ ] Logs: koi startup warning/crash nahi; `init_db()` migrations clean.
- [ ] Mobile app / bookmark naye URL par chal raha hai.

Sab green → Railway ~1 hafta baad decommission.

---

## 7. Rollback

Agar Northflank par kuch bhi tootey aur fix na ho:
- Railway abhi bhi live hai (delete nahi kiya) → traffic wapas Railway URL par.
- Northflank service pause/delete.
- Backup `paper_maker.db` local par safe — koi data loss nahi.
- Zero-downtime rollback jab tak Railway credit bacha hai.

---

## 8. Decisions (LOCKED — reviewed 4 July 2026)

1. **Hosting:** ✅ **Northflank Sandbox (free)** — free limit mein $0. Card mandatory
   (charge nahi) — accepted. Render/Fly/Koyeb free tiers persistent SQLite nahi dete.
2. **Build:** ✅ **Slim Dockerfile** (`python:3.12-slim`, **no LibreOffice**) —
   migrate-first (image chhoti, build fast; Railway credit khatam ho raha). Reliable
   start/port. Buildpack rejected.
3. **Port:** ✅ fixed **8080** (Northflank `$PORT` nahi deta), Dockerfile `CMD` + Ports
   config dono mein.
4. **PDF export:** ✅ **Deferred (accept-break)** — slim image mein band, Word chalega.
   Northflank settle hone ke baad alag PR mein LibreOffice add karke wapas (gotcha #6).
5. **Local Docker:** ✅ **Install nahi karenge** (is machine par Docker/WSL nahi). Slim
   Dockerfile Northflank cloud build karega; verify build logs + deployed smoke test se.
6. **DB restore:** ✅ **Manual** (safe `.backup` → temp URL → Northflank shell `curl` →
   restart → integrity-check). Koi admin route nahi.
7. **API key:** ✅ **Rotate** — nayi key, purani Railway retire (rollback window baad).
8. **Auth fail-closed:** ✅ Northflank env par **`PAPER_MAKER_REQUIRE_API_KEY=1`** (code
   change nahi chahiye — flag akela kaafi).
9. **Config-as-code:** ⏸️ Northflank template optional/later; pehle UI se set.

### Implementation ka rough order (jab "implement karo" bolo)
1. **PR-1 (code):** repo root par **slim** `Dockerfile` (python:3.12-slim, no LibreOffice,
   uvicorn on 8080). Local Docker nahi → Northflank cloud build + deployed verify.
2. **Manual ops (no code):** backup → Northflank project/service (Dockerfile, port 8080,
   auto-deploy) → volume `/data` → env vars (incl. `PAPER_MAKER_REQUIRE_API_KEY=1` + rotated
   key) → DB restore → smoke checklist (§6) → URL switch → ~1 hafta baad Railway retire.
3. **ROADMAP update:** O1 done mark (target = Northflank, not Render); PDF deferred note.
4. **Follow-up PR (PDF, later):** Dockerfile mein `libreoffice-writer` add → PDF export
   wapas + smoke re-verify.
5. **Optional:** Northflank template (config-as-code) as separate PR.

---

## Sources (verified July 2026)
- Northflank pricing / free Sandbox — [northflank.com/pricing](https://northflank.com/pricing)
  · 2 services, always-on (no sleep), free volume; card required.
- Card requirement — [Pricing on Northflank (docs)](https://northflank.com/docs/v1/application/billing/pricing-on-northflank)
  · *"all users must add a payment method ... regardless of plan selection."*
- Build (Dockerfile/buildpack) — [Build and deploy your code (docs)](https://northflank.com/docs/v1/application/getting-started/build-and-deploy-your-code)
- Ports (no `$PORT` injection; declare your port) — [Configure ports (docs)](https://northflank.com/docs/v1/application/network/configure-ports)
- Volumes (mount path, size) — [Add a volume (docs)](https://northflank.com/docs/v1/application/databases-and-persistence/add-a-volume)
- Disk/egress overage pricing — $0.30/GB/mo disk, $0.15/GB egress (Northflank pricing).
