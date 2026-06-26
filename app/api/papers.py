"""HTTP routes for paper assembly and retrieval."""

from fastapi import APIRouter, HTTPException

from app.models.requests import GeneratePaperRequest
from app.models.responses import GeneratePaperResponse, PaperResponse
from app.services import paper_service

router = APIRouter()


@router.post("/api/generate-paper", response_model=GeneratePaperResponse)
def generate_paper(req: GeneratePaperRequest):
    """Question bank se Bloom + difficulty distribution ke hisaab se balanced
    paper assemble karta hai. Least-used questions ko priority deta hai
    (taake repetition kam ho)."""
    try:
        result = paper_service.assemble_balanced_paper(req)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Paper assemble fail hui (DB error): {e}"
        ) from e
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Is subject/Bloom-level ke liye question bank khali hai. Pehle /api/generate-questions se questions banayen.",
        )
    return result


@router.get("/api/paper/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: str):
    try:
        result = paper_service.get_paper_with_questions(paper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Paper fetch fail hui (DB error): {e}") from e
    if result is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")
    return result
