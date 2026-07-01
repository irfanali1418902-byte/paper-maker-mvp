"""HTTP route for home-screen quick stats."""

from fastapi import APIRouter, HTTPException

from app.schemas.responses import QuickStatsResponse
from app.services import stats_service

router = APIRouter()


@router.get("/api/stats", response_model=QuickStatsResponse)
def get_stats():
    """Home screen ke quick stats: total papers, is mahine ke result uploads,
    sab se zyada use hone wala subject, aur question bank ka size."""
    try:
        return stats_service.get_quick_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats fetch fail hui (DB error): {e}") from e
