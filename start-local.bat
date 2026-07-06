@echo off
REM ============================================================
REM  AII Smart Paper Maker - Local Server launcher (Windows)
REM  Double-click to start. Secrets env.local.bat se aati hain.
REM ============================================================
title AII Paper Maker - Local Server
cd /d "%~dp0"

REM --- Local secrets/config (gitignored). env.local.bat banao is content ke saath:
REM       set DB_PATH=C:\PaperMakerData\paper_maker.db
REM       set PAPER_MAKER_API_KEY=your-long-random-key
REM       set GEMINI_API_KEY=your-gemini-key
if exist "env.local.bat" (
  call env.local.bat
) else (
  echo [!] env.local.bat nahi mila - DB_PATH default (repo) use hoga, keys unset.
  echo     SETUP-LOCAL.md step 5 dekhein.
)

REM --- Virtual environment
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [X] .venv nahi mila. Pehle chalao:
  echo        python -m venv .venv
  echo        .venv\Scripts\activate ^&^& pip install -r requirements.txt
  pause
  exit /b 1
)

echo(
echo ============================================================
echo   AII Smart Paper Maker - Local Server
echo ============================================================
echo   Is PC ke addresses (192.168.x.x wala note karein):
echo ------------------------------------------------------------
ipconfig | findstr /C:"IPv4"
echo ------------------------------------------------------------
echo   Is PC par:       http://localhost:8000
echo   Teachers (LAN):  http://[upar-wala-192.168-IP]:8000
echo   Band karne ke liye: Ctrl+C
echo ============================================================
echo(

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo(
echo Server band ho gaya. Koi key dabayein.
pause >nul
