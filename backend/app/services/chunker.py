from typing import List, Dict, Any
from app.services.audio_processor import format_timestamp
from app.core.config import settings
from app.core.logging import logger

class TranscriptChunk:
    def __init__(
        self,
        chunk_index: int,
        start_time: float,
        end_time: float,
        segment_ids: List[int],
        formatted_text: str,
        word_count: int
    ):
        self.chunk_index = chunk_index
        self.start_time = start_time
        self.end_time = end_time
        self.segment_ids = segment_ids
        self.formatted_text = formatted_text
        self.word_count = word_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_index": self.chunk_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_timestamp": format_timestamp(self.start_time),
            "end_timestamp": format_timestamp(self.end_time),
            "segment_ids": self.segment_ids,
            "formatted_text": self.formatted_text,
            "word_count": self.word_count
        }

def chunk_transcript(
    segments: List[Dict[str, Any]],
    target_words_per_chunk: int = 400,
    overlap_words: int = 50
) -> List[TranscriptChunk]:
    """
    Split transcript segments into semantic chunks.
    Preserves speaker labels, segment IDs, and timestamps.
    Avoids cutting mid-sentence.
    """
    if not segments:
        return []

    chunks: List[TranscriptChunk] = []
    current_segments = []
    current_word_count = 0
    chunk_index = 0

    i = 0
    while i < len(segments):
        seg = segments[i]
        text = seg.get("cleaned_text") or seg.get("text", "")
        speaker = seg.get("speaker_label", "Unknown")
        seg_id = seg.get("id") or seg.get("segment_id", i + 1)
        words = len(text.split())

        current_segments.append({
            "id": seg_id,
            "start": seg["start"],
            "end": seg["end"],
            "speaker": speaker,
            "text": text,
            "words": words
        })
        current_word_count += words

        # If current chunk has enough words or this is the last segment
        if current_word_count >= target_words_per_chunk or i == len(segments) - 1:
            # Build formatted text
            formatted_lines = []
            for s in current_segments:
                ts = format_timestamp(s["start"])
                formatted_lines.append(f"[{ts}] {s['speaker']}: {s['text']}")
            
            chunk_text = "\n".join(formatted_lines)
            chunk_start = current_segments[0]["start"]
            chunk_end = current_segments[-1]["end"]
            seg_ids = [s["id"] for s in current_segments]

            chunks.append(TranscriptChunk(
                chunk_index=chunk_index,
                start_time=chunk_start,
                end_time=chunk_end,
                segment_ids=seg_ids,
                formatted_text=chunk_text,
                word_count=current_word_count
            ))
            chunk_index += 1

            # Compute overlap for next chunk if not at end
            if i < len(segments) - 1:
                overlap_segments = []
                overlap_count = 0
                for s in reversed(current_segments):
                    overlap_segments.insert(0, s)
                    overlap_count += s["words"]
                    if overlap_count >= overlap_words:
                        break
                current_segments = list(overlap_segments)
                current_word_count = sum(s["words"] for s in current_segments)
            else:
                current_segments = []
                current_word_count = 0

        i += 1

    logger.info(f"Chunked transcript into {len(chunks)} chunks.")
    return chunks
