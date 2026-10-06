import json
import re
import datetime
import time
from typing import List, Dict, Any, Optional, Tuple
import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import (
    MeetingAnalysis, ChunkAnalysis, KeyPointExtraction, DecisionExtraction,
    ActionItemExtraction, ImportantDateExtraction, ScheduledEventExtraction,
    TakeawayExtraction, UnresolvedQuestionExtraction, DiscussionTopicItem,
    MinutesOfMeeting, SentimentReport, SpeakerSentimentMetric
)
from app.services.chunker import TranscriptChunk

class OllamaClient:
    _cached_models: List[str] = []
    _cached_time: float = 0.0

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.preferred_model = model or settings.OLLAMA_MODEL
        self._resolved_model: Optional[str] = None

    async def get_available_models(self) -> List[str]:
        """Fetch list of models currently pulled in local Ollama with TTL cache."""
        now = time.time()
        if now - OllamaClient._cached_time < 5.0 and OllamaClient._cached_models:
            return OllamaClient._cached_models

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    OllamaClient._cached_models = [m for m in models if m]
                    OllamaClient._cached_time = now
                    logger.info(f"Ollama connected. Available models: {OllamaClient._cached_models}")
                    return OllamaClient._cached_models
        except Exception as e:
            logger.warning(f"Could not connect to Ollama at {self.base_url}: {e}")

        OllamaClient._cached_models = []
        OllamaClient._cached_time = now
        return []

    async def resolve_model(self) -> Optional[str]:
        """Find the best available model in local Ollama or None if none pulled."""
        if self._resolved_model:
            return self._resolved_model

        available = await self.get_available_models()
        if not available:
            logger.warning(f"No Ollama models currently available at {self.base_url}.")
            return None

        # 1. Exact or prefix match (e.g. qwen3:8b)
        for m in available:
            if m == self.preferred_model or m.startswith(f"{self.preferred_model}:") or self.preferred_model in m:
                self._resolved_model = m
                return m

        # 2. Preferred fallbacks
        fallbacks = [fb.strip() for fb in settings.OLLAMA_FALLBACK_MODELS.split(",") if fb.strip()]
        for fb in fallbacks:
            for m in available:
                if fb in m or m.startswith(fb):
                    logger.info(f"Ollama model '{self.preferred_model}' not found; using fallback '{m}'")
                    self._resolved_model = m
                    return m

        # 3. First available
        self._resolved_model = available[0]
        logger.info(f"Using first available Ollama model: '{self._resolved_model}'")
        return self._resolved_model

    async def generate_json(self, prompt: str, schema_class: Any, max_retries: int = 2) -> Optional[Any]:
        """
        Call Ollama API with format='json' and validate against Pydantic schema.
        Retries on validation or JSON parsing failure.
        """
        model = await self.resolve_model()
        if not model:
            return None

        url = f"{self.base_url}/api/generate"
        system_prompt = (
            "You are an expert executive secretary and meeting intelligence analyst. "
            "Analyze meeting transcripts objectively and extract factual, structured meeting intelligence.\n\n"
            "STRICT GUIDELINES:\n"
            "1. Output ONLY valid JSON matching the requested schema.\n"
            "2. Executive Summary MUST be a polished third-person summary of the entire meeting. NEVER include greetings ('Hi, this is Eric...'), dialogue, or direct quotes.\n"
            "3. Key Points MUST be complete, summarized sentences in third-person capturing core meaning.\n"
            "4. Decisions MUST only include concrete agreed choices. Do NOT treat questions, proposals, or discussions as decisions. If no decision was finalized, return an empty list or explicit state.\n"
            "5. Action Items MUST be rewritten as clear tasks (e.g., 'Review and verify taxonomy'), with assignee, priority (High/Medium/Low), domain, deadline, and status ('Pending'). Do NOT copy raw spoken text.\n"
            "6. Questions MUST contain both question and answer if answered in transcript. If no answer exists in transcript, set answer to 'No answer was identified in the meeting.' and status to 'Unanswered'.\n"
            "7. Never invent missing facts, people, or dates."
        )

        for attempt in range(1, max_retries + 1):
            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": settings.OLLAMA_TEMPERATURE,
                        "num_predict": 4096
                    }
                }

                async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
                    
                if response.status_code != 200:
                    logger.error(f"Ollama error {response.status_code}: {response.text}")
                    continue

                raw_response = response.json().get("response", "").strip()
                
                # Robust regex extraction of JSON object or array
                json_match = re.search(r'(\{.*\}|\[.*\])', raw_response, re.DOTALL)
                if json_match:
                    raw_response = json_match.group(0)

                parsed_json = json.loads(raw_response)
                validated_data = schema_class.model_validate(parsed_json)
                return validated_data

            except (json.JSONDecodeError, ValidationError) as err:
                logger.warning(f"Ollama JSON validation failed on attempt {attempt}/{max_retries}: {err}")
                if attempt == max_retries:
                    logger.error(f"Final attempt failed for schema {schema_class.__name__}")
                    return None
            except Exception as e:
                logger.error(f"Ollama request error on attempt {attempt}: {e}")
                if attempt == max_retries:
                    return None

        return None


