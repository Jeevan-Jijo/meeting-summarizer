import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import Meeting, Recording

router = APIRouter(prefix="/audio", tags=["Audio"])

@router.get("/{meeting_id}")
def stream_meeting_audio(meeting_id: int, db: Session = Depends(get_db)):
    """Stream audio recording for playback in the web player."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.recording:
        raise HTTPException(status_code=404, detail="Audio recording not found")

    rec = meeting.recording
    # Prefer normalized WAV if available, otherwise original file
    path_to_serve = rec.normalized_path if (rec.normalized_path and os.path.exists(rec.normalized_path)) else rec.file_path

    if not os.path.exists(path_to_serve):
        raise HTTPException(status_code=404, detail="Audio file not found on server disk")

    ext = os.path.splitext(path_to_serve)[1].lower()
    media_type = "audio/wav" if ext == ".wav" else (rec.mime_type or "audio/mpeg")

    return FileResponse(
        path=path_to_serve,
        media_type=media_type,
        filename=os.path.basename(path_to_serve)
    )
