# Northflank deploy image — slim Python, koi LibreOffice nahi (PDF export baad ke PR mein).
# App uvicorn ko fixed port 8080 par bind karta hai kyunki Northflank $PORT inject nahi
# karta; wahi 8080 Northflank ke port config mein publicly expose hota hai.
FROM python:3.12-slim

WORKDIR /app

# Deps pehle copy karo taake requirements.txt na badle to ye layer cache ho (build fast).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
