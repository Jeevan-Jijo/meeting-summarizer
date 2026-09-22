import pytest
from app.services.analytics_service import compute_participation_metrics

def test_participation_metrics():
    segments = [
        {"speaker_tag": "SPEAKER_00", "speaker_label": "Speaker 1", "start_time": 0.0, "end_time": 30.0},
        {"speaker_tag": "SPEAKER_01", "speaker_label": "Speaker 2", "start_time": 30.0, "end_time": 60.0},
        {"speaker_tag": "SPEAKER_00", "speaker_label": "Speaker 1", "start_time": 60.0, "end_time": 90.0}
    ]

    metrics = compute_participation_metrics(segments, total_meeting_duration=100.0)

    assert metrics["total_speech_seconds"] == 90.0
    assert metrics["total_meeting_seconds"] == 100.0
    assert metrics["silence_seconds"] == 10.0
    assert len(metrics["speaker_metrics"]) == 2

    # Speaker 00 spoke for 60s out of 90s speech = 66.7%
    spk0 = next(m for m in metrics["speaker_metrics"] if m["speaker_tag"] == "SPEAKER_00")
    assert spk0["speaking_time_seconds"] == 60.0
    assert spk0["turn_count"] == 2
    assert spk0["percentage_of_speech"] == pytest.approx(66.7, 0.1)
