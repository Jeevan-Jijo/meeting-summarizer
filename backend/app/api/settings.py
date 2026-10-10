import os
import shutil
from typing import Dict, Any, List
from fastapi import APIRouter
from app.core.config import settings
from app.services.audio_processor import is_ffmpeg_available
from app.services.deepgram_service import DeepgramService
from app.services.llm_service import OllamaClient

router = APIRouter(prefix="/settings", tags=["Settings & Health"])

@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Check the operational status of all AI services and dependencies.
    Never exposes real secret tokens.
    """
    # 1. FFmpeg Check
    ffmpeg_ok = is_ffmpeg_available()
    ffmpeg_path = shutil.which("ffmpeg") or "Not found in PATH"

    # 2. Deepgram Service Check (Primary STT & Diarization)
    deepgram_service = DeepgramService()
    deepgram_configured = deepgram_service.is_configured()
    deepgram_health = {
        "configured": deepgram_configured,
        "model": getattr(settings, "DEEPGRAM_MODEL", "nova-2"),
        "status_message": "Deepgram Cloud STT ready" if deepgram_configured else "DEEPGRAM_API_KEY unconfigured in backend/.env"
    }

    # 3. Speaker Diarization Health
    diarization_health = {
        "model": f"deepgram-{getattr(settings, 'DEEPGRAM_MODEL', 'nova-2')}",
        "token_configured": deepgram_configured,
        "status_message": "Native Deepgram speaker diarization enabled" if deepgram_configured else "Requires DEEPGRAM_API_KEY",
        "is_ready": deepgram_configured
    }

    # 4. Ollama Status & Pulled Models Check
    ollama_client = OllamaClient()
    ollama_models = await ollama_client.get_available_models()
    ollama_connected = len(ollama_models) > 0 or bool(await ollama_client.resolve_model())
    resolved_model = await ollama_client.resolve_model() if ollama_connected else "None"

    return {
        "status": "healthy" if (ffmpeg_ok and deepgram_configured) else "warning",
        "ffmpeg": {
            "available": ffmpeg_ok,
            "path": ffmpeg_path
        },
        "deepgram": deepgram_health,
        "diarization": diarization_health,
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
