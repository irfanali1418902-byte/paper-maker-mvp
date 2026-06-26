"""HTTP routes for paper assembly and retrieval."""

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.models.requests import GeneratePaperRequest
from app.models.responses import GeneratePaperResponse, PaperResponse
from app.services import paper_service, result_service
from app.services.exceptions import ResultsValidationError

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


@router.get("/api/paper/{paper_id}/result-template")
def get_result_template(paper_id: str):
    """Empty CSV template — roll_no, student_name, then one column per
    question in paper order with max marks in the header. Teacher fills
    this in offline aur baad mein upload karte hain (Phase 2 analyzer)."""
    try:
        csv_bytes = result_service.build_result_template_csv(paper_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Result template generate fail hui (DB error): {e}",
        ) from e
    if csv_bytes is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="paper-{paper_id}-results.csv"',
        },
    )


@router.post("/api/paper/{paper_id}/upload-results")
def upload_results(paper_id: str, file: UploadFile = File(...)):
    """Teacher ka filled-in CSV/xlsx (template hi format mein) accept karta
    hai, validate karta hai, aur result_uploads + student_question_results
    mein save karta hai. Validation errors saari ek hi response mein wapas
    aati hain (400) — teacher pura sheet ek hi pass mein fix kare."""
    contents = file.file.read()

    try:
        result = result_service.import_results(paper_id, file.filename, contents)
    except ResultsValidationError as e:
        # Pass the structured per-row errors straight through so the
        # frontend can render them inline against the spreadsheet.
        raise HTTPException(status_code=400, detail=e.errors) from e
    except ValueError as e:
        # Unparseable file / wrong extension — well-formed request, bad content.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Results upload fail hui (DB error): {e}"
        ) from e

    if result is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")
    return result
