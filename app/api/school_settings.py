"""HTTP routes for school settings (singleton)."""

from fastapi import APIRouter, HTTPException

from app.schemas.requests import SchoolSettings
from app.schemas.responses import StatusResponse
from app.services import settings_service

router = APIRouter()


@router.get("/api/school-settings", response_model=SchoolSettings)
def get_school_settings():
    try:
        return settings_service.get_settings()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Settings fetch fail hui (DB error): {e}"
        ) from e


@router.post("/api/school-settings", response_model=StatusResponse)
def save_school_settings(settings: SchoolSettings):
    try:
        settings_service.save_settings(settings)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Settings save fail hui (DB error): {e}"
        ) from e
    return {"status": "saved"}
