import os
import shutil
from typing import Dict, Any, List
from fastapi import APIRouter
from app.core.config import settings
from app.services.audio_processor import is_ffmpeg_available
from app.services.transcriber import detect_device_and_compute_type
from app.services.diarizer import Diarizer
from app.services.llm_service import OllamaClient

router = APIRouter(prefix="/settings", tags=["Settings & Health"])

@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Check the operational status of all local AI engines and dependencies.
    Never exposes real secret tokens.
    """
    # 1. FFmpeg Check
    ffmpeg_ok = is_ffmpeg_available()
    ffmpeg_path = shutil.which("ffmpeg") or "Not found in PATH"

    # 2. faster-whisper & PyTorch CUDA check
    whisper_device, whisper_compute = detect_device_and_compute_type()
    cuda_available = False
    gpu_name = None
    vram_gb = 0.0
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    except Exception:
        pass

    # 3. pyannote Diarization & HF Token Check
    diarizer = Diarizer()
    hf_token_set = bool(settings.HF_TOKEN or os.environ.get("HF_TOKEN", "").strip())
    diarization_ready, diar_msg = diarizer.is_available()

    # 4. Ollama Status & Pulled Models Check
    ollama_client = OllamaClient()
    ollama_models = await ollama_client.get_available_models()
    ollama_connected = len(ollama_models) > 0 or bool(await ollama_client.resolve_model())
    resolved_model = await ollama_client.resolve_model() if ollama_connected else "None"

    return {
        "status": "healthy" if ffmpeg_ok else "warning",
        "ffmpeg": {
            "available": ffmpeg_ok,
            "path": ffmpeg_path
        },
        "whisper": {
            "primary_model": settings.WHISPER_MODEL,
            "fallback_model": settings.WHISPER_FALLBACK_MODEL,
            "device": whisper_device,
            "compute_type": whisper_compute,
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "vram_gb": vram_gb
        },
        "diarization": {
            "model": settings.DIARIZATION_MODEL,
            "token_configured": hf_token_set,
            "status_message": diar_msg,
            "is_ready": diarization_ready and hf_token_set,
            "instructions": (
                "To enable pyannote speaker diarization, accept terms at "
                "https://huggingface.co/pyannote/speaker-diarization-3.1 and set HF_TOKEN in your environment."
            )
        },
        "ollama": {
            "base_url": settings.OLLAMA_BASE_URL,
            "connected": ollama_connected,
            "target_model": settings.OLLAMA_MODEL,
            "active_model": resolved_model,
            "available_models": ollama_models
        },
        "embeddings": {
            "model": settings.EMBEDDING_MODEL,
            "device": settings.EMBEDDING_DEVICE
        }
    }
