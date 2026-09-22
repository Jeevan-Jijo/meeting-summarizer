import pytest
from app.services.chunker import chunk_transcript

def test_chunking_preserves_metadata():
    segments = [
        {"id": 1, "start": 0.0, "end": 10.0, "speaker_label": "Alex", "cleaned_text": "This is segment one containing ten words for our test case."},
        {"id": 2, "start": 10.5, "end": 20.0, "speaker_label": "Sarah", "cleaned_text": "This is segment two continuing the discussion with more details."},
        {"id": 3, "start": 20.5, "end": 30.0, "speaker_label": "Marcus", "cleaned_text": "This is segment three finishing up the test chunking pipeline."}
    ]

    # Target small words to force chunks
    chunks = chunk_transcript(segments, target_words_per_chunk=15, overlap_words=5)

    assert len(chunks) >= 2
    first_chunk = chunks[0]
    assert 1 in first_chunk.segment_ids
    assert first_chunk.start_time == 0.0
    assert "[00:00:00] Alex:" in first_chunk.formatted_text

def test_empty_chunking():
    chunks = chunk_transcript([])
    assert chunks == []
