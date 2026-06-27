"""HTTP routes for the Phase 2 result analyzer dashboard.

Read-only views over uploaded results: list a paper's uploads, and the
per-student / per-question / per-Bloom dashboard for a given upload (or the
paper's latest upload).
"""

from fastapi import APIRouter, HTTPException

from app.models.responses import DashboardResponse, UploadsResponse
from app.services import dashboard_service

router = APIRouter()


@router.get("/api/paper/{paper_id}/uploads", response_model=UploadsResponse)
def list_paper_uploads(paper_id: str):
    """Saare results uploads is paper ke liye, newest pehle. Empty list ka
    matlab paper to hai par abhi koi result upload nahi hua."""
    try:
        uploads = dashboard_service.list_uploads(paper_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Uploads fetch fail hui (DB error): {e}"
        ) from e
    if uploads is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")
    return {"uploads": uploads}


@router.get("/api/paper/{paper_id}/dashboard", response_model=DashboardResponse)
def get_paper_dashboard(paper_id: str):
    """Is paper ke latest upload ka full dashboard — frontend ke paas sirf
    paper_id ho to yehi use karein."""
    try:
        dashboard = dashboard_service.get_latest_dashboard_for_paper(paper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard banane mein DB error: {e}") from e
    if dashboard is None:
        raise HTTPException(
            status_code=404,
            detail="Paper nahi mila ya is paper ka koi result abhi upload nahi hua.",
        )
    return dashboard


@router.get("/api/upload/{upload_id}/dashboard", response_model=DashboardResponse)
def get_upload_dashboard(upload_id: str):
    """Kisi specific upload ka dashboard (jab teacher purane upload dekhna chahe)."""
    try:
        dashboard = dashboard_service.get_dashboard_for_upload(upload_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard banane mein DB error: {e}") from e
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Upload nahi mila.")
    return dashboard
