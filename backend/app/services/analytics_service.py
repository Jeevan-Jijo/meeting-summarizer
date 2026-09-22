from typing import List, Dict, Any
from app.schemas.analysis import SentimentReport

def compute_participation_metrics(
    transcript_segments: List[Dict[str, Any]],
    total_meeting_duration: float
) -> Dict[str, Any]:
    """
    Compute factual participation statistics from aligned transcript segments.
    """
    if not transcript_segments:
        return {
            "total_speech_seconds": 0.0,
            "total_meeting_seconds": total_meeting_duration,
            "speaker_metrics": [],
            "silence_seconds": total_meeting_duration,
            "silence_percentage": 100.0
        }

    speaker_times = {}
    speaker_turns = {}
    speaker_labels = {}
    speaker_custom_names = {}
    last_speaker = None

    for seg in transcript_segments:
        tag = seg.get("speaker_tag", "SPEAKER_00")
        label = seg.get("speaker_label", "Unknown Speaker")
        start = seg.get("start_time", seg.get("start", 0.0))
        end = seg.get("end_time", seg.get("end", 0.0))
        dur = max(0.01, end - start)

        speaker_times[tag] = speaker_times.get(tag, 0.0) + dur
        speaker_labels[tag] = label

        if tag != last_speaker:
            speaker_turns[tag] = speaker_turns.get(tag, 0) + 1
            last_speaker = tag

    total_speech = sum(speaker_times.values())
    total_dur = max(total_meeting_duration, total_speech)
    silence = max(0.0, total_dur - total_speech)

    metrics = []
    for tag, time_sec in speaker_times.items():
        turns = max(1, speaker_turns.get(tag, 1))
        percentage = round((time_sec / max(0.01, total_speech)) * 100.0, 1)
        meeting_percentage = round((time_sec / max(0.01, total_dur)) * 100.0, 1)
        avg_turn = round(time_sec / turns, 2)

        metrics.append({
            "speaker_tag": tag,
            "speaker_label": speaker_labels.get(tag, tag),
            "speaking_time_seconds": round(time_sec, 2),
            "percentage_of_speech": percentage,
            "percentage_of_meeting": meeting_percentage,
            "turn_count": turns,
            "avg_turn_length_seconds": avg_turn
        })

    metrics.sort(key=lambda x: x["speaking_time_seconds"], reverse=True)

    return {
        "total_speech_seconds": round(total_speech, 2),
        "total_meeting_seconds": round(total_dur, 2),
        "silence_seconds": round(silence, 2),
        "silence_percentage": round((silence / max(0.01, total_dur)) * 100.0, 1),
        "speaker_metrics": metrics
    }
