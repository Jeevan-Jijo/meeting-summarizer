import pytest
from app.schemas.analysis import ImportantDateExtraction

def test_date_ambiguity_flag():
    # Ambiguous relative date needs confirmation
    dt_ambiguous = ImportantDateExtraction(
        raw_phrase="sometime next month",
        description="Target beta release",
        needs_confirmation=True,
        confidence=0.8
    )
    assert dt_ambiguous.needs_confirmation is True
    assert dt_ambiguous.normalized_date is None

    # Specific date does not require confirmation
    dt_explicit = ImportantDateExtraction(
        raw_phrase="October 1st, 2026",
        normalized_date="2026-10-01",
        description="Internal alpha milestone",
        needs_confirmation=False,
        confidence=0.99
    )
    assert dt_explicit.needs_confirmation is False
    assert dt_explicit.normalized_date == "2026-10-01"
