import asyncio
import datetime
import os
import traceback
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import (
    Meeting, Recording, Speaker, TranscriptSegment, TranscriptChunkModel, ProcessingJob,
    MeetingSummary, KeyPoint, Decision, ActionItem, ImportantDate,
    ScheduledEvent, Takeaway, UnresolvedQuestion, utcnow
)
from app.services.audio_processor import normalize_audio
from app.services.deepgram_service import DeepgramService
from app.services.chunker import chunk_transcript
from app.services.llm_service import LLMService
from app.services.vector_store import MeetingVectorStore

def is_valid_content(text: Optional[str]) -> bool:
    """Filter out non-informative boilerplate text from extractions."""
    if not text:
        return False
    t = text.strip().lower()
    if t in ["none", "n/a", "null", "none.", "none specified", "no deadline specified.", "no description provided.", "unknown"]:
        return False
    if any(t.startswith(prefix) for prefix in [
        "no decision", "no action item", "no important date", "no question", "no takeaway", "no event", "no date"
    ]):
        return False
    return len(t) > 2


def compute_speaker_stats_from_segments(segments: list) -> dict:
    """
    Compute speaker statistics directly from Deepgram diarized segments/utterances.
    """
    if not segments:
        return {}

    speaker_durations = {}
    speaker_turns_count = {}
    speaker_labels = {}
    last_speaker_tag = None

    for seg in segments:
        spk_tag = seg.get("speaker_tag", "SPEAKER_00")
        spk_label = seg.get("speaker_label", "Speaker 1")
        s_start = float(seg.get("start", 0.0))
        s_end = float(seg.get("end", s_start + 1.0))
        dur = max(0.01, s_end - s_start)

        speaker_durations[spk_tag] = speaker_durations.get(spk_tag, 0.0) + dur
        speaker_labels[spk_tag] = spk_label

        if spk_tag != last_speaker_tag:
            speaker_turns_count[spk_tag] = speaker_turns_count.get(spk_tag, 0) + 1
            last_speaker_tag = spk_tag

    total_speech_time = sum(speaker_durations.values())
    if total_speech_time <= 0:
        total_speech_time = 1.0

    speaker_stats = {}
    for tag, duration in speaker_durations.items():
        turns = max(1, speaker_turns_count.get(tag, 1))
        percentage = round((duration / total_speech_time) * 100.0, 1)
        speaker_stats[tag] = {
            "speaker_tag": tag,
            "display_name": speaker_labels.get(tag, tag),
            "speaking_time_seconds": round(duration, 2),
            "speaking_percentage": percentage,
            "turn_count": turns,
            "avg_turn_seconds": round(duration / turns, 2)
        }

    return speaker_stats


