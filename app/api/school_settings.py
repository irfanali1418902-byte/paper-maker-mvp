"""HTTP routes for school settings (singleton)."""

from fastapi import APIRouter

from app.models.requests import SchoolSettings
from app.models.responses import StatusResponse
from app.services import settings_service

router = APIRouter()


@router.get("/api/school-settings", response_model=SchoolSettings)
def get_school_settings():
    return settings_service.get_settings()


@router.post("/api/school-settings", response_model=StatusResponse)
def save_school_settings(settings: SchoolSettings):
    settings_service.save_settings(settings)
    return {"status": "saved"}
