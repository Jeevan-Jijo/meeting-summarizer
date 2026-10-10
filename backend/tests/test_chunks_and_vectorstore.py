import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.database import SessionLocal, Base, engine
from app.core.config import settings
from app.models.db_models import (
    Meeting, Recording, Speaker, TranscriptSegment, TranscriptChunkModel,
    ProcessingJob, MeetingSummary, utcnow
)
from app.services.chunker import chunk_transcript, TranscriptChunk
from app.services.vector_store import MeetingVectorStore, SimpleFallbackEmbedder
from app.services import vector_store as vs_module

@pytest.fixture(autouse=True)
def setup_db_and_mocks(monkeypatch):
    """Setup SQLite database schema and fast fallback embedder before each test."""
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(vs_module, "get_embedder", lambda: SimpleFallbackEmbedder(384))
    yield
    db = SessionLocal()
    db.query(ProcessingJob).delete()
    db.query(TranscriptChunkModel).delete()
    db.query(TranscriptSegment).delete()
    db.query(Speaker).delete()
    db.query(MeetingSummary).delete()
    db.query(Recording).delete()
    db.query(Meeting).delete()
    db.commit()
    db.close()


def test_transcript_chunker_logic():
    segments = [
        {"id": 1, "start": 0.0, "end": 5.0, "speaker_label": "Speaker 1", "cleaned_text": "Hello world and welcome to the meeting."},
        {"id": 2, "start": 5.5, "end": 10.0, "speaker_label": "Speaker 2", "cleaned_text": "We are discussing the new vector store architecture today."}
    ]
    chunks = chunk_transcript(segments, target_words_per_chunk=10, overlap_words=2)
    assert len(chunks) >= 1
    assert chunks[0].start_time == 0.0
    assert chunks[0].segment_ids == [1, 2]
    assert "[00:00:00] Speaker 1: Hello world" in chunks[0].formatted_text


def test_chunk_persistence_in_database():
    """Verify storing TranscriptChunkModel records in SQLite and relationship mapping."""
    db = SessionLocal()
    meeting = Meeting(title="Persistence Test", status="COMPLETED")
    db.add(meeting)
    db.flush()

    c1 = TranscriptChunkModel(
        meeting_id=meeting.id,
        chunk_index=0,
        start_time=0.0,
        end_time=10.0,
        segment_ids=[1, 2],
        formatted_text="[00:00:00] Speaker 1: Hello world",
        word_count=5
    )
    c2 = TranscriptChunkModel(
        meeting_id=meeting.id,
        chunk_index=1,
        start_time=10.0,
        end_time=20.0,
        segment_ids=[3],
        formatted_text="[00:00:10] Speaker 2: Architecture updates",
        word_count=4
    )
    db.add_all([c1, c2])
    db.commit()

    saved_chunks = db.query(TranscriptChunkModel).filter(TranscriptChunkModel.meeting_id == meeting.id).all()
    assert len(saved_chunks) == 2
    assert saved_chunks[0].chunk_index == 0
    assert saved_chunks[1].chunk_index == 1
    assert saved_chunks[0].segment_ids == [1, 2]

    # Verify relationship from Meeting model
    m_reloaded = db.query(Meeting).filter(Meeting.id == meeting.id).first()
    assert len(m_reloaded.transcript_chunks) == 2
    db.close()


def test_meeting_deletion_cleans_chunks_and_vector_index(tmp_path, monkeypatch):
    """Verify deleting a meeting removes DB chunks and FAISS vector index files from disk."""
    # Use temporary vector directory for test isolation
    test_vec_dir = tmp_path / "vectors"
    monkeypatch.setattr(settings, "VECTOR_DIR", test_vec_dir)

    db = SessionLocal()
    meeting = Meeting(title="Deletion Test", status="COMPLETED")
    db.add(meeting)
    db.flush()

    c1 = TranscriptChunkModel(
        meeting_id=meeting.id,
        chunk_index=0,
        start_time=0.0,
        end_time=10.0,
        segment_ids=[1],
        formatted_text="Sample text for deletion test.",
        word_count=5
    )
    db.add(c1)
    db.commit()

    vstore = MeetingVectorStore(meeting.id)
    vstore.build_index([c1])
    assert vstore.index_dir.exists()
    assert vstore.index_file.exists()

    # Perform search
    res = vstore.search("deletion", top_k=1)
    assert len(res) == 1

    # Delete index explicitly
    vstore.delete_index()
    assert not vstore.index_dir.exists()

    # Cascade delete meeting from DB
    db.delete(meeting)
    db.commit()

    remaining_chunks = db.query(TranscriptChunkModel).filter(TranscriptChunkModel.meeting_id == meeting.id).all()
    assert len(remaining_chunks) == 0

    # Ensure search on deleted meeting returns empty list
    res_after = vstore.search("deletion", top_k=1)
    assert len(res_after) == 0
    db.close()


@pytest.mark.anyio
async def test_vector_store_qa_with_fallback(tmp_path, monkeypatch):
    """Test vector store search and RAG QA fallback behavior."""
    test_vec_dir = tmp_path / "vectors"
    monkeypatch.setattr(settings, "VECTOR_DIR", test_vec_dir)

    c1 = {
        "chunk_index": 0,
        "start_time": 15.0,
        "end_time": 30.0,
        "segment_ids": [10],
        "formatted_text": "[00:00:15] Speaker 1: We decided to deploy Deepgram for cloud ASR.",
        "word_count": 9
    }

    vstore = MeetingVectorStore(999)
    vstore.build_index([c1])

    search_res = vstore.search("Deepgram", top_k=1)
    assert len(search_res) == 1
    assert search_res[0]["start_time"] == 15.0

    # Test Q&A fallback when Ollama is unavailable
    answer, citations = await vstore.answer_question("What did we deploy?", "Test Meeting")
    assert len(citations) == 1
    assert citations[0].start_time == 15.0
    assert "00:00:15" in citations[0].timestamp_str
