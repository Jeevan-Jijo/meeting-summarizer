from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.db_models import ProcessingJob, Meeting
from app.schemas.job import ProcessingJobRead, ProcessingJobListItem

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=List[ProcessingJobListItem])
def list_jobs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List recent processing jobs."""
    jobs = db.query(ProcessingJob).order_by(desc(ProcessingJob.created_at)).offset(skip).limit(limit).all()
    results = []
    for j in jobs:
        meeting_title = j.meeting.title if j.meeting else "Unknown Meeting"
        results.append(ProcessingJobListItem(
            id=j.id,
            meeting_id=j.meeting_id,
            meeting_title=meeting_title,
            status=j.status,
            progress_percent=j.progress_percent,
            current_step=j.current_step,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
            created_at=j.created_at
        ))
    return results

@router.get("/{job_id}", response_model=ProcessingJobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Fetch processing job status, logs, and progress."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/meeting/{meeting_id}/latest", response_model=Optional[ProcessingJobRead])
def get_latest_job_for_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Fetch the latest processing job for a specific meeting."""
    job = db.query(ProcessingJob).filter(ProcessingJob.meeting_id == meeting_id).order_by(desc(ProcessingJob.created_at)).first()
    return job
