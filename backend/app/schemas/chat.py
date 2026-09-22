import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class Citation(BaseModel):
    segment_id: Optional[int] = None
    start_time: float
    end_time: float
    timestamp_str: str
    speaker_label: str
    text: str

class ChatQueryRequest(BaseModel):
    meeting_id: int
    query: str = Field(..., min_length=1)

class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    role: str
    content: str
    citations: List[Citation] = []
    created_at: datetime.datetime

class ChatQueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    meeting_id: int
    query: str
