import os
import math
import re
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import settings
from app.core.logging import logger

try:
    from deepgram import DeepgramClient
except ImportError:
    DeepgramClient = None


class DeepgramService:
    """
    Speech-to-text and speaker diarization service using the official Deepgram Python SDK.
    Replaces local Whisper / NVIDIA NeMo processing with fast, accurate, cloud-based transcription.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else getattr(settings, "DEEPGRAM_API_KEY", "")
        self.model = model or getattr(settings, "DEEPGRAM_MODEL", "nova-2") or "nova-2"

    def is_configured(self) -> bool:
        """Check if a valid Deepgram API key is configured."""
        key = (self.api_key or "").strip()
        return bool(key and key != "your_deepgram_api_key_here")

    def get_client(self) -> Any:
        """Get an initialized DeepgramClient or raise ConfigurationError."""
        if not DeepgramClient:
            raise RuntimeError(
                "The 'deepgram-sdk' package is not installed. Run 'pip install deepgram-sdk' to use Deepgram service."
            )

        if not self.is_configured():
            raise ValueError(
                "DEEPGRAM_API_KEY is missing or unconfigured. Please add your API key to backend/.env (DEEPGRAM_API_KEY=your_key)."
            )

        return DeepgramClient(api_key=self.api_key)

    def transcribe_file(self, audio_path: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Transcribe audio/video recording with native Deepgram speaker diarization.

        Returns:
            Tuple[segments, language]:
                - segments: List of segment dicts compatible with MIS pipeline & DB:
                    [
                        {
                            "start": 0.0,
                            "end": 5.4,
                            "text": "Good morning everyone.",
                            "speaker_tag": "SPEAKER_00",
                            "speaker_label": "Speaker 1",
                            "confidence": 0.98
                        },
                        ...
                    ]
                - language: Detected or configured language string (e.g. 'en')
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio recording file not found at '{audio_path}'")

        client = self.get_client()
        logger.info(f"Initiating Deepgram Nova-2 transcription for file: {audio_path}")

        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            if len(audio_bytes) == 0:
                raise ValueError(f"Audio file '{audio_path}' is empty (0 bytes).")

            response = client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model=self.model,
                smart_format=True,
                punctuate=True,
                diarize=True,
                utterances=True,
                detect_language=True
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Deepgram API transcription request failed for '{audio_path}': {error_msg}")
            if "401" in error_msg or "Unauthorized" in error_msg or "invalid api key" in error_msg.lower():
                raise ValueError("Deepgram API authentication failed: Invalid or expired DEEPGRAM_API_KEY.") from e
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise RuntimeError("Deepgram API rate limit exceeded. Please retry after a brief pause.") from e
            else:
                raise RuntimeError(f"Deepgram API transcription failed for '{audio_path}': {error_msg}") from e

        return self.parse_deepgram_response(response, audio_path)

    def parse_deepgram_response(self, response: Any, audio_path: str = "") -> Tuple[List[Dict[str, Any]], str]:
        """
        Parse Deepgram API response object/dict into standard MIS segment structure.
        Handles utterances, paragraphs, raw transcripts, and empty results.
        """
        if not response:
            raise RuntimeError("Received empty response payload from Deepgram API.")

        # Resolve results dictionary/object
        results = getattr(response, "results", None)
        if results is None and isinstance(response, dict):
            results = response.get("results")

        if not results:
            logger.warning(f"No results returned in Deepgram payload for {audio_path}")
            return self._empty_fallback_segments()

        # Extract language detection
        language = "en"
        channels = getattr(results, "channels", None) or (results.get("channels") if isinstance(results, dict) else None)
        
        if channels and len(channels) > 0:
            ch0 = channels[0]
            detected_lang = getattr(ch0, "detected_language", None) or (ch0.get("detected_language") if isinstance(ch0, dict) else None)
            if detected_lang:
                language = detected_lang

        # 1. Primary Strategy: Utterances with speaker diarization
        utterances = getattr(results, "utterances", None) or (results.get("utterances") if isinstance(results, dict) else None)
        
        if utterances and len(utterances) > 0:
            segments = []
            for utt in utterances:
                if isinstance(utt, dict):
                    transcript_text = str(utt.get("transcript", "") or "").strip()
                    start_time = float(utt.get("start", 0.0) or 0.0)
                    end_time = float(utt.get("end", start_time + 1.0) or (start_time + 1.0))
                    confidence = float(utt.get("confidence", 0.95) or 0.95)
                    speaker_id = utt.get("speaker", 0)
                else:
                    transcript_text = str(getattr(utt, "transcript", "") or "").strip()
                    start_time = float(getattr(utt, "start", 0.0) or 0.0)
                    end_time = float(getattr(utt, "end", start_time + 1.0) or (start_time + 1.0))
                    confidence = float(getattr(utt, "confidence", 0.95) or 0.95)
                    speaker_id = getattr(utt, "speaker", 0)

                if not transcript_text:
                    continue
                try:
                    spk_num = int(speaker_id if speaker_id is not None else 0)
                except (ValueError, TypeError):
                    spk_num = 0

                speaker_tag = f"SPEAKER_{spk_num:02d}"
                speaker_label = f"Speaker {spk_num + 1}"

                segments.append({
                    "start": round(start_time, 2),
                    "end": round(end_time, 2),
                    "text": transcript_text,
                    "speaker_tag": speaker_tag,
                    "speaker_label": speaker_label,
                    "confidence": round(max(0.1, min(1.0, confidence)), 3)
                })

            if segments:
                logger.info(f"Successfully extracted {len(segments)} speaker-diarized utterances from Deepgram response.")
                return segments, language

        # 2. Secondary Strategy: Alternatives transcript paragraphs / words
        if channels and len(channels) > 0:
            ch0 = channels[0]
            alts = getattr(ch0, "alternatives", None) or (ch0.get("alternatives") if isinstance(ch0, dict) else None)
            if alts and len(alts) > 0:
                alt0 = alts[0]
                full_text = getattr(alt0, "transcript", "") or (alt0.get("transcript") if isinstance(alt0, dict) else "")
                full_text = full_text.strip()

                if full_text:
                    confidence = float(getattr(alt0, "confidence", 0.95) or (alt0.get("confidence", 0.95) if isinstance(alt0, dict) else 0.95))
                    words = getattr(alt0, "words", None) or (alt0.get("words") if isinstance(alt0, dict) else None)
                    duration = 5.0
                    if words and len(words) > 0:
                        last_w = words[-1]
                        duration = float(getattr(last_w, "end", 5.0) or (last_w.get("end", 5.0) if isinstance(last_w, dict) else 5.0))

                    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', full_text) if s.strip()]
                    if not sentences:
                        sentences = [full_text]

                    total_chars = max(1, sum(len(s) for s in sentences))
                    segments = []
                    curr_time = 0.0

                    for i, s in enumerate(sentences):
                        seg_dur = (len(s) / total_chars) * duration
                        end_time = min(duration, curr_time + seg_dur) if i < len(sentences) - 1 else duration
                        segments.append({
                            "start": round(curr_time, 2),
                            "end": round(end_time, 2),
                            "text": s,
                            "speaker_tag": "SPEAKER_00",
                            "speaker_label": "Speaker 1",
                            "confidence": round(confidence, 3)
                        })
                        curr_time = end_time

                    return segments, language

        # 3. Fallback if no speech found in recording
        return self._empty_fallback_segments()

    def _empty_fallback_segments(self) -> Tuple[List[Dict[str, Any]], str]:
        return [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "[No audible speech detected in recording]",
                "speaker_tag": "SPEAKER_00",
                "speaker_label": "Unknown Speaker",
                "confidence": 0.5
            }
        ], "en"


def transcribe_with_deepgram(audio_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """Helper function to transcribe an audio file using Deepgram service."""
    service = DeepgramService()
    return service.transcribe_file(audio_path)