async def update_job_status(
    db: Session,
    job_id: int,
    status: str,
    progress: float,
    step_name: str,
    log_msg: Optional[str] = None,
    error_msg: Optional[str] = None
):
    """Update job state, progress percentage, and log history in SQLite."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        return

    job.status = status
    job.progress_percent = round(progress, 1)
    job.current_step = step_name
    
    if log_msg:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        curr_logs = list(job.logs) if job.logs else []
        curr_logs.append(f"[{timestamp}] [{status}] {log_msg}")
        job.logs = curr_logs
        logger.info(f"[Job {job_id}] [{status}] {log_msg}")

    if error_msg:
        job.error_message = error_msg
        job.status = "FAILED"

    if status in ("COMPLETED", "FAILED"):
        job.completed_at = utcnow()

    # Also sync meeting status
    meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
    if meeting:
        meeting.status = status

    db.commit()
    db.refresh(job)


async def process_meeting_pipeline(meeting_id: int, job_id: int):
    """
    Main background pipeline execution covering all states sequentially with Deepgram cloud STT.
    """
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not meeting or not job:
            logger.error(f"Meeting {meeting_id} or Job {job_id} not found in DB.")
            return

        job.started_at = utcnow()
        db.commit()

        # Check existing transcript segments for retry optimization
        existing_segments = db.query(TranscriptSegment).filter(
            TranscriptSegment.meeting_id == meeting_id
        ).order_by(TranscriptSegment.start_time).all()

        if existing_segments:
            await update_job_status(
                db, job_id, "TRANSCRIBING", 50.0,
                "Using existing transcript",
                f"Found {len(existing_segments)} existing transcript segments for meeting {meeting_id}. Skipping STT step."
            )
            created_segs = existing_segments
            existing_speakers = db.query(Speaker).filter(Speaker.meeting_id == meeting_id).all()
            created_speakers = {s.speaker_tag: s for s in existing_speakers}
        else:
            # Step 1: PREPROCESSING (FFmpeg)
            await update_job_status(db, job_id, "PREPROCESSING", 10.0, "Normalizing audio with FFmpeg", "Starting FFmpeg audio normalization...")
            recording = meeting.recording
            if not recording:
                raise ValueError("No recording associated with meeting.")

            raw_audio_path = recording.file_path
            normalized_wav_path = str(settings.PROCESSED_DIR / f"meeting_{meeting_id}_norm.wav")
            
            success, msg, duration = await normalize_audio(raw_audio_path, normalized_wav_path)
            if not success:
                raise RuntimeError(f"Audio normalization failed: {msg}")

            recording.normalized_path = normalized_wav_path
            recording.duration_seconds = duration
            meeting.duration_seconds = duration
            db.commit()

            # Step 2: TRANSCRIBING & DIARIZING (Deepgram Service)
            await update_job_status(
                db, job_id, "TRANSCRIBING", 30.0,
                "Transcribing & Diarizing with Deepgram",
                "Sending normalized recording to Deepgram Cloud STT (Nova-2 model)..."
            )

            deepgram_service = DeepgramService()
            if not deepgram_service.is_configured():
                raise ValueError(
                    "DEEPGRAM_API_KEY is missing or unconfigured. Please configure DEEPGRAM_API_KEY in backend/.env"
                )

            raw_segments, detected_language = await asyncio.to_thread(
                deepgram_service.transcribe_file, normalized_wav_path
            )

            await update_job_status(
                db, job_id, "TRANSCRIBING", 50.0,
                "Processing Deepgram transcript & speakers",
                f"Deepgram returned {len(raw_segments)} segments in language '{detected_language}'."
            )

            # Calculate speaker stats directly from Deepgram utterances
            speaker_stats = compute_speaker_stats_from_segments(raw_segments)

            # Clear existing speakers & segments if re-running
            db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).delete()
            db.query(Speaker).filter(Speaker.meeting_id == meeting_id).delete()
            db.commit()

            # Create Speaker DB records
            created_speakers = {}
            for spk_tag, s_data in speaker_stats.items():
                spk_obj = Speaker(
                    meeting_id=meeting_id,
                    speaker_tag=spk_tag,
                    display_name=s_data["display_name"],
                    is_customized=False,
                    speaking_time_seconds=s_data["speaking_time_seconds"],
                    speaking_percentage=s_data["speaking_percentage"],
                    turn_count=s_data["turn_count"],
                    avg_turn_seconds=s_data["avg_turn_seconds"]
                )
                db.add(spk_obj)
                db.flush()
                created_speakers[spk_tag] = spk_obj

            # Create TranscriptSegment DB records
            created_segs = []
            for seg in raw_segments:
                spk_tag = seg.get("speaker_tag", "SPEAKER_00")
                spk_obj = created_speakers.get(spk_tag)
                
                t_seg = TranscriptSegment(
                    meeting_id=meeting_id,
                    speaker_id=spk_obj.id if spk_obj else None,
                    speaker_label=spk_obj.display_name if spk_obj else seg.get("speaker_label", "Speaker"),
                    start_time=seg["start"],
                    end_time=seg["end"],
                    raw_text=seg["text"],
                    cleaned_text=seg.get("cleaned_text", seg["text"]),
                    confidence=seg.get("confidence", 1.0),
                    language=detected_language
                )
                db.add(t_seg)
                created_segs.append(t_seg)

            db.commit()

        # Step 5: CHUNKING & PERSISTENCE
        await update_job_status(db, job_id, "CHUNKING", 65.0, "Semantic Chunking", "Creating metadata-preserving semantic chunks...")
        
        # Check existing chunks in database for retry optimization
        existing_chunks = db.query(TranscriptChunkModel).filter(
            TranscriptChunkModel.meeting_id == meeting_id
        ).order_by(TranscriptChunkModel.chunk_index).all()

        if existing_chunks:
            logger.info(f"Reusing {len(existing_chunks)} existing database chunks for meeting {meeting_id}")
            created_chunks = existing_chunks
        else:
            seg_dicts = [
                {
                    "id": s.id,
                    "start": s.start_time,
                    "end": s.end_time,
                    "speaker_label": s.speaker_label,
                    "cleaned_text": s.cleaned_text
                }
                for s in created_segs
            ]
            raw_chunks = chunk_transcript(seg_dicts, target_words_per_chunk=350, overlap_words=40)
            
            # Clear old chunks for meeting
            db.query(TranscriptChunkModel).filter(TranscriptChunkModel.meeting_id == meeting_id).delete()
            db.commit()

            created_chunks = []
            for chk in raw_chunks:
                c_model = TranscriptChunkModel(
                    meeting_id=meeting_id,
                    chunk_index=chk.chunk_index,
                    start_time=chk.start_time,
                    end_time=chk.end_time,
                    segment_ids=chk.segment_ids,
                    formatted_text=chk.formatted_text,
                    word_count=chk.word_count
                )
                db.add(c_model)
                created_chunks.append(c_model)
            db.commit()

        # Step 6: ANALYZING (Ollama LLM structured extractions)
        await update_job_status(db, job_id, "ANALYZING", 75.0, "LLM Extraction via Ollama", "Extracting summary, decisions, action items, dates...")
        llm = LLMService()
        meeting_date_str = meeting.meeting_date.strftime("%Y-%m-%d")
        
        # Analyze chunks concurrently
        tasks = [llm.analyze_chunk(chk, meeting.title, meeting_date_str) for chk in created_chunks]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        chunk_results = [r for r in raw_results if r and not isinstance(r, Exception)]

        # Synthesize final document
        speaker_names = [s.display_name for s in created_speakers.values()]
        analysis = await llm.synthesize_analysis(chunk_results, meeting.title, meeting_date_str, speaker_names)

        # Clear existing extractions
        db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting_id).delete()
        db.query(KeyPoint).filter(KeyPoint.meeting_id == meeting_id).delete()
        db.query(Decision).filter(Decision.meeting_id == meeting_id).delete()
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
        db.query(ImportantDate).filter(ImportantDate.meeting_id == meeting_id).delete()
        db.query(ScheduledEvent).filter(ScheduledEvent.meeting_id == meeting_id).delete()
        db.query(Takeaway).filter(Takeaway.meeting_id == meeting_id).delete()
        db.query(UnresolvedQuestion).filter(UnresolvedQuestion.meeting_id == meeting_id).delete()

        # Save Summary
        if analysis:
            summary_record = MeetingSummary(
                meeting_id=meeting_id,
                executive_summary=analysis.executive_summary,
                agenda_topics=analysis.agenda_topics,
                discussion_topics=[t.model_dump() for t in analysis.discussion_topics] if analysis.discussion_topics else [],
                minutes_of_meeting=analysis.minutes_of_meeting.model_dump() if analysis.minutes_of_meeting else {},
                overall_sentiment_estimate=analysis.sentiment.overall_sentiment_estimate if analysis.sentiment else "Constructive",
                sentiment_justification=analysis.sentiment.justification if analysis.sentiment else None
            )
            db.add(summary_record)

            # Update speaker tones if returned in sentiment report
            if analysis.sentiment and analysis.sentiment.speaker_estimates:
                for est in analysis.sentiment.speaker_estimates:
                    for spk in created_speakers.values():
                        if spk.speaker_tag == est.speaker_label or spk.display_name == est.speaker_label:
                            spk.estimated_tone = f"{est.estimated_tone} ({est.observation})"

            # Save Key Points
            for kp in analysis.key_points:
                if is_valid_content(kp.point):
                    db.add(KeyPoint(
                        meeting_id=meeting_id,
                        point=kp.point,
                        category=kp.category,
                        source_segment_ids=kp.source_segment_ids,
                        source_text=kp.source_text,
                        start_time=kp.start_time,
                        end_time=kp.end_time,
                        confidence=kp.confidence
                    ))

            # Save Decisions
            for dec in analysis.decisions:
                if is_valid_content(dec.decision):
                    db.add(Decision(
                        meeting_id=meeting_id,
                        decision=dec.decision,
                        context=dec.context,
                        impact=dec.impact,
                        made_by=dec.made_by,
                        source_segment_ids=dec.source_segment_ids,
                        source_text=dec.source_text,
                        start_time=dec.start_time,
                        end_time=dec.end_time,
                        confidence=dec.confidence
                    ))

            # Save Action Items
            for act in analysis.action_items:
                if is_valid_content(act.description):
                    db.add(ActionItem(
                        meeting_id=meeting_id,
                        description=act.description,
                        assignee=act.assignee if is_valid_content(act.assignee) else "Unassigned",
                        deadline=act.deadline if is_valid_content(act.deadline) else "Not specified",
                        priority=act.priority or "Medium",
                        domain=act.domain or "Other",
                        status=act.status or "Pending",
                        is_completed=False,
                        source_segment_ids=act.source_segment_ids,
                        source_text=act.source_text,
                        start_time=act.start_time,
                        end_time=act.end_time,
                        confidence=act.confidence
                    ))

            # Save Dates
            for dt in analysis.important_dates:
                if is_valid_content(dt.raw_phrase):
                    db.add(ImportantDate(
                        meeting_id=meeting_id,
                        raw_phrase=dt.raw_phrase,
                        normalized_date=dt.normalized_date,
                        description=dt.description if is_valid_content(dt.description) else dt.raw_phrase,
                        needs_confirmation=dt.needs_confirmation,
                        source_segment_ids=dt.source_segment_ids,
                        source_text=dt.source_text,
                        start_time=dt.start_time,
                        end_time=dt.end_time,
                        confidence=dt.confidence
                    ))

            # Save Scheduled Events
            for ev in analysis.scheduled_events:
                if is_valid_content(ev.event_title):
                    db.add(ScheduledEvent(
                        meeting_id=meeting_id,
                        event_title=ev.event_title,
                        date_phrase=ev.date_phrase,
                        normalized_datetime=ev.normalized_datetime,
                        participants=ev.participants,
                        source_segment_ids=ev.source_segment_ids,
                        source_text=ev.source_text,
                        start_time=ev.start_time,
                        end_time=ev.end_time,
                        confidence=ev.confidence
                    ))

            # Save Takeaways
            for tk in analysis.takeaways:
                if is_valid_content(tk.takeaway):
                    db.add(Takeaway(
                        meeting_id=meeting_id,
                        takeaway=tk.takeaway,
                        category=tk.category,
                        source_segment_ids=tk.source_segment_ids,
                        source_text=tk.source_text,
                        start_time=tk.start_time,
                        end_time=tk.end_time,
                        confidence=tk.confidence
                    ))

            # Save Questions
            for q in analysis.unresolved_questions:
                if is_valid_content(q.question):
                    db.add(UnresolvedQuestion(
                        meeting_id=meeting_id,
                        question=q.question,
                        answer=q.answer if is_valid_content(q.answer) else "No answer was identified in the meeting.",
                        status=q.status if q.status else "Unanswered",
                        raised_by=q.raised_by if is_valid_content(q.raised_by) else "Speaker 00",
                        context=q.context if is_valid_content(q.context) else None,
                        source_segment_ids=q.source_segment_ids,
                        source_text=q.source_text,
                        start_time=q.start_time,
                        end_time=q.end_time,
                        confidence=q.confidence
                    ))

        db.commit()

        # Step 7: INDEXING (Local FAISS + sentence-transformers)
        await update_job_status(db, job_id, "INDEXING", 90.0, "Building vector index", "Indexing transcript embeddings for local RAG chatbot...")
        vstore = MeetingVectorStore(meeting_id)
        await asyncio.to_thread(vstore.build_index, created_chunks)

        # Step 8: FINALIZING
        await update_job_status(db, job_id, "FINALIZING", 98.0, "Finalizing meeting results", "Assembling meeting minutes...")
        await update_job_status(db, job_id, "COMPLETED", 100.0, "Complete", "Meeting Intelligence pipeline completed successfully!")

    except Exception as e:
        err_stack = traceback.format_exc()
        logger.error(f"Pipeline error for meeting {meeting_id}: {err_stack}")
        await update_job_status(
            db, job_id, "FAILED", 100.0, "Pipeline Failed",
            log_msg=f"Error: {str(e)}",
            error_msg=str(e)
        )
    finally:
        db.close()
