import datetime
import json
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Untitled Meeting")
    description = Column(Text, nullable=True)
    meeting_date = Column(DateTime, default=utcnow, nullable=False)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="UPLOADED", nullable=False)  # Processing states
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    recording = relationship("Recording", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.start_time")
    processing_jobs = relationship("ProcessingJob", back_populates="meeting", cascade="all, delete-orphan", order_by="desc(ProcessingJob.created_at)")
    summary = relationship("MeetingSummary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    key_points = relationship("KeyPoint", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    important_dates = relationship("ImportantDate", back_populates="meeting", cascade="all, delete-orphan")
    scheduled_events = relationship("ScheduledEvent", back_populates="meeting", cascade="all, delete-orphan")
    takeaways = relationship("Takeaway", back_populates="meeting", cascade="all, delete-orphan")
    unresolved_questions = relationship("UnresolvedQuestion", back_populates="meeting", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="meeting", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    normalized_path = Column(String(512), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="recording")


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    speaker_tag = Column(String(64), nullable=False)  # e.g., "SPEAKER_00", "Speaker 1"
    display_name = Column(String(128), nullable=False)  # e.g. "Speaker 1" or user customized "Alice"
    is_customized = Column(Boolean, default=False, nullable=False)
    speaking_time_seconds = Column(Float, default=0.0, nullable=False)
    speaking_percentage = Column(Float, default=0.0, nullable=False)
    turn_count = Column(Integer, default=0, nullable=False)
    avg_turn_seconds = Column(Float, default=0.0, nullable=False)
    estimated_tone = Column(String(64), nullable=True)  # Factual AI tone estimate

    meeting = relationship("Meeting", back_populates="speakers")
    transcript_segments = relationship("TranscriptSegment", back_populates="speaker")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    speaker_id = Column(Integer, ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True)
    speaker_label = Column(String(128), nullable=False, default="Unknown Speaker")
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    language = Column(String(16), default="en", nullable=True)

    meeting = relationship("Meeting", back_populates="transcript_segments")
    speaker = relationship("Speaker", back_populates="transcript_segments")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="QUEUED", nullable=False)
    progress_percent = Column(Float, default=0.0, nullable=False)
    current_step = Column(String(100), default="Queued", nullable=False)
    error_message = Column(Text, nullable=True)
    logs = Column(JSON, default=list, nullable=False)  # list of log messages
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="processing_jobs")


class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    executive_summary = Column(Text, nullable=False)
    agenda_topics = Column(JSON, default=list, nullable=False)
    overall_sentiment_estimate = Column(String(128), nullable=True)
    sentiment_justification = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="summary")


class KeyPoint(Base):
    __tablename__ = "key_points"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    point = Column(Text, nullable=False)
    category = Column(String(100), default="General", nullable=False)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="key_points")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    decision = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="decisions")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String(128), default="Unassigned", nullable=False)
    deadline = Column(String(128), nullable=True)
    priority = Column(String(32), default="Medium", nullable=False)  # Low, Medium, High, Urgent
    is_completed = Column(Boolean, default=False, nullable=False)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="action_items")


class ImportantDate(Base):
    __tablename__ = "important_dates"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    raw_phrase = Column(String(255), nullable=False)
    normalized_date = Column(String(128), nullable=True)
    description = Column(Text, nullable=False)
    needs_confirmation = Column(Boolean, default=False, nullable=False)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="important_dates")


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    event_title = Column(String(255), nullable=False)
    date_phrase = Column(String(255), nullable=False)
    normalized_datetime = Column(String(128), nullable=True)
    participants = Column(JSON, default=list, nullable=False)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="scheduled_events")


class Takeaway(Base):
    __tablename__ = "takeaways"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    takeaway = Column(Text, nullable=False)
    category = Column(String(100), default="General", nullable=False)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="takeaways")


class UnresolvedQuestion(Base):
    __tablename__ = "unresolved_questions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    raised_by = Column(String(128), default="Unknown", nullable=False)
    context = Column(Text, nullable=True)
    source_segment_ids = Column(JSON, default=list, nullable=False)
    source_text = Column(Text, nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting", back_populates="unresolved_questions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)  # "user", "assistant"
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list, nullable=False)  # list of {start_time, end_time, timestamp_str, text, speaker}
    created_at = Column(DateTime, default=utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="chat_messages")
