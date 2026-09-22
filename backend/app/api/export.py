from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import Meeting
from app.schemas.meeting import MeetingDetail
from app.services.export_service import generate_markdown_mom, generate_json_mom, generate_pdf_mom

router = APIRouter(prefix="/export", tags=["Export"])

def _get_meeting_dict(meeting_id: int, db: Session) -> dict:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Serialize to dict via Pydantic MeetingDetail schema
    detail = MeetingDetail.model_validate(meeting)
    return detail.model_dump()


@router.get("/{meeting_id}/markdown", response_class=PlainTextResponse)
def export_meeting_markdown(meeting_id: int, db: Session = Depends(get_db)):
    """Export Minutes of Meeting as clean Markdown."""
    meeting_dict = _get_meeting_dict(meeting_id, db)
    md_content = generate_markdown_mom(meeting_dict)
    
    filename = f"minutes_meeting_{meeting_id}.md"
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{meeting_id}/json")
def export_meeting_json(meeting_id: int, db: Session = Depends(get_db)):
    """Export complete structured meeting data as JSON."""
    meeting_dict = _get_meeting_dict(meeting_id, db)
    json_str = generate_json_mom(meeting_dict)
    
    filename = f"meeting_{meeting_id}_data.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{meeting_id}/pdf")
def export_meeting_pdf(meeting_id: int, db: Session = Depends(get_db)):
    """Export polished Minutes of Meeting as PDF."""
    meeting_dict = _get_meeting_dict(meeting_id, db)
    pdf_bytes = generate_pdf_mom(meeting_dict)
    
    filename = f"minutes_meeting_{meeting_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
