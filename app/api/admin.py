"""TEMPORARY admin route — token-gated DB restore.

Local paper_maker.db ko deployed instance par upload karne ke liye. Endpoint tab
tak inert (403) jab tak DB_UPLOAD_TOKEN env set na ho. Use ke baad ye file +
db_admin_service.py hata dein aur main.py se admin include nikaal dein.

  curl -F "token=$DB_UPLOAD_TOKEN" -F "file=@paper_maker.db" \\
       https://<app>.up.railway.app/api/admin/restore-db
"""

import secrets

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import db_admin_service

router = APIRouter()


@router.post("/api/admin/restore-db")
def restore_db(token: str = Form(...), file: UploadFile = File(...)):
    expected = db_admin_service.upload_token()
    if not expected:
        raise HTTPException(
            status_code=403, detail="DB restore disabled — DB_UPLOAD_TOKEN env set nahi."
        )
    # Constant-time compare — token guess ko timing se asaan na banaye.
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Token galat hai.")
    if not (file.filename or "").lower().endswith(".db"):
        raise HTTPException(status_code=400, detail="Sirf .db file upload karein.")

    data = file.file.read()
    try:
        result = db_admin_service.restore_db(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB restore fail hui: {e}") from e

    return {"status": "ok", **result}
