import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    status: str
    progress_percent: float
    current_step: str
    error_message: Optional[str] = None
    logs: List[str] = []
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime


class ProcessingJobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    meeting_title: str
    status: str
    progress_percent: float
    current_step: str
    error_message: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