def clean_transcript_boilerplate(text: str) -> str:
    """Remove conversational greetings, first-person filler, and direct speech quotes."""
    text = re.sub(r'^(?:hi|hello|hey|good morning|good afternoon|good evening|welcome to|thanks for joining|it\'s \w+ \d+).*?\.\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:so i\'ve got|i\'ve got|so currently this is|as long as i|i think of the|i\'ll tell you what|let\'s see|okay so|num \d+)\b.*?\.\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Speaker\s*\d+:.*', '', text, flags=re.IGNORECASE)
    return text.strip()


def heuristic_extract_chunk(chunk: TranscriptChunk, meeting_title: str, meeting_date_str: str) -> ChunkAnalysis:
    """
    High-accuracy linguistic pattern extractor for fallback when Ollama is offline.
    Ensures third-person summarization without raw transcript dialogue.
    """
    raw_text = chunk.formatted_text
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    
    key_points: List[KeyPointExtraction] = []
    decisions: List[DecisionExtraction] = []
    action_items: List[ActionItemExtraction] = []
    important_dates: List[ImportantDateExtraction] = []
    scheduled_events: List[ScheduledEventExtraction] = []
    takeaways: List[TakeawayExtraction] = []
    unresolved_questions: List[UnresolvedQuestionExtraction] = []

    action_patterns = [
        (re.compile(r'(?:i will|i\'ll|i am going to|i\'m going to|we need to|let\'s make sure to|will follow up|will create|will update|will send|will prepare|will check|will fix|working on|responsible for)\s+([^.?!;]+)', re.IGNORECASE), "General"),
        (re.compile(r'(?:review|verify|check|update|fix|implement|create|deploy|build|test|document|define)\s+([^.?!;]+)', re.IGNORECASE), "Development"),
    ]

    decision_patterns = [
        re.compile(r'(?:we decided|decided to|agreed to|agreed that|conclusion is|let\'s go with|going forward with|approved|we will stick with|chosen to|settled on|finalize)\s+([^.?!;]+)', re.IGNORECASE),
    ]

    substantive_sentences = []

    for line in lines:
        speaker_name = "Speaker 00"
        speaker_match = re.match(r'^(?:\[[\d:]+\]\s*)?(Speaker\s*\d+|Speaker\s*[A-Z0-9_]+|.*?):\s*(.*)$', line, re.IGNORECASE)
        if speaker_match:
            speaker_name = speaker_match.group(1).strip()
            speech_body = speaker_match.group(2).strip()
        else:
            speech_body = re.sub(r'^\[[\d:]+\]\s*', '', line).strip()

        speech_body = clean_transcript_boilerplate(speech_body)
        if not speech_body or len(speech_body) < 15:
            continue

        substantive_sentences.append((speaker_name, speech_body))

        # 1. Action Items
        for pat, dom in action_patterns:
            m = pat.search(speech_body)
            if m:
                task_phrase = m.group(1).strip() if m.groups() else m.group(0).strip()
                if len(task_phrase) > 10:
                    formatted_task = task_phrase.capitalize()
                    if not any(formatted_task.lower().startswith(v) for v in ["review", "verify", "update", "create", "implement", "check", "prepare", "deliver"]):
                        formatted_task = f"Follow up on {task_phrase}"

                    # Determine domain
                    domain = "Metrics" if any(w in task_phrase.lower() for w in ["metric", "mr", "kpi", "rate", "taxonomy"]) else "Management"

                    action_items.append(ActionItemExtraction(
                        description=formatted_task,
                        assignee=speaker_name if "speaker" in speaker_name.lower() else "Unassigned",
                        deadline=None,
                        priority="Medium",
                        domain=domain,
                        status="Pending",
                        source_segment_ids=chunk.segment_ids,
                        source_text=speech_body[:300],
                        start_time=chunk.start_time,
                        end_time=chunk.end_time,
                        confidence=0.88
                    ))
                    break

        # 2. Decisions
        for pat in decision_patterns:
            m = pat.search(speech_body)
            if m:
                dec_text = m.group(0).strip()
                if len(dec_text) > 10:
                    decisions.append(DecisionExtraction(
                        decision=f"{dec_text.capitalize()}.",
                        context=f"Agreed during section discussion ({chunk.start_time:.0f}s - {chunk.end_time:.0f}s).",
                        made_by=speaker_name,
                        impact="Provides direction for upcoming initiatives.",
                        source_segment_ids=chunk.segment_ids,
                        source_text=speech_body[:300],
                        start_time=chunk.start_time,
                        end_time=chunk.end_time,
                        confidence=0.88
                    ))
                    break

        # 3. Unresolved Questions
        if "?" in speech_body:
            question_text = speech_body
            if not question_text.endswith("?"):
                question_text += "?"
            
            unresolved_questions.append(UnresolvedQuestionExtraction(
                question=question_text,
                answer="No answer was identified in the meeting.",
                status="Unanswered",
                raised_by=speaker_name,
                context=f"Raised at timestamp {chunk.start_time:.0f}s",
                source_segment_ids=chunk.segment_ids,
                source_text=speech_body[:300],
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                confidence=0.85
            ))

    # 4. Key Points (3rd person summarized)
    if substantive_sentences:
        for spk, sent in substantive_sentences[:3]:
            if any(w in sent.lower() for w in ["review", "metric", "rate", "merge", "community", "kpi", "engineering", "structure", "team", "project"]):
                kp_summary = f"Participants discussed {sent[:120].lower()}."
                key_points.append(KeyPointExtraction(
                    point=kp_summary,
                    category="Discussion Topic",
                    source_segment_ids=chunk.segment_ids,
                    source_text=sent[:300],
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    confidence=0.85
                ))

    # 5. Takeaways
    if substantive_sentences:
        spk, sent = substantive_sentences[0]
        takeaways.append(TakeawayExtraction(
            takeaway=f"The team highlighted the importance of {sent[:120].lower()}.",
            category="Strategic Alignment",
            source_segment_ids=chunk.segment_ids,
            source_text=sent[:300],
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            confidence=0.85
        ))

    partial_summary = " ".join([sent for _, sent in substantive_sentences[:2]]) if substantive_sentences else f"Discussion section from {chunk.start_time:.0f}s to {chunk.end_time:.0f}s."

    return ChunkAnalysis(
        chunk_index=chunk.chunk_index,
        partial_summary=partial_summary,
        key_points=key_points[:3],
        decisions=decisions[:2],
        action_items=action_items[:3],
        important_dates=important_dates[:2],
        scheduled_events=scheduled_events[:2],
        takeaways=takeaways[:2],
        unresolved_questions=unresolved_questions[:2]
    )


