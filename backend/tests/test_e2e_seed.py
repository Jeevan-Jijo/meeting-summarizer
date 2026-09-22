import json
from pathlib import Path
import pytest
from app.core.database import SessionLocal, Base, engine
from app.models.db_models import (
    Meeting, Recording, Speaker, TranscriptSegment, MeetingSummary,
    KeyPoint, Decision, ActionItem, ImportantDate, ScheduledEvent, Takeaway, UnresolvedQuestion, utcnow
)
from app.services.vector_store import MeetingVectorStore, SimpleFallbackEmbedder
from app.services import vector_store as vs_module
from app.services.chunker import chunk_transcript
from app.services.export_service import generate_markdown_mom, generate_json_mom, generate_pdf_mom
from app.schemas.meeting import MeetingDetail

def test_seed_sample_meeting_and_exports(monkeypatch):
    # Use deterministic local fallback embedder for ultra-fast unit test execution
    monkeypatch.setattr(vs_module, "get_embedder", lambda: SimpleFallbackEmbedder(384))

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    sample_path = Path("sample_data/sample_meeting.json")
    if not sample_path.exists():
        sample_path = Path(__file__).parent.parent.parent / "sample_data" / "sample_meeting.json"

    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check if exists or create
    existing = db.query(Meeting).filter(Meeting.title == data["title"]).first()
    if existing:
        db.delete(existing)
        db.commit()

    meeting = Meeting(
        title=data["title"],
        description="Sprint planning & architecture meeting for local AI pipeline.",
        meeting_date=utcnow(),
        duration_seconds=data["duration_seconds"],
        status="COMPLETED"
    )
    db.add(meeting)
    db.flush()

    # Speakers
    speaker_map = {}
    for s in data["speakers"]:
        spk = Speaker(
            meeting_id=meeting.id,
            speaker_tag=s["id"],
            display_name=s["custom_name"],
            is_customized=True,
            speaking_time_seconds=90.0,
            speaking_percentage=33.3,
            turn_count=3,
            avg_turn_seconds=30.0,
            estimated_tone="Constructive & Directive"
        )
        db.add(spk)
        db.flush()
        speaker_map[s["id"]] = spk

    # Transcript Segments
    seg_dicts = []
    for seg in data["transcript"]:
        spk = speaker_map.get(seg["speaker_id"])
        ts = TranscriptSegment(
            meeting_id=meeting.id,
            speaker_id=spk.id if spk else None,
            speaker_label=seg["speaker_label"],
            start_time=seg["start_time"],
            end_time=seg["end_time"],
            raw_text=seg["text"],
            cleaned_text=seg["text"],
            confidence=0.98,
            language="en"
        )
        db.add(ts)
        db.flush()
        seg_dicts.append({
            "id": ts.id,
            "start": ts.start_time,
            "end": ts.end_time,
            "speaker_label": ts.speaker_label,
            "cleaned_text": ts.cleaned_text
        })

    # Extractions
    db.add(MeetingSummary(
        meeting_id=meeting.id,
        executive_summary="The team locked in the local-first inference architecture for MIS, agreeing to run faster-whisper, pyannote, and Ollama sequentially on RTX 4060 GPUs.",
        agenda_topics=["Local Pipeline Architecture", "GPU VRAM Management", "Release Milestones"],
        overall_sentiment_estimate="Highly constructive and aligned",
        sentiment_justification="Decisive technical alignment with clear assignment of deliverables."
    ))

    db.add(Decision(
        meeting_id=meeting.id,
        decision="Execute Whisper STT and Ollama LLM sequentially in the worker pipeline.",
        context="Keeps peak VRAM usage under 6 GB on 8 GB laptop GPUs.",
        impact="Prevents CUDA out-of-memory errors on consumer laptops.",
        source_segment_ids=[4],
        source_text="Let's officially decide to sequence heavy GPU operations in our background worker.",
        start_time=77.5,
        end_time=105.0,
        confidence=0.99
    ))

    db.add(ActionItem(
        meeting_id=meeting.id,
        description="Document worker queue architecture specs in docs/architecture.md",
        assignee="Marcus Vance",
        deadline="Friday, September 18th",
        priority="High",
        is_completed=False,
        source_segment_ids=[4, 5],
        source_text="I will wrap up the worker queue architecture documentation and commit it to docs/architecture.md by Friday, September 18th.",
        start_time=105.5,
        end_time=120.0,
        confidence=0.98
    ))

    db.add(ImportantDate(
        meeting_id=meeting.id,
        raw_phrase="Friday, September 18th",
        normalized_date="2026-09-18",
        description="Architecture documentation commit milestone",
        needs_confirmation=False,
        source_segment_ids=[5],
        start_time=105.5,
        end_time=120.0,
        confidence=0.98
    ))

    db.commit()
    db.refresh(meeting)

    # Build Vector Index
    chunks = chunk_transcript(seg_dicts, target_words_per_chunk=100, overlap_words=20)
    vstore = MeetingVectorStore(meeting.id)
    vstore.build_index(chunks)

    # Verify Vector Search
    search_res = vstore.search("architecture", top_k=2)
    assert len(search_res) > 0

    # Verify Exports
    meeting_dict = MeetingDetail.model_validate(meeting).model_dump()
    md_output = generate_markdown_mom(meeting_dict)
    assert "Minutes of Meeting" in md_output
    assert "Marcus Vance" in md_output

    json_output = generate_json_mom(meeting_dict)
    assert "Q3 MIS Architecture" in json_output

    pdf_bytes = generate_pdf_mom(meeting_dict)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    db.close()
