# Local Deployment Guide — School System (AII Smart Paper Maker)

FastAPI app ek **school computer** (server) par chalti hai. 20 teachers usi WiFi/LAN par
apne browser se `http://<server-IP>:8000` khol kar use karte hain. Koi cloud/monthly cost
nahi. **Internet sirf AI question-generation (Gemini) ke waqt** chahiye — question bank,
papers, dashboard, Word/PDF export sab **offline** chalte hain.

**Server PC requirement:** 4 GB RAM kaafi hai (app halki hai — Python + SQLite). Ek PC
chuno jo school hours mein ON + LAN par rahe.

---

## 1. Prerequisites (server PC par ek dafa)

| Software | Kyun | Kahan se |
|---|---|---|
| **Python 3.12** | app runtime | https://www.python.org/downloads/ (3.12.x; "Add Python to PATH" tick karo) |
| **LibreOffice** *(optional)* | **PDF export** chalane ke liye | https://www.libreoffice.org/download — default path par install (`C:\Program Files\LibreOffice\`) |

> LibreOffice ke baghair: **Word (.docx) export chalega**, PDF export par app saaf error
> deti hai. LibreOffice install karte hi PDF export bhi chalne lagega (app khud
> `C:\Program Files\LibreOffice\program\soffice.exe` dhoond leti hai).

Verify (CMD/PowerShell): `python --version` → `Python 3.12.x`.

---

## 2. Code laao

```
git clone https://github.com/irfanali1418902-byte/paper-maker-mvp.git
cd paper-maker-mvp
```
(Ya repo ka ZIP copy karke server PC par rakh do.)

---

## 3. Virtual environment + dependencies

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
Sab pip se aata hai (koi system tool nahi). Ek dafa internet chahiye.

---

## 4. Database — school ka real data

App SQLite ka **ek file** use karti hai. Data ko repo se bahar ek stable folder mein rakho
taake git operations/updates se mehfooz rahe:

1. Folder banao: `C:\PaperMakerData\`
2. **Real data (247 questions, 27 papers…):** verified backup file
   `paper_maker_prod_20260704.db` ko us folder mein **`paper_maker.db`** naam se copy karo.
   *(Ya fresh khaali DB chahiye to ye step chhod do — app pehli baar khud bana legi.)*
3. Neeche `DB_PATH` isi file ko point karega.

> ⚠️ Agar cloud (Railway/Northflank) copies bhi chal rahi hain to data alag-alag ho jayega
> (local aur cloud sync nahi hote). Tay karo **kaun sa primary** hai; ek hi jagah edit ho.

---

## 5. Configuration (env vars)

Repo root mein ek **`env.local.bat`** file banao (ye **gitignored** hai — secrets safe).
`start-local.bat` isko khud load kar leta hai. Content:

```bat
set DB_PATH=C:\PaperMakerData\paper_maker.db
set PAPER_MAKER_API_KEY=your-long-random-key
set GEMINI_API_KEY=your-gemini-key
```

Vars ka matlab:

| Var | Value | Note |
|---|---|---|
| `DB_PATH` | `C:\PaperMakerData\paper_maker.db` | step 4 wali file |
| `PAPER_MAKER_API_KEY` | koi lambi random string | teachers ise ek dafa app ke "Access key" box mein daalenge (browser yaad rakhta hai). **Set na karo to LAN par auth OFF** (trusted network ho to theek) |
| `GEMINI_API_KEY` | apni Gemini key | AI question generation ke liye (internet ke saath). Na ho to baaki app chalti hai, AI generate band |

---

## 6. Windows Firewall — port 8000 kholo (20 teachers ke liye zaroori)

**Admin** PowerShell mein ek dafa:
```
netsh advfirewall firewall add rule name="Paper Maker 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## 7. Server chalao

**Aasan:** repo mein `start-local.bat` par double-click (venv activate + env + server + IP
dikhata hai).

**Ya manually** (venv active hote hue):
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
`--host 0.0.0.0` zaroori hai — isi se doosre devices LAN par connect kar paate hain.

---

## 8. Access — teachers kaise kholenge

- **Server PC par khud:** http://localhost:8000
- **Kisi bhi teacher ke phone/laptop (same WiFi) par:** `http://<server-IP>:8000`

Server PC ka IP (CMD): `ipconfig` → `IPv4 Address` (jaise `192.168.1.25`) → teachers
kholenge **http://192.168.1.25:8000**.

- Router mein server PC ko **static/reserved IP** do (reboot par IP na badle).
- Agar `PAPER_MAKER_API_KEY` set hai: har teacher pehli baar "Access key" box mein wahi key
  daalega (browser localStorage mein save ho jati hai).

---

## 9. Server ko chalta rakhna (recommended)

- **Simple:** `start-local.bat` ki shortcut `shell:startup` folder mein — PC on hote hi chalu.
- **Service jaisa (auto-restart, background):** [NSSM](https://nssm.cc/download) se —
  ```
  nssm install PaperMaker "C:\path\paper-maker-mvp\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
  nssm set PaperMaker AppDirectory "C:\path\paper-maker-mvp"
  nssm set PaperMaker AppEnvironmentExtra DB_PATH=C:\PaperMakerData\paper_maker.db PAPER_MAKER_API_KEY=... GEMINI_API_KEY=...
  nssm start PaperMaker
  ```

---

## 10. Backups (SQLite = ek file, aasan)

Rozana/haftawar `C:\PaperMakerData\paper_maker.db` ko kisi aur drive/USB par copy kar lo.
Safe copy ke liye (app chalte hue) SQLite `.backup` behtar hai:
```
python -c "import sqlite3; s=sqlite3.connect(r'C:\PaperMakerData\paper_maker.db'); d=sqlite3.connect(r'D:\backups\paper_maker_%DATE%.db'); s.backup(d); print('ok')"
```

---

## 11. Troubleshooting

| Masla | Hal |
|---|---|
| Teacher connect nahi hota | Firewall rule (step 6)? Same WiFi? Sahi IP? Server `--host 0.0.0.0` par chal raha? |
| `/api` par "API key ghalat ya missing" | Teacher ne sahi key daali? Server par `PAPER_MAKER_API_KEY` wahi hai? |
| AI generate fail | `GEMINI_API_KEY` set + internet? |
| PDF export error, Word chal raha | LibreOffice install karo (step 1) — default path par |
| Purana data nahi dikh raha | `DB_PATH` sahi file (step 4) point kar raha? |

---

## Internet dependency — saaf
- **One-time setup:** `pip install` ke liye internet.
- **Rozana:** sirf **Gemini AI** call ke waqt internet. Baaki sab (bank, papers, dashboard,
  Word/PDF export, 20 teachers LAN serving) **offline**.

---

## (Task 3 — future) Company/Publisher distribution
Multi-school package alag `docs/DISTRIBUTION.md` mein: Docker image (Python + LibreOffice
bundled), ek installer script, per-school config (DB_PATH, keys, port), aur update mechanism.
Repo ka `Dockerfile` (slim, cloud wala) is ke liye base hai — LibreOffice add hoga.
