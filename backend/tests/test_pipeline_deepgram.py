import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.database import SessionLocal, Base, engine
from app.models.db_models import (
    Meeting, Recording, Speaker, TranscriptSegment, ProcessingJob,
    MeetingSummary, KeyPoint, Decision, ActionItem, ImportantDate,
    ScheduledEvent, Takeaway, UnresolvedQuestion, utcnow
)
from app.services.pipeline_worker import process_meeting_pipeline, compute_speaker_stats_from_segments
from app.services import vector_store as vs_module
from app.services.vector_store import SimpleFallbackEmbedder

@pytest.fixture(autouse=True)
def setup_db_and_mocks(monkeypatch):
    """Setup SQLite database schema and fast fallback embedder before each test."""
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(vs_module, "get_embedder", lambda: SimpleFallbackEmbedder(384))
    yield
    db = SessionLocal()
    db.query(ProcessingJob).delete()
    db.query(TranscriptSegment).delete()
    db.query(Speaker).delete()
    db.query(MeetingSummary).delete()
    db.query(Recording).delete()
    db.query(Meeting).delete()
    db.commit()
    db.close()


def test_compute_speaker_stats_from_segments():
    segments = [
        {"start": 0.0, "end": 4.0, "text": "Hello world", "speaker_tag": "SPEAKER_00", "speaker_label": "Speaker 1"},
        {"start": 4.0, "end": 10.0, "text": "Hi Marcus", "speaker_tag": "SPEAKER_01", "speaker_label": "Speaker 2"},
        {"start": 10.0, "end": 16.0, "text": "Let's review", "speaker_tag": "SPEAKER_00", "speaker_label": "Speaker 1"},
    ]
    stats = compute_speaker_stats_from_segments(segments)
    assert "SPEAKER_00" in stats
    assert "SPEAKER_01" in stats
    assert stats["SPEAKER_00"]["turn_count"] == 2
    assert stats["SPEAKER_01"]["turn_count"] == 1
    assert stats["SPEAKER_00"]["speaking_time_seconds"] == 10.0
    assert stats["SPEAKER_01"]["speaking_time_seconds"] == 6.0


@pytest.mark.anyio
async def test_pipeline_deepgram_successful_flow(tmp_path):
    """Test full pipeline execution calling DeepgramService and saving transcript & speakers to DB."""
    fake_audio = tmp_path / "test_recording.mp4"
    fake_audio.write_bytes(b"fake video/audio data")

    db = SessionLocal()
    meeting = Meeting(title="Deepgram Test Meeting", status="QUEUED")
    db.add(meeting)
    db.flush()

    recording = Recording(
        meeting_id=meeting.id,
        original_filename="test_recording.mp4",
        file_path=str(fake_audio),
        mime_type="video/mp4",
        file_size_bytes=100
    )
    db.add(recording)

    job = ProcessingJob(meeting_id=meeting.id, status="QUEUED")
    db.add(job)
    db.commit()
    meeting_id = meeting.id
    job_id = job.id
    db.close()

    # Mock normalize_audio
    mock_normalize = patch("app.services.pipeline_worker.normalize_audio", return_value=(True, "OK", 30.0))

    # Mock DeepgramService
    mock_deepgram_instance = MagicMock()
    mock_deepgram_instance.is_configured.return_value = True
    mock_deepgram_instance.transcribe_file.return_value = (
        [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "Welcome to our Deepgram integration review.",
                "speaker_tag": "SPEAKER_00",
                "speaker_label": "Speaker 1",
                "confidence": 0.98
            },
            {
                "start": 5.5,
                "end": 12.0,
                "text": "Deepgram Cloud STT provides fast diarization.",
                "speaker_tag": "SPEAKER_01",
                "speaker_label": "Speaker 2",
                "confidence": 0.95
            }
        ],
        "en"
    )
    mock_deepgram_cls = patch("app.services.pipeline_worker.DeepgramService", return_value=mock_deepgram_instance)

    # Mock LLMService to avoid calling Ollama server during automated tests
    mock_llm_instance = MagicMock()
    async def fake_analyze_chunk(*args, **kwargs):
        return MagicMock()
    mock_llm_instance.analyze_chunk = fake_analyze_chunk

    mock_analysis_result = MagicMock()
    mock_analysis_result.executive_summary = "Deepgram STT integration completed successfully."
    mock_analysis_result.agenda_topics = ["Deepgram Integration", "Testing"]
    mock_analysis_result.discussion_topics = []
    mock_analysis_result.minutes_of_meeting = None
    mock_analysis_result.sentiment = None
    mock_analysis_result.key_points = []
    mock_analysis_result.decisions = []
    mock_analysis_result.action_items = []
    mock_analysis_result.important_dates = []
    mock_analysis_result.scheduled_events = []
    mock_analysis_result.takeaways = []
    mock_analysis_result.unresolved_questions = []

    async def fake_synthesize(*args, **kwargs):
        return mock_analysis_result
    mock_llm_instance.synthesize_analysis = fake_synthesize
    mock_llm_cls = patch("app.services.pipeline_worker.LLMService", return_value=mock_llm_instance)

    with mock_normalize, mock_deepgram_cls, mock_llm_cls:
        await process_meeting_pipeline(meeting_id, job_id)

    db = SessionLocal()
    updated_meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert updated_meeting.status == "COMPLETED"

    speakers = db.query(Speaker).filter(Speaker.meeting_id == meeting_id).all()
    assert len(speakers) == 2

    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).all()
    assert len(segments) == 2
    assert segments[0].speaker_label == "Speaker 1"
    assert segments[1].speaker_label == "Speaker 2"
    assert "Deepgram integration review" in segments[0].cleaned_text

    completed_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    assert completed_job.status == "COMPLETED"
    assert completed_job.progress_percent == 100.0
    db.close()


