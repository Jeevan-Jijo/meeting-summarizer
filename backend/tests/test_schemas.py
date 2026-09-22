import pytest
from pydantic import ValidationError
from app.schemas.analysis import (
    KeyPointExtraction, DecisionExtraction, ActionItemExtraction,
    ImportantDateExtraction, ScheduledEventExtraction, TakeawayExtraction,
    UnresolvedQuestionExtraction, MeetingAnalysis, SentimentReport
)

def test_key_point_validation():
    kp = KeyPointExtraction(
        point="Adopt sequential GPU pipeline execution",
        category="Architecture",
        source_segment_ids=[1, 2],
        source_text="Let's run Whisper and LLM sequentially.",
        start_time=12.0,
        end_time=24.5,
        confidence=0.98
    )
    assert kp.point == "Adopt sequential GPU pipeline execution"
    assert kp.confidence == 0.98
    assert kp.source_segment_ids == [1, 2]

def test_action_item_defaults():
    ai = ActionItemExtraction(
        description="Update architecture.md specs",
        assignee="Marcus",
        deadline="Friday, September 18th",
        priority="High"
    )
    assert ai.assignee == "Marcus"
    assert ai.priority == "High"
    assert ai.confidence == 1.0

def test_confidence_bounds():
    with pytest.raises(ValidationError):
        KeyPointExtraction(point="Invalid confidence", confidence=1.5)

    with pytest.raises(ValidationError):
        KeyPointExtraction(point="Invalid confidence negative", confidence=-0.1)

def test_meeting_analysis_synthesis():
    analysis = MeetingAnalysis(
        executive_summary="Executive summary for the team sync.",
        agenda_topics=["Architecture", "Milestones"],
        key_points=[KeyPointExtraction(point="Key point 1")],
        decisions=[DecisionExtraction(decision="Decision 1")],
        action_items=[ActionItemExtraction(description="Action 1", assignee="Alex")],
        important_dates=[ImportantDateExtraction(raw_phrase="Next Tuesday", description="Design review", needs_confirmation=True)],
        scheduled_events=[ScheduledEventExtraction(event_title="Review", date_phrase="Tuesday 10 AM")],
        takeaways=[TakeawayExtraction(takeaway="Takeaway 1")],
        unresolved_questions=[UnresolvedQuestionExtraction(question="Question 1", raised_by="Sarah")]
    )
    assert len(analysis.key_points) == 1
    assert analysis.important_dates[0].needs_confirmation is True
