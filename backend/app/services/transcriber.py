import os
import gc
import math
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging import logger

def detect_device_and_compute_type() -> Tuple[str, str]:
    """Detect appropriate device and compute type for faster-whisper."""
    if settings.WHISPER_DEVICE == "cpu":
        return "cpu", "int8"
    
    try:
        import torch
        if torch.cuda.is_available():
            # Check VRAM
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"CUDA detected: {torch.cuda.get_device_name(0)} with {vram_gb:.2f} GB VRAM")
            return "cuda", "float16"
    except Exception as e:
        logger.warning(f"PyTorch CUDA check failed: {e}")
        
    return "cpu", "int8"

class Transcriber:
    def __init__(self, model_size_or_path: str = None):
        self.model_name = model_size_or_path or settings.WHISPER_MODEL
        self.device, self.compute_type = detect_device_and_compute_type()
        self.model = None

    def load_model(self):
        """Load the faster-whisper model into memory."""
        if self.model is not None:
            return self.model
            
        from faster_whisper import WhisperModel
        try:
            logger.info(f"Loading faster-whisper model '{self.model_name}' on {self.device} ({self.compute_type})...")
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
        except Exception as e:
            logger.warning(f"Failed loading model '{self.model_name}' on {self.device}: {e}. Trying fallback '{settings.WHISPER_FALLBACK_MODEL}' on cpu/int8...")
            self.model_name = settings.WHISPER_FALLBACK_MODEL
            self.device = "cpu"
            self.compute_type = "int8"
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
        return self.model

    def transcribe(self, audio_path: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Transcribe audio file.
        Returns (segments_list, detected_language).
        Each segment dict contains: start, end, text, avg_logprob, no_speech_prob.
        """
        model = self.load_model()
        logger.info(f"Starting transcription for {audio_path}...")
        
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            word_timestamps=False
        )
        
        detected_language = info.language
        logger.info(f"Detected language: {detected_language} with probability {info.language_probability:.2f}")

        results = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            
            # Confidence proxy from avg_logprob: exp(avg_logprob) clamped [0.1, 1.0]
            confidence = max(0.1, min(1.0, math.exp(seg.avg_logprob))) if seg.avg_logprob is not None else 0.95
            
            results.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
                "confidence": round(confidence, 3),
                "avg_logprob": seg.avg_logprob
            })
            
        logger.info(f"Transcription finished: {len(results)} segments generated.")
        return results, detected_language

    def unload(self):
        """Unload model and free GPU VRAM."""
        self.model = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("faster-whisper model unloaded and VRAM cleared.")
