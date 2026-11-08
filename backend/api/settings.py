from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from backend.config import get_settings as get_backend_settings

router = APIRouter()

class SettingsUpdate(BaseModel):
    niche: str
    format: str
    platforms: list[str]
    premium: bool

@router.get('')
async def get_settings():
    settings = get_backend_settings()
    
    # Expose actual keys obfuscated, plus some global flags
    return {
        "openai_key": "********" if settings.gemini_api_key else "",
        "gemini_key": "********" if settings.gemini_api_key else "",
        "telegram_token": "********" if settings.telegram_bot_token else "",
        "youtube_key": "********" if settings.youtube_api_key else "",
        "pexels_key": "********" if settings.pexels_api_key else "",
        "spend_cap": settings.monthly_budget_usd,
    }

@router.post('')
async def update_settings(req: SettingsUpdate):
    # In a real scenario we'd update .env or a DB
    return {"status": "success", "settings": req.dict()}
