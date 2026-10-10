import os
import gc
import re
import sys
import math
import types
from typing import List, Dict, Any, Tuple

from app.core.config import settings
from app.core.logging import logger

# Ensure youtokentome stub is registered for Python 3.9/Windows environment if missing
try:
    import youtokentome as yttm
except ImportError:
    yttm = types.ModuleType("youtokentome")
    yttm.BpeModel = object
    sys.modules["youtokentome"] = yttm

# Ensure NumPy 2.0+ compatibility for NeMo's np.sctypes access
import numpy as np
if not hasattr(np, "sctypes"):
    np.sctypes = {
        "int": [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64],
        "float": [np.float16, np.float32, np.float64],
        "complex": [np.complex64, np.complex128],
        "bool": [np.bool_],
    }


def detect_device_and_compute_type() -> Tuple[str, str]:
    """Detect appropriate device and compute type for NVIDIA Parakeet."""
    device_setting = getattr(settings, "PARAKEET_DEVICE", getattr(settings, "WHISPER_DEVICE", "auto"))
    if device_setting == "cpu":
        return "cpu", "float32"

    try:
        import torch
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"CUDA detected for Parakeet: {torch.cuda.get_device_name(0)} with {vram_gb:.2f} GB VRAM")
            return "cuda", "float16"
    except Exception as e:
        logger.warning(f"PyTorch CUDA check failed: {e}")

    return "cpu", "float32"


class Transcriber:
    """
    NVIDIA Parakeet Speech-to-Text engine wrapper using NVIDIA NeMo toolkit.
    Uses pretrained model `nvidia/parakeet-tdt-0.6b-v2` for English audio transcription.
    """
    def __init__(self, model_size_or_path: str = None):
        self.model_name = model_size_or_path or getattr(settings, "PARAKEET_MODEL", "nvidia/parakeet-tdt-0.6b-v2")
        self.device, self.compute_type = detect_device_and_compute_type()
        self.model = None

    def load_model(self):
        """Load the NVIDIA Parakeet model into memory using NeMo toolkit."""
        if self.model is not None:
            return self.model

        import torch
        import nemo.collections.asr as nemo_asr

        logger.info(f"Loading NVIDIA Parakeet model '{self.model_name}' on {self.device} ({self.compute_type})...")
        try:
            model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(
                model_name=self.model_name,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed loading EncDecRNNTBPEModel '{self.model_name}': {e}. Trying ASRModel fallback...")
            fallback_model_name = getattr(settings, "PARAKEET_FALLBACK_MODEL", "nvidia/parakeet-tdt-0.6b-v2")
            try:
                model = nemo_asr.models.ASRModel.from_pretrained(
                    model_name=fallback_model_name,
                    strict=False
                )
            except Exception as ex:
                logger.error(f"Fallback model loading failed: {ex}")
                raise RuntimeError(f"Could not load NVIDIA Parakeet ASR model '{self.model_name}': {ex}")

        # Move to GPU if available and requested
        if self.device == "cuda" and torch.cuda.is_available():
            try:
                model = model.to(torch.device("cuda"))
            except Exception as dev_err:
                logger.warning(f"Could not move Parakeet model to CUDA: {dev_err}. Running on CPU.")
                self.device = "cpu"
                model = model.to(torch.device("cpu"))
        else:
            self.device = "cpu"
            model = model.to(torch.device("cpu"))

        model.eval()
        self.model = model
        logger.info(f"NVIDIA Parakeet model successfully loaded on {self.device}.")
        return self.model

    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            return float(info.duration)
        except Exception:
            pass

        try:
            import wave
            with wave.open(audio_path, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return float(frames) / float(max(1, rate))
        except Exception:
            pass

        return 1.0

    def transcribe(self, audio_path: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Transcribe audio file using NVIDIA Parakeet.
        Returns (segments_list, detected_language).
        Each segment dict contains: start, end, text, confidence.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise ValueError(f"Audio file is empty: {audio_path}")

        duration = max(0.5, self.get_audio_duration(audio_path))
        model = self.load_model()
        logger.info(f"Starting NVIDIA Parakeet transcription for {audio_path} (duration: {duration:.2f}s)...")

        try:
            res = model.transcribe([audio_path], return_hypotheses=True)
        except Exception as e:
            logger.error(f"Error during Parakeet transcription execution: {e}")
            raise RuntimeError(f"NVIDIA Parakeet transcription failed for {audio_path}: {e}")

        text = ""
        confidence = 0.95

        if res and len(res) > 0:
            hyp_item = res[0]
            if isinstance(hyp_item, list) and len(hyp_item) > 0:
                hyp = hyp_item[0]
                text = getattr(hyp, "text", str(hyp)).strip()
                if hasattr(hyp, "score") and hyp.score is not None and hyp.score != 0.0:
                    confidence = round(max(0.1, min(1.0, math.exp(hyp.score))), 3)
            elif hasattr(hyp_item, "text"):
                text = hyp_item.text.strip()
            elif isinstance(hyp_item, str):
                text = hyp_item.strip()

        if not text:
            logger.warning(f"No speech text returned by Parakeet for {audio_path}.")
            return [{
                "start": 0.0,
                "end": round(duration, 2),
                "text": "[No audible speech detected in recording]",
                "confidence": 0.5
            }], "en"

        # Break full text into timestamped sentence segments
        sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]
        if not sentences:
            sentences = [text]

        total_chars = max(1, sum(len(s) for s in sentences))
        results = []
        curr_time = 0.0

        for i, s in enumerate(sentences):
            seg_dur = (len(s) / total_chars) * duration
            end_time = min(duration, curr_time + seg_dur) if i < len(sentences) - 1 else duration
            results.append({
                "start": round(curr_time, 2),
                "end": round(end_time, 2),
                "text": s,
                "confidence": round(confidence, 3)
            })
            curr_time = end_time

        logger.info(f"Parakeet transcription finished: {len(results)} segments generated.")
        return results, "en"

    def unload(self):
        """Unload model and free GPU VRAM / CPU memory."""
        self.model = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("NVIDIA Parakeet model unloaded and memory cleared.")

