import os
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import (
    Meeting, Recording, Speaker, TranscriptSegment, ProcessingJob,
    MeetingSummary, KeyPoint, Decision, ActionItem, ImportantDate,
    ScheduledEvent, Takeaway, UnresolvedQuestion, utcnow
)
from app.schemas.meeting import (
    MeetingListItem, MeetingDetail, MeetingUpdate, SpeakerUpdate, SpeakerRead,
    MeetingSummaryUpdate, MeetingSummaryRead,
    KeyPointUpdate, KeyPointRead, DecisionUpdate, DecisionRead,
    ActionItemUpdate, ActionItemRead, ImportantDateUpdate, ImportantDateRead,
    ScheduledEventUpdate, ScheduledEventRead, TakeawayUpdate, TakeawayRead,
    UnresolvedQuestionUpdate, UnresolvedQuestionRead
)
from app.services.pipeline_worker import process_meeting_pipeline

router = APIRouter(prefix="/meetings", tags=["Meetings"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".mkv", ".aac"}
MAX_FILE_SIZE = 1024 * 1024 * 500  # 500 MB limit

@router.get("", response_model=List[MeetingListItem])
def list_meetings(
    search: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List meetings with optional search and status filter."""
    query = db.query(Meeting)
    
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(or_(Meeting.title.ilike(search_fmt), Meeting.description.ilike(search_fmt)))
        
    if status and status != "ALL":
        query = query.filter(Meeting.status == status)

    meetings = query.order_by(desc(Meeting.created_at)).offset(skip).limit(limit).all()

    items = []
    for m in meetings:
        items.append(MeetingListItem(
            id=m.id,
            title=m.title,
            meeting_date=m.meeting_date,
            duration_seconds=m.duration_seconds,
            status=m.status,
            speaker_count=len(m.speakers),
            action_item_count=len(m.action_items),
            created_at=m.created_at
        ))
    return items


@router.post("/upload")
async def upload_meeting(
    background_tasks: BackgroundTasks,
    title: str = Form("Untitled Meeting"),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an audio or video file or browser recording and trigger local processing pipeline.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )

    # Save file to upload directory
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = str(settings.UPLOAD_DIR / unique_filename)

    file_size = 0
    with open(file_path, "wb") as f_out:
        while content := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(content)
            if file_size > MAX_FILE_SIZE:
                os.remove(file_path)
                raise HTTPException(status_code=400, detail="File size exceeds maximum 500 MB limit.")
            f_out.write(content)

    # Create Meeting and Recording entities
    meeting = Meeting(
        title=title.strip() or "Untitled Meeting",
        description=description.strip() if description else None,
        meeting_date=utcnow(),
        status="QUEUED"
    )
    db.add(meeting)
    db.flush()

    recording = Recording(
        meeting_id=meeting.id,
        original_filename=file.filename,
        file_path=file_path,
        mime_type=file.content_type,
        file_size_bytes=file_size,
        duration_seconds=0.0
    )
    db.add(recording)

    job = ProcessingJob(
        meeting_id=meeting.id,
        status="QUEUED",
        progress_percent=0.0,
        current_step="Queued for processing",
        logs=["[System] Upload received and job queued."]
    )
    db.add(job)
    db.commit()
    db.refresh(meeting)
    db.refresh(job)

    # Trigger background pipeline
    background_tasks.add_task(process_meeting_pipeline, meeting.id, job.id)

    return {
        "meeting_id": meeting.id,
        "job_id": job.id,
        "status": "QUEUED",
        "message": "File uploaded and background processing initiated."
    }


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting_detail(meeting_id: int, db: Session = Depends(get_db)):
    """Fetch full meeting information with transcript, summary, and all extractions."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(meeting_id: int, update_data: MeetingUpdate, db: Session = Depends(get_db)):
    """Update meeting title, description, or date."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if update_data.title is not None:
        meeting.title = update_data.title
    if update_data.description is not None:
        meeting.description = update_data.description
    if update_data.meeting_date is not None:
        meeting.meeting_date = update_data.meeting_date

    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Delete a meeting and its local artifacts."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Clean recording file if present
    if meeting.recording:
        try:
            if os.path.exists(meeting.recording.file_path):
                os.remove(meeting.recording.file_path)
            if meeting.recording.normalized_path and os.path.exists(meeting.recording.normalized_path):
                os.remove(meeting.recording.normalized_path)
        except Exception as e:
            logger.warning(f"Error removing files for meeting {meeting_id}: {e}")

    db.delete(meeting)
    db.commit()
    return {"status": "deleted", "meeting_id": meeting_id}


@router.post("/{meeting_id}/reprocess")
def reprocess_meeting(meeting_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger reprocessing of an existing meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.recording or not os.path.exists(meeting.recording.file_path):
        raise HTTPException(status_code=400, detail="No source recording found to reprocess.")

    meeting.status = "QUEUED"
    job = ProcessingJob(
        meeting_id=meeting.id,
        status="QUEUED",
        progress_percent=0.0,
        current_step="Queued for reprocessing",
        logs=["[System] Reprocessing requested."]
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_meeting_pipeline, meeting.id, job.id)
    return {"status": "QUEUED", "job_id": job.id, "meeting_id": meeting.id}


# --- SPEAKER RENAMING ---
@router.patch("/{meeting_id}/speakers/{speaker_id}", response_model=SpeakerRead)
def rename_speaker(meeting_id: int, speaker_id: int, payload: SpeakerUpdate, db: Session = Depends(get_db)):
    """Rename a speaker and cascade the name to all associated transcript segments."""
    speaker = db.query(Speaker).filter(Speaker.id == speaker_id, Speaker.meeting_id == meeting_id).first()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")

    new_name = payload.display_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Speaker name cannot be empty")

    speaker.display_name = new_name
    speaker.is_customized = True

    # Cascade to all transcript segments for this speaker
    db.query(TranscriptSegment).filter(
        TranscriptSegment.meeting_id == meeting_id,
        TranscriptSegment.speaker_id == speaker_id
    ).update({"speaker_label": new_name})

    db.commit()
    db.refresh(speaker)
    return speaker


# --- EDIT EXTRACTIONS ---
@router.patch("/{meeting_id}/summary", response_model=MeetingSummaryRead)
def update_meeting_summary(meeting_id: int, payload: MeetingSummaryUpdate, db: Session = Depends(get_db)):
    summary = db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    if payload.executive_summary is not None:
        summary.executive_summary = payload.executive_summary
    if payload.agenda_topics is not None:
        summary.agenda_topics = payload.agenda_topics
    if payload.overall_sentiment_estimate is not None:
        summary.overall_sentiment_estimate = payload.overall_sentiment_estimate
    if payload.sentiment_justification is not None:
        summary.sentiment_justification = payload.sentiment_justification

    db.commit()
    db.refresh(summary)
    return summary


@router.patch("/{meeting_id}/action_items/{item_id}", response_model=ActionItemRead)
def update_action_item(meeting_id: int, item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db)):
    item = db.query(ActionItem).filter(ActionItem.id == item_id, ActionItem.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/action_items/{item_id}")
def delete_action_item(meeting_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(ActionItem).filter(ActionItem.id == item_id, ActionItem.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": item_id}


@router.patch("/{meeting_id}/decisions/{decision_id}", response_model=DecisionRead)
def update_decision(meeting_id: int, decision_id: int, payload: DecisionUpdate, db: Session = Depends(get_db)):
    item = db.query(Decision).filter(Decision.id == decision_id, Decision.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Decision not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/decisions/{decision_id}")
def delete_decision(meeting_id: int, decision_id: int, db: Session = Depends(get_db)):
    item = db.query(Decision).filter(Decision.id == decision_id, Decision.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Decision not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": decision_id}


@router.patch("/{meeting_id}/key_points/{point_id}", response_model=KeyPointRead)
def update_key_point(meeting_id: int, point_id: int, payload: KeyPointUpdate, db: Session = Depends(get_db)):
    item = db.query(KeyPoint).filter(KeyPoint.id == point_id, KeyPoint.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Key point not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/key_points/{point_id}")
def delete_key_point(meeting_id: int, point_id: int, db: Session = Depends(get_db)):
    item = db.query(KeyPoint).filter(KeyPoint.id == point_id, KeyPoint.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Key point not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": point_id}


@router.patch("/{meeting_id}/important_dates/{date_id}", response_model=ImportantDateRead)
def update_important_date(meeting_id: int, date_id: int, payload: ImportantDateUpdate, db: Session = Depends(get_db)):
    item = db.query(ImportantDate).filter(ImportantDate.id == date_id, ImportantDate.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Important date not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/important_dates/{date_id}")
def delete_important_date(meeting_id: int, date_id: int, db: Session = Depends(get_db)):
    item = db.query(ImportantDate).filter(ImportantDate.id == date_id, ImportantDate.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Important date not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": date_id}


@router.patch("/{meeting_id}/questions/{question_id}", response_model=UnresolvedQuestionRead)
def update_question(meeting_id: int, question_id: int, payload: UnresolvedQuestionUpdate, db: Session = Depends(get_db)):
    item = db.query(UnresolvedQuestion).filter(UnresolvedQuestion.id == question_id, UnresolvedQuestion.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/questions/{question_id}")
def delete_question(meeting_id: int, question_id: int, db: Session = Depends(get_db)):
    item = db.query(UnresolvedQuestion).filter(UnresolvedQuestion.id == question_id, UnresolvedQuestion.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": question_id}


@router.patch("/{meeting_id}/takeaways/{takeaway_id}", response_model=TakeawayRead)
def update_takeaway(meeting_id: int, takeaway_id: int, payload: TakeawayUpdate, db: Session = Depends(get_db)):
    item = db.query(Takeaway).filter(Takeaway.id == takeaway_id, Takeaway.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Takeaway not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{meeting_id}/takeaways/{takeaway_id}")
def delete_takeaway(meeting_id: int, takeaway_id: int, db: Session = Depends(get_db)):
    item = db.query(Takeaway).filter(Takeaway.id == takeaway_id, Takeaway.meeting_id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Takeaway not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": takeaway_id}
