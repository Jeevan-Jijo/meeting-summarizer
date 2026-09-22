from typing import List, Optional
from pydantic import BaseModel, Field

class BaseEvidenceItem(BaseModel):
    source_segment_ids: List[int] = Field(default_factory=list, description="IDs of source transcript segments")
    source_text: str = Field(default="", description="Exact or near-exact transcript excerpt providing evidence")
    start_time: float = Field(default=0.0, description="Start timestamp in seconds")
    end_time: float = Field(default=0.0, description="End timestamp in seconds")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

class KeyPointExtraction(BaseEvidenceItem):
    point: str = Field(..., description="Concise key point statement")
    category: str = Field(default="General", description="Category e.g., Architecture, Product, Operations, Budget")

class DecisionExtraction(BaseEvidenceItem):
    decision: str = Field(..., description="The concrete decision reached by participants")
    context: Optional[str] = Field(default=None, description="Why this decision was made or alternative options considered")
    impact: Optional[str] = Field(default=None, description="Scope or impact of the decision")

class ActionItemExtraction(BaseEvidenceItem):
    description: str = Field(..., description="Actionable task to be done")
    assignee: str = Field(default="Unassigned", description="Name or speaker label of the person responsible. Never invent a person.")
    deadline: Optional[str] = Field(default=None, description="Stated deadline or timeframe. Do not invent.")
    priority: str = Field(default="Medium", description="Low, Medium, High, or Urgent")

class ImportantDateExtraction(BaseEvidenceItem):
    raw_phrase: str = Field(..., description="Verbatim date phrase spoken (e.g. 'next Tuesday', 'September 22nd')")
    normalized_date: Optional[str] = Field(default=None, description="ISO or normalized date e.g. '2026-09-22'")
    description: str = Field(..., description="Event or milestone associated with this date")
    needs_confirmation: bool = Field(default=False, description="Set to true if ambiguous or unspecified year/day")

class ScheduledEventExtraction(BaseEvidenceItem):
    event_title: str = Field(..., description="Title of the meeting or event scheduled")
    date_phrase: str = Field(..., description="Spoken date phrase for the event")
    normalized_datetime: Optional[str] = Field(default=None, description="Normalized date/time if resolvable")
    participants: List[str] = Field(default_factory=list, description="Participants expected to attend")

class TakeawayExtraction(BaseEvidenceItem):
    takeaway: str = Field(..., description="High-level strategic takeaway or insight")
    category: str = Field(default="General", description="Topic category")

class UnresolvedQuestionExtraction(BaseEvidenceItem):
    question: str = Field(..., description="Open question, dilemma, or unresolved item raised")
    raised_by: str = Field(default="Unknown", description="Speaker who posed the question")
    context: Optional[str] = Field(default=None, description="Context or blockers related to the question")

class SpeakerSentimentMetric(BaseModel):
    speaker_label: str
    estimated_tone: str = Field(..., description="e.g. 'Constructive', 'Neutral', 'Inquisitive', 'Cautious'")
    observation: str = Field(..., description="Brief factual AI estimate note. Not a performance rating.")

class SentimentReport(BaseModel):
    overall_sentiment_estimate: str = Field(..., description="Overall tone e.g. 'Collaborative and productive'")
    justification: str = Field(..., description="Contextual explanation based strictly on spoken transcript evidence")
    speaker_estimates: List[SpeakerSentimentMetric] = Field(default_factory=list)

class MeetingAnalysis(BaseModel):
    executive_summary: str = Field(..., description="Comprehensive 2-4 paragraph executive summary of the meeting")
    agenda_topics: List[str] = Field(default_factory=list, description="Main topics or agenda items discussed")
    key_points: List[KeyPointExtraction] = Field(default_factory=list)
    decisions: List[DecisionExtraction] = Field(default_factory=list)
    action_items: List[ActionItemExtraction] = Field(default_factory=list)
    important_dates: List[ImportantDateExtraction] = Field(default_factory=list)
    scheduled_events: List[ScheduledEventExtraction] = Field(default_factory=list)
    takeaways: List[TakeawayExtraction] = Field(default_factory=list)
    unresolved_questions: List[UnresolvedQuestionExtraction] = Field(default_factory=list)
    sentiment: Optional[SentimentReport] = None

class ChunkAnalysis(BaseModel):
    chunk_index: int
    partial_summary: str = Field(..., description="Summary of this transcript chunk")
    key_points: List[KeyPointExtraction] = Field(default_factory=list)
    decisions: List[DecisionExtraction] = Field(default_factory=list)
    action_items: List[ActionItemExtraction] = Field(default_factory=list)
    important_dates: List[ImportantDateExtraction] = Field(default_factory=list)
    scheduled_events: List[ScheduledEventExtraction] = Field(default_factory=list)
    takeaways: List[TakeawayExtraction] = Field(default_factory=list)
    unresolved_questions: List[UnresolvedQuestionExtraction] = Field(default_factory=list)
