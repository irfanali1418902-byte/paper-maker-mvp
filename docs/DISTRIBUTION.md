# Company / Multi-School Distribution — Docker Package

Paper Maker ko **kisi bhi school** par ek Docker container se deploy karo. Har school apna
container + apna data + apni keys chalata hai. Sab kuch bundled hai (Python, LibreOffice,
Urdu/EN fonts) — **PDF export bhi container ke andar chalta hai**. Sirf Gemini AI ke liye
internet chahiye.

Ye [SETUP-LOCAL.md](SETUP-LOCAL.md) (manual Python install) ka **packaged** version hai —
IT staff ke liye tez, dohराने-layak, aur consistent.

---

## Files (repo mein)
```
docker/
  Dockerfile          # distribution image (Python + LibreOffice + fonts)
  docker-compose.yml  # service + persistent DB volume + auto-restart + healthcheck
  .env.example        # per-school config template
docs/DISTRIBUTION.md  # ye file
```

---

## 1. Server (school) requirements
- **Docker** installed:
  - Windows/Mac: **Docker Desktop** (https://www.docker.com/products/docker-desktop)
  - Linux: **Docker Engine** + `docker compose` plugin
- **RAM:** ~2 GB image ko + runtime; 4 GB PC theek. (LibreOffice PDF export RAM-hungry
  hota hai — ek waqt mein ek conversion.)
- School LAN par ek always-on PC.

---

## 2. Deploy (ek school) — 4 steps

```bash
# 1) Package laao
git clone https://github.com/irfanali1418902-byte/paper-maker-mvp.git
cd paper-maker-mvp

# 2) Per-school config
cp docker/.env.example docker/.env
#    docker/.env kholo -> PAPER_MAKER_API_KEY (lambi random), GEMINI_API_KEY bharo

# 3) (optional) Real data: backup DB ko volume par rakho
mkdir -p docker/data
cp /path/to/paper_maker_prod_YYYYMMDD.db docker/data/paper_maker.db
#    (skip karo to app pehli baar khaali DB bana legi)

# 4) Build + run
docker compose -f docker/docker-compose.yml up -d --build
```

Pehli build LibreOffice ki wajah se thoda time (~kuch minute) legi. Baad ke runs cached.

---

## 3. Access (teachers)
- Server PC ka LAN IP nikalo (`ipconfig` / `ip addr`) → jaise `192.168.1.25`.
- Teachers browser mein: **http://192.168.1.25:8000**
- `PAPER_MAKER_API_KEY` set hai to har teacher pehli baar "Access key" box mein wahi key
  daalega (browser yaad rakhta hai).
- Firewall: Windows par host port 8000 inbound allow karo (SETUP-LOCAL.md step 6).

---

## 4. Manage
```bash
docker compose -f docker/docker-compose.yml ps          # status
docker compose -f docker/docker-compose.yml logs -f     # live logs
docker compose -f docker/docker-compose.yml restart     # restart
docker compose -f docker/docker-compose.yml down        # stop (data safe rehta hai)
```
`restart: unless-stopped` — PC reboot/crash par container khud chalu ho jata hai.

---

## 5. Backups (zaroori — asli data)
Poora data ek file mein: **`docker/data/paper_maker.db`**. Ise regularly kisi aur
drive/USB par copy karo. Live-safe copy:
```bash
docker compose -f docker/docker-compose.yml exec paper-maker \
  python -c "import sqlite3; s=sqlite3.connect('/data/paper_maker.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d); print('ok')"
# phir docker/data/backup.db ko bahar copy karo
```

---

## 6. Updates (naya version deploy)
```bash
git pull
docker compose -f docker/docker-compose.yml up -d --build
```
DB volume (`docker/data/`) chhua nahi jata — data safe rehta hai. `init_db()` naye
schema migrations khud laga leta hai.

---

## 7. Multi-school notes
- **Har school = alag copy** (apna `docker/.env` + apna `docker/data/`). Ek dusre se independent.
- Ek hi PC par kai schools chalane ho to har ek ke liye alag `HOST_PORT` (`.env` mein) +
  alag data folder do.
- **Har school ki API key alag** rakho (leak ho to sirf ek school affect ho).
- Gemini key: ek shared company key, ya per-school — usage/billing policy ke mutabiq.

---

## 8. PDF export / Urdu
- Container mein `libreoffice-writer` + `fonts-noto-nastaliq-urdu` bundled — Word aur **PDF
  dono** chalte hain, Urdu Nastaliq render hota hai.
- Agar kisi khaas font ki zaroorat ho to `docker/Dockerfile` ke `apt-get` list mein add
  karke rebuild karo.

---

## 9. Troubleshooting
| Masla | Hal |
|---|---|
| `docker compose` command nahi | Docker Desktop chal raha? Linux par `docker compose` plugin? |
| Teachers connect nahi hote | Host firewall port 8000? Same LAN? Sahi IP? |
| PDF export fail | Container logs dekho; image rebuild (`up -d --build`) |
| Data gayab | `docker/data/paper_maker.db` mojood? `.env` ka `DB_PATH=/data/paper_maker.db`? |
| Port busy | `docker/.env` mein `HOST_PORT` badlo |

---

## 10. Cloud vs distribution image (do alag Dockerfiles)
- **`./Dockerfile`** (repo root) — cloud (Northflank) ke liye **slim, no LibreOffice**, PDF
  deferred. Ise mat badlo (live cloud deploy isi par hai).
- **`docker/Dockerfile`** — ye distribution image, **LibreOffice + fonts bundled**. On-prem
  schools ke liye.
