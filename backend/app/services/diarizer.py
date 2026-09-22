import os
import gc
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging import logger

class Diarizer:
    def __init__(self, token: str = None):
        raw_token = token or settings.HF_TOKEN or os.environ.get("HF_TOKEN", "") or ""
        self.token = raw_token.strip()
        self.pipeline = None

    def is_available(self) -> Tuple[bool, str]:
        """Check if pyannote can be loaded with valid token."""
        if not self.token:
            return False, "Hugging Face token (HF_TOKEN) is not configured. Falling back to single-speaker mode."
        try:
            import pyannote.audio
            return True, "pyannote.audio available with token"
        except ImportError:
            return False, "pyannote.audio package is not installed in the environment."

    def load_pipeline(self):
        """Load the pyannote speaker diarization pipeline."""
        if self.pipeline is not None:
            return self.pipeline
            
        if not self.token:
            logger.info("No HF_TOKEN provided; skipping pyannote loading.")
            return None
            
        try:
            from pyannote.audio import Pipeline
            import torch
            
            logger.info(f"Loading pyannote pipeline '{settings.DIARIZATION_MODEL}'...")
            try:
                self.pipeline = Pipeline.from_pretrained(
                    settings.DIARIZATION_MODEL,
                    token=self.token
                )
            except TypeError:
                self.pipeline = Pipeline.from_pretrained(
                    settings.DIARIZATION_MODEL,
                    use_auth_token=self.token
                )
            
            if torch.cuda.is_available() and settings.WHISPER_DEVICE != "cpu":
                self.pipeline.to(torch.device("cuda"))
                logger.info("pyannote diarization loaded on CUDA")
            else:
                logger.info("pyannote diarization loaded on CPU")
                
            return self.pipeline
        except Exception as e:
            logger.warning(
                f"Could not load pyannote pipeline ({e}). "
                f"Please ensure you accepted terms at https://huggingface.co/pyannote/speaker-diarization-3.1 "
                f"and generated a token at https://huggingface.co/settings/tokens. "
                f"Gracefully continuing with Unknown Speaker tags."
            )
            self.pipeline = None
            return None

    def diarize(self, audio_path: str) -> Tuple[List[Dict[str, Any]], bool, str]:
        """
        Diarize audio file.
        Returns (speaker_turns_list, is_real_diarization, status_message).
        speaker_turns_list format: [{'start': 0.0, 'end': 12.5, 'speaker': 'SPEAKER_00'}, ...]
        """
        pipeline = self.load_pipeline()
        
        if pipeline is None:
            return [], False, "Diarization skipped (HF_TOKEN not set or model access not granted)."
            
        try:
            logger.info(f"Running pyannote diarization on {audio_path}...")
            diarization = pipeline(audio_path)
            
            turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                turns.append({
                    "start": round(turn.start, 2),
                    "end": round(turn.end, 2),
                    "speaker": str(speaker)
                })
                
            logger.info(f"Diarization complete: found {len(turns)} turns across {len(set(t['speaker'] for t in turns))} speakers.")
            return turns, True, "Speaker diarization completed successfully"
        except Exception as e:
            logger.error(f"Error during diarization inference: {e}")
            return [], False, f"Diarization error: {str(e)}"

    def unload(self):
        """Free VRAM after diarization step."""
        self.pipeline = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("Diarization pipeline unloaded and VRAM cleared.")
