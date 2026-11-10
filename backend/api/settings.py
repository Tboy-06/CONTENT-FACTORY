from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.config import get_settings as get_backend_settings
import os

router = APIRouter()

class SettingsUpdate(BaseModel):
    ollama_model: Optional[str] = None
    default_voice: Optional[str] = None
    force_offline: Optional[bool] = None
    telegram_token: Optional[str] = None
    gemini_key: Optional[str] = None
    niche: Optional[str] = None
    format: Optional[str] = None
    platforms: Optional[List[str]] = None
    premium: Optional[bool] = None

@router.get('')
async def get_settings():
    settings = get_backend_settings()
    
    return {
        "ollama_model": os.environ.get("OLLAMA_MODEL", "SparkLLM/Spark-X2.5-4B"),
        "default_voice": settings.tts_voice or "en-US-ChristopherNeural",
        "force_offline": os.environ.get("FORCE_OFFLINE", "false").lower() == "true",
        "openai_key": "********" if settings.gemini_api_key else "",
        "gemini_key": "********" if settings.gemini_api_key else "",
        "telegram_token": "********" if settings.telegram_bot_token else "",
        "youtube_key": "********" if settings.youtube_api_key else "",
        "pexels_key": "********" if settings.pexels_api_key else "",
        "spend_cap": settings.monthly_budget_usd,
    }

@router.post('')
async def update_settings(req: SettingsUpdate):
    settings = get_backend_settings()
    data = req.dict(exclude_unset=True)
    
    if req.ollama_model:
        os.environ["OLLAMA_MODEL"] = req.ollama_model
    if req.default_voice:
        settings.tts_voice = req.default_voice
    if req.force_offline is not None:
        os.environ["FORCE_OFFLINE"] = "true" if req.force_offline else "false"
        
    return {"status": "success", "settings": data}