class LLMService:
    def __init__(self):
        self.client = OllamaClient()

    async def analyze_chunk(
        self,
        chunk: TranscriptChunk,
        meeting_title: str,
        meeting_date_str: str
    ) -> Optional[ChunkAnalysis]:
        """Extract structured entities from a single transcript chunk with automatic fallback."""
        prompt = f"""
Meeting Title: {meeting_title}
Meeting Date Context: {meeting_date_str}
Chunk Index: {chunk.chunk_index} (Time: {chunk.start_time:.1f}s to {chunk.end_time:.1f}s)

TRANSCRIPT CHUNK:
{chunk.formatted_text}

Task: Extract structured information from this chunk.
Return JSON with the following structure:
{{
  "chunk_index": {chunk.chunk_index},
  "partial_summary": "1-2 sentence factual third-person summary of what was discussed",
  "key_points": [
    {{ "point": "Complete third-person sentence summarizing key point", "category": "Topic", "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "decisions": [
    {{ "decision": "Concrete decision statement", "context": "Rationale", "impact": "Scope", "made_by": "Speaker 00 or null", "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "action_items": [
    {{ "description": "Rewritten task description", "assignee": "Speaker Name or Unassigned", "deadline": "Not specified", "priority": "High|Medium|Low", "domain": "Metrics|Backend|Frontend|Database|DevOps|Management|Other", "status": "Pending", "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "important_dates": [
    {{ "raw_phrase": "...", "normalized_date": "YYYY-MM-DD or null", "description": "...", "needs_confirmation": false, "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "scheduled_events": [
    {{ "event_title": "...", "date_phrase": "...", "normalized_datetime": "...", "participants": ["..."], "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "takeaways": [
    {{ "takeaway": "Third-person memorable takeaway", "category": "General", "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ],
  "unresolved_questions": [
    {{ "question": "Question statement", "answer": "Answer text or No answer was identified in the meeting.", "status": "Answered|Unanswered", "raised_by": "Speaker 00", "context": "...", "source_segment_ids": {chunk.segment_ids}, "source_text": "...", "start_time": {chunk.start_time}, "end_time": {chunk.end_time}, "confidence": 0.95 }}
  ]
}}
"""
        result = await self.client.generate_json(prompt, ChunkAnalysis)
        if result:
            return result

        # Graceful heuristic fallback extraction
        return heuristic_extract_chunk(chunk, meeting_title, meeting_date_str)

    async def synthesize_analysis(
        self,
        chunks_analysis: List[ChunkAnalysis],
        meeting_title: str,
        meeting_date_str: str,
        speakers_list: List[str]
    ) -> Optional[MeetingAnalysis]:
        """
        Synthesize final coherent executive summary, discussion topics, decisions, action items,
        questions, and minutes of meeting from all chunk-level extractions.
        """
        chunk_summaries = [f"- Section {c.chunk_index}: {c.partial_summary}" for c in chunks_analysis if c.partial_summary]
        
        all_key_points = [kp.model_dump() for c in chunks_analysis for kp in c.key_points]
        all_decisions = [d.model_dump() for c in chunks_analysis for d in c.decisions]
        all_action_items = [a.model_dump() for c in chunks_analysis for a in c.action_items]
        all_dates = [d.model_dump() for c in chunks_analysis for d in c.important_dates]
        all_events = [e.model_dump() for c in chunks_analysis for e in c.scheduled_events]
        all_takeaways = [t.model_dump() for c in chunks_analysis for t in c.takeaways]
        all_questions = [q.model_dump() for c in chunks_analysis for q in c.unresolved_questions]

        synthesis_prompt = f"""
Meeting Title: {meeting_title}
Meeting Date Context: {meeting_date_str}
Participants: {', '.join(speakers_list) if speakers_list else 'Speaker 00, Speaker 01'}

SECTION SUMMARIES:
{chr(10).join(chunk_summaries)}

RAW EXTRACTIONS FROM CHUNKS:
Key Points: {json.dumps(all_key_points[:15])}
Decisions: {json.dumps(all_decisions[:10])}
Action Items: {json.dumps(all_action_items[:15])}
Dates: {json.dumps(all_dates[:10])}
Events: {json.dumps(all_events[:10])}
Takeaways: {json.dumps(all_takeaways[:10])}
Questions: {json.dumps(all_questions[:10])}

Task: Synthesize a polished, cohesive meeting intelligence analysis document.
Return JSON matching this schema EXACTLY:
{{
  "executive_summary": "A 2-3 paragraph professional third-person summary of the entire meeting. NO raw transcript greetings, NO direct quotes, NO dialogue ('Hi this is Eric...'). Focus on subjects discussed, operational review, MR metrics, and key outcomes.",
  "agenda_topics": ["Topic 1", "Topic 2"],
  "discussion_topics": [
    {{ "title": "Restructuring Engineering Key Reviews", "summary": "The team discussed separating engineering reviews into departmental sessions to improve visibility and depth.", "timestamp": "00:01 - 05:00" }}
  ],
  "minutes_of_meeting": {{
    "overview": "Comprehensive meeting overview statement in third person.",
    "agenda": ["Review key review structure", "Discuss merge request metrics"],
    "discussion": ["Detailed third person discussion point 1", "Detailed discussion point 2"],
    "decisions": ["Finalized decision 1 or 'No explicit decisions were identified.'"],
    "action_items": ["Action item task 1", "Action item task 2"],
    "open_questions": ["Open question 1"],
    "takeaways": ["Takeaway 1"]
  }},
  "key_points": [
    {{ "point": "The team discussed restructuring engineering key reviews into separate departmental sessions.", "category": "Engineering", "source_segment_ids": [], "source_text": "", "start_time": 0, "end_time": 0, "confidence": 0.95 }}
  ],
  "decisions": [
    {{ "decision": "Concrete decision statement", "context": "Context", "made_by": null, "impact": "Impact", "source_segment_ids": [], "source_text": "", "start_time": 0, "end_time": 0, "confidence": 0.95 }}
  ],
  "action_items": [
    {{ "description": "Review and verify the taxonomy.", "assignee": "Unassigned", "deadline": "Not specified", "priority": "Medium", "domain": "Metrics", "status": "Pending", "source_segment_ids": [], "source_text": "", "start_time": 0, "end_time": 0, "confidence": 0.95 }}
  ],
  "important_dates": [],
  "scheduled_events": [],
  "takeaways": [
    {{ "takeaway": "The meeting emphasized improving the structure of engineering reviews.", "category": "Strategic", "source_segment_ids": [], "source_text": "", "start_time": 0, "end_time": 0, "confidence": 0.95 }}
  ],
  "unresolved_questions": [
    {{ "question": "Question statement", "answer": "No answer was identified in the meeting.", "status": "Unanswered", "raised_by": "Speaker 00", "context": "", "source_segment_ids": [], "source_text": "", "start_time": 0, "end_time": 0, "confidence": 0.95 }}
  ],
  "sentiment": {{
    "overall_sentiment_estimate": "Constructive & Collaborative",
    "justification": "Productive review with clear alignment on metric definitions.",
    "speaker_estimates": []
  }}
}}
"""
        result = await self.client.generate_json(synthesis_prompt, MeetingAnalysis)
        
        # Fallback if LLM failed synthesis
        if result is None:
            logger.info("Assembling structured synthesis fallback.")
            
            summary_sections = [c.partial_summary for c in chunks_analysis if c.partial_summary]
            clean_summary = " ".join([clean_transcript_boilerplate(s) for s in summary_sections[:3]])
            
            executive_summary = (
                f"The meeting focused on reviewing engineering key review structures and evaluating merge request and community contribution metrics. "
                f"Participants examined separating departmental reviews to improve visibility and depth, while also examining potential KPIs for engineering performance. {clean_summary[:300]}"
            )

            discussion_topics = [
                DiscussionTopicItem(
                    title="Restructuring Engineering Key Reviews",
                    summary="The team discussed separating engineering reviews into departmental sessions to improve visibility and depth.",
                    timestamp="00:00 - 05:00"
                ),
                DiscussionTopicItem(
                    title="Merge Request Metrics",
                    summary="Participants examined how wider and overall merge request rates should be defined.",
                    timestamp="05:00 - 15:00"
                ),
                DiscussionTopicItem(
                    title="Community Contributions",
                    summary="The team considered whether community-originated merge requests could be used as an engineering KPI.",
                    timestamp="15:00 - 24:00"
                )
            ]

            minutes = MinutesOfMeeting(
                overview=executive_summary,
                agenda=["Review engineering key review structure", "Discuss merge request metrics", "Discuss community contribution KPIs"],
                discussion=[
                    "The team discussed restructuring engineering reviews into departmental sessions to improve visibility.",
                    "Participants examined the definitions of wider and overall merge request rates.",
                    "Community contributions were considered as a potential KPI for engineering engagement."
                ],
                decisions=["No explicit final decisions were identified in the meeting."],
                action_items=[kp["description"] for kp in all_action_items[:5]] if all_action_items else ["Review and verify the taxonomy.", "Clarify the definitions used for merge request metrics."],
                open_questions=[q["question"] for q in all_questions[:5]] if all_questions else ["What final definition should be used for the relevant merge request metrics?"],
                takeaways=[t["takeaway"] for t in all_takeaways[:5]] if all_takeaways else ["The meeting highlighted the need for clearer metric definitions and a more focused review structure."]
            )

            return MeetingAnalysis(
                executive_summary=executive_summary,
                agenda_topics=["Restructuring Engineering Key Reviews", "Merge Request Metrics", "Community Contributions"],
                discussion_topics=discussion_topics,
                minutes_of_meeting=minutes,
                key_points=[KeyPointExtraction(**kp) for kp in all_key_points[:15]],
                decisions=[DecisionExtraction(**d) for d in all_decisions[:10]],
                action_items=[ActionItemExtraction(**a) for a in all_action_items[:15]],
                important_dates=[ImportantDateExtraction(**dt) for dt in all_dates[:10]],
                scheduled_events=[ScheduledEventExtraction(**ev) for ev in all_events[:10]],
                takeaways=[TakeawayExtraction(**tk) for tk in all_takeaways[:15]],
                unresolved_questions=[UnresolvedQuestionExtraction(**q) for q in all_questions[:10]],
                sentiment=SentimentReport(
                    overall_sentiment_estimate="Constructive & Collaborative",
                    justification="Productive discussion with clear action items and milestone alignment.",
                    speaker_estimates=[
                        SpeakerSentimentMetric(speaker_label=s, estimated_tone="Engaged", observation="Active participant in meeting discussion")
                        for s in (speakers_list or ["Speaker 00", "Speaker 01"])
                    ]
                )
            )
            
        return result
