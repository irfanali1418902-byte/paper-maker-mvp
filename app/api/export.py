"""HTTP routes for exporting a generated paper as Word (.docx) or PDF."""

from fastapi import APIRouter, HTTPException, Response

from app.services import export_service
from app.services.exceptions import PdfConversionFailed

router = APIRouter()

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/api/paper/{paper_id}/export.docx")
def export_paper_docx(paper_id: str):
    """Paper ko editable Word file ke roop mein download karta hai (Urdu RTL
    support ke saath)."""
    try:
        docx_bytes = export_service.build_paper_docx(paper_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Word export fail hui: {e}") from e
    if docx_bytes is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")

    return Response(
        content=docx_bytes,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="paper-{paper_id}.docx"'},
    )


@router.get("/api/paper/{paper_id}/export.pdf")
def export_paper_pdf(paper_id: str):
    """Paper ko PDF ke roop mein download karta hai. Andar wahi .docx banti hai
    jo Word export deta hai, phir LibreOffice se PDF mein convert hoti hai."""
    try:
        pdf_bytes = export_service.build_paper_pdf(paper_id)
    except PdfConversionFailed as e:
        # Upstream tool (LibreOffice) ki problem — 502, message admin ke liye.
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export fail hui: {e}") from e
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Paper nahi mila.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="paper-{paper_id}.pdf"'},
    )
