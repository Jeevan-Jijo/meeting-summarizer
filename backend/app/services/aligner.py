import re
from typing import List, Dict, Any, Tuple
from app.core.logging import logger

def align_transcript_with_speakers(
    transcript_segments: List[Dict[str, Any]],
    speaker_turns: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Assign each transcript segment to the speaker with the maximum temporal overlap.
    
    Returns:
    - aligned_segments: List of segment dicts with 'speaker_tag' and 'speaker_label'
    - speaker_stats: Dict of speaker_tag -> {display_name, speaking_time, turns, avg_turn, percentage}
    """
    if not transcript_segments:
        return [], {}

    # If no speaker turns from diarization, assign single Unknown Speaker or turn fallback
    if not speaker_turns:
        aligned_segments = []
        for i, seg in enumerate(transcript_segments):
            seg_copy = dict(seg)
            seg_copy["speaker_tag"] = "SPEAKER_00"
            seg_copy["speaker_label"] = "Unknown Speaker"
            aligned_segments.append(seg_copy)

        total_time = sum(s["end"] - s["start"] for s in transcript_segments)
        speaker_stats = {
            "SPEAKER_00": {
                "speaker_tag": "SPEAKER_00",
                "display_name": "Unknown Speaker",
                "speaking_time_seconds": round(total_time, 2),
                "speaking_percentage": 100.0,
                "turn_count": len(transcript_segments),
                "avg_turn_seconds": round(total_time / max(1, len(transcript_segments)), 2)
            }
        }
        return aligned_segments, speaker_stats

    # Map raw speaker tags (e.g. "SPEAKER_00", "SPEAKER_01") to user friendly "Speaker 1", "Speaker 2"
    unique_speakers = sorted(list(set(t["speaker"] for t in speaker_turns)))
    speaker_tag_to_label = {}
    for idx, tag in enumerate(unique_speakers):
        speaker_tag_to_label[tag] = f"Speaker {idx + 1}"

    aligned_segments = []
    speaker_durations = {tag: 0.0 for tag in unique_speakers}
    speaker_turns_count = {tag: 0 for tag in unique_speakers}
    last_speaker_tag = None

    for seg in transcript_segments:
        s_start = seg["start"]
        s_end = seg["end"]
        s_dur = max(0.01, s_end - s_start)

        # Compute overlap with each speaker turn
        best_speaker = None
        max_overlap = -1.0

        for turn in speaker_turns:
            overlap = max(0.0, min(s_end, turn["end"]) - max(s_start, turn["start"]))
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = turn["speaker"]

        # If no positive overlap, pick nearest turn
        if max_overlap <= 0.0:
            best_dist = float("inf")
            for turn in speaker_turns:
                mid_turn = (turn["start"] + turn["end"]) / 2.0
                mid_seg = (s_start + s_end) / 2.0
                dist = abs(mid_turn - mid_seg)
                if dist < best_dist:
                    best_dist = dist
                    best_speaker = turn["speaker"]

        if best_speaker is None and unique_speakers:
            best_speaker = unique_speakers[0]
        elif best_speaker is None:
            best_speaker = "SPEAKER_00"

        speaker_tag_to_label.setdefault(best_speaker, f"Speaker {len(speaker_tag_to_label) + 1}")
        speaker_label = speaker_tag_to_label[best_speaker]

        speaker_durations[best_speaker] = speaker_durations.get(best_speaker, 0.0) + s_dur
        if best_speaker != last_speaker_tag:
            speaker_turns_count[best_speaker] = speaker_turns_count.get(best_speaker, 0) + 1
            last_speaker_tag = best_speaker

        seg_copy = dict(seg)
        seg_copy["speaker_tag"] = best_speaker
        seg_copy["speaker_label"] = speaker_label
        # Clean text basic normalization
        seg_copy["cleaned_text"] = re.sub(r'\s+', ' ', seg["text"]).strip()
        aligned_segments.append(seg_copy)

    total_speech_time = sum(speaker_durations.values())
    if total_speech_time <= 0:
        total_speech_time = 1.0

    speaker_stats = {}
    for tag, duration in speaker_durations.items():
        turns = max(1, speaker_turns_count.get(tag, 1))
        percentage = round((duration / total_speech_time) * 100.0, 1)
        speaker_stats[tag] = {
            "speaker_tag": tag,
            "display_name": speaker_tag_to_label.get(tag, tag),
            "speaking_time_seconds": round(duration, 2),
            "speaking_percentage": percentage,
            "turn_count": turns,
            "avg_turn_seconds": round(duration / turns, 2)
        }

    return aligned_segments, speaker_stats
