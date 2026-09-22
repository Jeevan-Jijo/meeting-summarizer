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
    Meeting, Recording, Speaker, TranscriptSegment, ProcessingJob,
    MeetingSummary, KeyPoint, Decision, ActionItem, ImportantDate,
    ScheduledEvent, Takeaway, UnresolvedQuestion, utcnow
)
from app.services.audio_processor import normalize_audio
from app.services.transcriber import Transcriber
from app.services.diarizer import Diarizer
from app.services.aligner import align_transcript_with_speakers
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
    Main background pipeline execution covering all states sequentially.
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

        # Step 2: TRANSCRIBING (faster-whisper)
        await update_job_status(db, job_id, "TRANSCRIBING", 25.0, "Transcribing with faster-whisper", "Transcribing audio segments...")
        transcriber = Transcriber()
        try:
            raw_segments, detected_language = await asyncio.to_thread(transcriber.transcribe, normalized_wav_path)
        finally:
            transcriber.unload()

        if not raw_segments:
            logger.warning(f"No speech detected for meeting {meeting_id}. Creating empty placeholder.")
            raw_segments = [{
                "start": 0.0,
                "end": max(1.0, duration),
                "text": "[No audible speech detected in recording]",
                "confidence": 0.5
            }]
            detected_language = "en"

        # Step 3: DIARIZING (pyannote.audio)
        await update_job_status(db, job_id, "DIARIZING", 45.0, "Speaker Diarization", "Detecting speaker turns...")
        diarizer = Diarizer()
        try:
            speaker_turns, is_real, diar_msg = await asyncio.to_thread(diarizer.diarize, normalized_wav_path)
            await update_job_status(db, job_id, "DIARIZING", 50.0, "Speaker Diarization", diar_msg)
        finally:
            diarizer.unload()

        # Step 4: ALIGNING (Segment + Speaker matching)
        await update_job_status(db, job_id, "ALIGNING", 55.0, "Aligning transcript & speakers", "Assigning speaker tags to transcript segments...")
        aligned_segs, speaker_stats = align_transcript_with_speakers(raw_segments, speaker_turns)

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
        for seg in aligned_segs:
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

        # Step 5: CHUNKING
        await update_job_status(db, job_id, "CHUNKING", 65.0, "Semantic Chunking", "Creating metadata-preserving semantic chunks...")
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
        chunks = chunk_transcript(seg_dicts, target_words_per_chunk=350, overlap_words=40)

        # Step 6: ANALYZING (Ollama LLM structured extractions)
        await update_job_status(db, job_id, "ANALYZING", 75.0, "LLM Extraction via Ollama", "Extracting summary, decisions, action items, dates...")
        llm = LLMService()
        meeting_date_str = meeting.meeting_date.strftime("%Y-%m-%d")
        
        # Analyze chunks
        chunk_results = []
        for chk in chunks:
            res = await llm.analyze_chunk(chk, meeting.title, meeting_date_str)
            if res:
                chunk_results.append(res)

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
                        deadline=act.deadline if is_valid_content(act.deadline) else None,
                        priority=act.priority or "Medium",
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
                        raised_by=q.raised_by if is_valid_content(q.raised_by) else "Speaker",
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
        await asyncio.to_thread(vstore.build_index, chunks)

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
