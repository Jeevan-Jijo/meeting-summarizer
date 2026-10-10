from typing import List, Optional, Any
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
    made_by: Optional[str] = Field(default=None, description="Person or speaker label who made/confirmed the decision")

class ActionItemExtraction(BaseEvidenceItem):
    description: str = Field(..., description="Actionable task to be done")
    assignee: str = Field(default="Unassigned", description="Name or speaker label of the person responsible")
    deadline: Optional[str] = Field(default=None, description="Stated deadline or timeframe")
    priority: str = Field(default="Medium", description="High, Medium, or Low")
    domain: str = Field(default="Other", description="Backend, Frontend, Database, AI/ML, DevOps, Testing, Documentation, Product, Management, Marketing, Finance, Research, Metrics, Other")
    status: str = Field(default="Pending", description="Pending, In Progress, or Completed")

class ImportantDateExtraction(BaseEvidenceItem):
    raw_phrase: str = Field(..., description="Verbatim date phrase spoken")
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
    question: str = Field(..., description="Open question, dilemma, or item raised")
    answer: Optional[str] = Field(default=None, description="Answer from the transcript if present, or null if unanswered")
    status: str = Field(default="Unanswered", description="Answered, Partially Answered, or Unanswered")
    raised_by: str = Field(default="Unknown", description="Speaker who posed the question")
    context: Optional[str] = Field(default=None, description="Context or blockers related to the question")

class DiscussionTopicItem(BaseModel):
    title: str = Field(..., description="Topic title")
    summary: str = Field(..., description="Short 1-2 sentence third-person summary")
    timestamp: Optional[str] = Field(default=None, description="Time range or timestamp reference")

class MinutesOfMeeting(BaseModel):
    overview: str = Field(default="", description="Meeting overview")
    agenda: List[str] = Field(default_factory=list, description="Agenda items")
    discussion: List[str] = Field(default_factory=list, description="Discussion summary points")
    decisions: List[str] = Field(default_factory=list, description="Decisions list")
    action_items: List[str] = Field(default_factory=list, description="Action items list")
    open_questions: List[str] = Field(default_factory=list, description="Open questions list")
    takeaways: List[str] = Field(default_factory=list, description="Key takeaways list")

class SpeakerSentimentMetric(BaseModel):
    speaker_label: str
    estimated_tone: str = Field(..., description="e.g. 'Constructive', 'Neutral', 'Inquisitive'")
    observation: str = Field(..., description="Brief factual AI estimate note")

class SentimentReport(BaseModel):
    overall_sentiment_estimate: str = Field(..., description="Overall tone e.g. 'Collaborative and productive'")
    justification: str = Field(..., description="Contextual explanation based strictly on spoken transcript evidence")
    speaker_estimates: List[SpeakerSentimentMetric] = Field(default_factory=list)

from pydantic import BaseModel, Field, field_validator

class MeetingAnalysis(BaseModel):
    executive_summary: str = Field(..., description="Comprehensive 2-4 paragraph executive summary of the meeting")
    agenda_topics: List[str] = Field(default_factory=list, description="Main topics or agenda items discussed")
    discussion_topics: List[DiscussionTopicItem] = Field(default_factory=list)
    minutes_of_meeting: Optional[MinutesOfMeeting] = None
    key_points: List[KeyPointExtraction] = Field(default_factory=list)
    decisions: List[DecisionExtraction] = Field(default_factory=list)
    action_items: List[ActionItemExtraction] = Field(default_factory=list)
    important_dates: List[ImportantDateExtraction] = Field(default_factory=list)
    scheduled_events: List[ScheduledEventExtraction] = Field(default_factory=list)
    takeaways: List[TakeawayExtraction] = Field(default_factory=list)
    unresolved_questions: List[UnresolvedQuestionExtraction] = Field(default_factory=list)
    sentiment: Optional[SentimentReport] = None

    @field_validator('takeaways', mode='before')
    @classmethod
    def parse_takeaways(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"takeaway": item, "category": "General"})
                else:
                    res.append(item)
            return res
        return v

    @field_validator('key_points', mode='before')
    @classmethod
    def parse_key_points(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"point": item, "category": "General"})
                else:
                    res.append(item)
            return res
        return v

    @field_validator('important_dates', mode='before')
    @classmethod
    def parse_important_dates(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"raw_phrase": item, "description": item})
                elif isinstance(item, dict):
                    if "raw_phrase" not in item:
                        item["raw_phrase"] = item.get("date") or item.get("phrase") or "Date"
                    if "description" not in item:
                        item["description"] = item.get("raw_phrase") or "Milestone date"
                    res.append(item)
                else:
                    res.append(item)
            return res
        return v

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

    @field_validator('takeaways', mode='before')
    @classmethod
    def parse_takeaways(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"takeaway": item, "category": "General"})
                else:
                    res.append(item)
            return res
        return v

    @field_validator('key_points', mode='before')
    @classmethod
    def parse_key_points(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"point": item, "category": "General"})
                else:
                    res.append(item)
            return res
        return v

    @field_validator('important_dates', mode='before')
    @classmethod
    def parse_important_dates(cls, v):
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"raw_phrase": item, "description": item})
                elif isinstance(item, dict):
                    if "raw_phrase" not in item:
                        item["raw_phrase"] = item.get("date") or item.get("phrase") or "Date"
                    if "description" not in item:
                        item["description"] = item.get("raw_phrase") or "Milestone date"
                    res.append(item)
                else:
                    res.append(item)
            return res
        return v
