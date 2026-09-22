import pytest
from app.services.aligner import align_transcript_with_speakers

def test_alignment_with_speaker_turns():
    transcript_segments = [
        {"start": 0.0, "end": 10.0, "text": "Good morning everyone."},
        {"start": 10.5, "end": 20.0, "text": "Thanks, glad to be here."},
        {"start": 20.5, "end": 35.0, "text": "Let's review the architecture."}
    ]

    speaker_turns = [
        {"start": 0.0, "end": 10.2, "speaker": "SPEAKER_00"},
        {"start": 10.3, "end": 20.1, "speaker": "SPEAKER_01"},
        {"start": 20.2, "end": 35.0, "speaker": "SPEAKER_00"}
    ]

    aligned, stats = align_transcript_with_speakers(transcript_segments, speaker_turns)

    assert len(aligned) == 3
    assert aligned[0]["speaker_tag"] == "SPEAKER_00"
    assert aligned[0]["speaker_label"] == "Speaker 1"
    assert aligned[1]["speaker_tag"] == "SPEAKER_01"
    assert aligned[1]["speaker_label"] == "Speaker 2"
    assert aligned[2]["speaker_tag"] == "SPEAKER_00"

    assert "SPEAKER_00" in stats
    assert "SPEAKER_01" in stats
    assert stats["SPEAKER_00"]["turn_count"] == 2
    assert stats["SPEAKER_01"]["turn_count"] == 1

def test_alignment_graceful_fallback_no_turns():
    transcript_segments = [
        {"start": 0.0, "end": 15.0, "text": "This is a single speaker monologue."}
    ]
    aligned, stats = align_transcript_with_speakers(transcript_segments, [])

    assert len(aligned) == 1
    assert aligned[0]["speaker_label"] == "Unknown Speaker"
    assert "SPEAKER_00" in stats
    assert stats["SPEAKER_00"]["speaking_percentage"] == 100.0
