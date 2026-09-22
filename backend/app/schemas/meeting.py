import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# Base & Shared Schemas
class TranscriptSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    speaker_id: Optional[int] = None
    speaker_label: str
    start_time: float
    end_time: float
    raw_text: str
    cleaned_text: str
    confidence: float
    language: Optional[str] = "en"


class SpeakerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    speaker_tag: str
    display_name: str
    is_customized: bool
    speaking_time_seconds: float
    speaking_percentage: float
    turn_count: int
    avg_turn_seconds: float
    estimated_tone: Optional[str] = None


class SpeakerUpdate(BaseModel):
    display_name: str


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    original_filename: str
    file_size_bytes: int
    duration_seconds: float
    mime_type: Optional[str] = None
    created_at: datetime.datetime


class MeetingSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    executive_summary: str
    agenda_topics: List[str]
    overall_sentiment_estimate: Optional[str] = None
    sentiment_justification: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class MeetingSummaryUpdate(BaseModel):
    executive_summary: Optional[str] = None
    agenda_topics: Optional[List[str]] = None
    overall_sentiment_estimate: Optional[str] = None
    sentiment_justification: Optional[str] = None


class KeyPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    point: str
    category: str
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class KeyPointUpdate(BaseModel):
    point: Optional[str] = None
    category: Optional[str] = None


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    decision: str
    context: Optional[str] = None
    impact: Optional[str] = None
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class DecisionUpdate(BaseModel):
    decision: Optional[str] = None
    context: Optional[str] = None
    impact: Optional[str] = None


class ActionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    description: str
    assignee: str
    deadline: Optional[str] = None
    priority: str
    is_completed: bool
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class ActionItemUpdate(BaseModel):
    description: Optional[str] = None
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    is_completed: Optional[bool] = None


class ImportantDateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    raw_phrase: str
    normalized_date: Optional[str] = None
    description: str
    needs_confirmation: bool
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class ImportantDateUpdate(BaseModel):
    raw_phrase: Optional[str] = None
    normalized_date: Optional[str] = None
    description: Optional[str] = None
    needs_confirmation: Optional[bool] = None


class ScheduledEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    event_title: str
    date_phrase: str
    normalized_datetime: Optional[str] = None
    participants: List[str]
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class ScheduledEventUpdate(BaseModel):
    event_title: Optional[str] = None
    date_phrase: Optional[str] = None
    normalized_datetime: Optional[str] = None
    participants: Optional[List[str]] = None


class TakeawayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    takeaway: str
    category: str
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class TakeawayUpdate(BaseModel):
    takeaway: Optional[str] = None
    category: Optional[str] = None


class UnresolvedQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    question: str
    raised_by: str
    context: Optional[str] = None
    source_segment_ids: List[int]
    source_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: float


class UnresolvedQuestionUpdate(BaseModel):
    question: Optional[str] = None
    raised_by: Optional[str] = None
    context: Optional[str] = None


# Meeting Details & List
class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    meeting_date: datetime.datetime
    duration_seconds: float
    status: str
    speaker_count: int
    action_item_count: int
    created_at: datetime.datetime


class MeetingDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    meeting_date: datetime.datetime
    duration_seconds: float
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    recording: Optional[RecordingRead] = None
    speakers: List[SpeakerRead] = []
    transcript_segments: List[TranscriptSegmentRead] = []
    summary: Optional[MeetingSummaryRead] = None
    key_points: List[KeyPointRead] = []
    decisions: List[DecisionRead] = []
    action_items: List[ActionItemRead] = []
    important_dates: List[ImportantDateRead] = []
    scheduled_events: List[ScheduledEventRead] = []
    takeaways: List[TakeawayRead] = []
    unresolved_questions: List[UnresolvedQuestionRead] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_date: Optional[datetime.datetime] = None
