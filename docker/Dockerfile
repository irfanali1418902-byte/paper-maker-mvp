# =============================================================================
# Paper Maker — DISTRIBUTION image (on-prem / multi-school).
#
# Cloud ./Dockerfile (Northflank, slim, no LibreOffice) se ALAG. Yahan LibreOffice +
# EN/Urdu fonts bundled hain taake **PDF export container ke andar chale** (app bilingual
# hai — Urdu Nastaliq render zaroori). SQLite DB /data volume par persist hoti hai.
#
# Build (repo root se):  docker build -f docker/Dockerfile -t paper-maker:latest .
# Ya:                    docker compose -f docker/docker-compose.yml up -d --build
# =============================================================================
FROM python:3.12-slim

# System deps: LibreOffice (docx->pdf via soffice) + fonts (Latin + Urdu Nastaliq).
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-writer \
      fonts-liberation \
      fonts-dejavu-core \
      fonts-noto-core \
      fonts-noto-nastaliq-urdu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# soffice ko HOME chahiye hota hai (root ke liye set); app UserInstallation profile
# temp mein banata hai, par HOME safe-side.
ENV HOME=/root

WORKDIR /app

# Deps pehle (layer cache).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DB persistent volume par (docker-compose /data mount karta hai).
ENV DB_PATH=/data/paper_maker.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
