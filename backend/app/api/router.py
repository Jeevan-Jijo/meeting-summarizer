from fastapi import APIRouter
from app.api.meetings import router as meetings_router
from app.api.jobs import router as jobs_router
from app.api.chat import router as chat_router
from app.api.export import router as export_router
from app.api.settings import router as settings_router
from app.api.audio import router as audio_router

api_router = APIRouter()
api_router.include_router(meetings_router)
api_router.include_router(jobs_router)
api_router.include_router(chat_router)
api_router.include_router(export_router)
api_router.include_router(settings_router)
api_router.include_router(audio_router)