@pytest.mark.anyio
async def test_pipeline_deepgram_missing_api_key(tmp_path):
    """Test pipeline failure when Deepgram API key is missing."""
    fake_audio = tmp_path / "test_recording.wav"
    fake_audio.write_bytes(b"audio bytes")

    db = SessionLocal()
    meeting = Meeting(title="Unconfigured Deepgram", status="QUEUED")
    db.add(meeting)
    db.flush()

    recording = Recording(
        meeting_id=meeting.id,
        original_filename="test_recording.wav",
        file_path=str(fake_audio)
    )
    db.add(recording)

    job = ProcessingJob(meeting_id=meeting.id, status="QUEUED")
    db.add(job)
    db.commit()
    meeting_id = meeting.id
    job_id = job.id
    db.close()

    mock_normalize = patch("app.services.pipeline_worker.normalize_audio", return_value=(True, "OK", 10.0))
    mock_deepgram_instance = MagicMock()
    mock_deepgram_instance.is_configured.return_value = False
    mock_deepgram_cls = patch("app.services.pipeline_worker.DeepgramService", return_value=mock_deepgram_instance)

    with mock_normalize, mock_deepgram_cls:
        await process_meeting_pipeline(meeting_id, job_id)

    db = SessionLocal()
    failed_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    assert failed_job.status == "FAILED"
    assert "DEEPGRAM_API_KEY is missing or unconfigured" in failed_job.error_message
    db.close()


@pytest.mark.anyio
async def test_pipeline_deepgram_api_error_handling(tmp_path):
    """Test handling of Deepgram API errors (e.g. 401 Unauthorized)."""
    fake_audio = tmp_path / "test_recording.wav"
    fake_audio.write_bytes(b"audio bytes")

    db = SessionLocal()
    meeting = Meeting(title="Deepgram Error", status="QUEUED")
    db.add(meeting)
    db.flush()

    recording = Recording(
        meeting_id=meeting.id,
        original_filename="test_recording.wav",
        file_path=str(fake_audio)
    )
    db.add(recording)

    job = ProcessingJob(meeting_id=meeting.id, status="QUEUED")
    db.add(job)
    db.commit()
    meeting_id = meeting.id
    job_id = job.id
    db.close()

    mock_normalize = patch("app.services.pipeline_worker.normalize_audio", return_value=(True, "OK", 10.0))
    mock_deepgram_instance = MagicMock()
    mock_deepgram_instance.is_configured.return_value = True
    mock_deepgram_instance.transcribe_file.side_effect = ValueError("Deepgram API authentication failed: Invalid or expired DEEPGRAM_API_KEY.")
    mock_deepgram_cls = patch("app.services.pipeline_worker.DeepgramService", return_value=mock_deepgram_instance)

    with mock_normalize, mock_deepgram_cls:
        await process_meeting_pipeline(meeting_id, job_id)

    db = SessionLocal()
    failed_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    assert failed_job.status == "FAILED"
    assert "authentication failed" in failed_job.error_message.lower()
    db.close()


@pytest.mark.anyio
async def test_pipeline_deepgram_retry_skips_stt_when_transcript_exists(tmp_path):
    """Test retry behavior: if transcript segments exist in DB, pipeline skips Deepgram STT call."""
    db = SessionLocal()
    meeting = Meeting(title="Retry Meeting", status="QUEUED")
    db.add(meeting)
    db.flush()

    spk = Speaker(meeting_id=meeting.id, speaker_tag="SPEAKER_00", display_name="Speaker 1")
    db.add(spk)
    db.flush()

    seg = TranscriptSegment(
        meeting_id=meeting.id,
        speaker_id=spk.id,
        speaker_label="Speaker 1",
        start_time=0.0,
        end_time=5.0,
        raw_text="Already transcribed text.",
        cleaned_text="Already transcribed text.",
        confidence=0.99
    )
    db.add(seg)

    job = ProcessingJob(meeting_id=meeting.id, status="QUEUED")
    db.add(job)
    db.commit()
    meeting_id = meeting.id
    job_id = job.id
    db.close()

    mock_deepgram_instance = MagicMock()
    mock_deepgram_cls = patch("app.services.pipeline_worker.DeepgramService", return_value=mock_deepgram_instance)

    mock_llm_instance = MagicMock()
    async def fake_analyze(*args, **kwargs):
        return MagicMock()
    mock_llm_instance.analyze_chunk = fake_analyze

    mock_analysis_result = MagicMock()
    mock_analysis_result.executive_summary = "Retry summary"
    mock_analysis_result.agenda_topics = []
    mock_analysis_result.discussion_topics = []
    mock_analysis_result.minutes_of_meeting = None
    mock_analysis_result.sentiment = None
    mock_analysis_result.key_points = []
    mock_analysis_result.decisions = []
    mock_analysis_result.action_items = []
    mock_analysis_result.important_dates = []
    mock_analysis_result.scheduled_events = []
    mock_analysis_result.takeaways = []
    mock_analysis_result.unresolved_questions = []

    async def fake_synth(*args, **kwargs):
        return mock_analysis_result
    mock_llm_instance.synthesize_analysis = fake_synth
    mock_llm_cls = patch("app.services.pipeline_worker.LLMService", return_value=mock_llm_instance)

    with mock_deepgram_cls, mock_llm_cls:
        await process_meeting_pipeline(meeting_id, job_id)

    # Verify Deepgram transcribe_file was NOT called because transcript already exists
    assert not mock_deepgram_instance.transcribe_file.called

    db = SessionLocal()
    completed_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    assert completed_job.status == "COMPLETED"
    db.close()
