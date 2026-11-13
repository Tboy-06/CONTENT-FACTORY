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
    custom_domain: Optional[str] = None
    telegram_token: Optional[str] = None
    gemini_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    moonshot_model: Optional[str] = None
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
        "custom_domain": os.environ.get("CUSTOM_DOMAIN", "localhost:3000"),
        "openai_key": "********" if settings.gemini_api_key else "",
        "gemini_key": "********" if settings.gemini_api_key else "",
        "moonshot_api_key": "********" if (settings.moonshot_api_key or os.environ.get("MOONSHOT_API_KEY")) else "",
        "moonshot_model": settings.moonshot_model or os.environ.get("MOONSHOT_MODEL", "kimi-k3"),
        "telegram_token": "********" if settings.telegram_bot_token else "",
        "youtube_key": "********" if settings.youtube_api_key else "",
        "pexels_key": "********" if settings.pexels_api_key else "",
        "spend_cap": getattr(settings, "monthly_budget_usd", 0.0),
    }

@router.post('')
async def update_settings(req: SettingsUpdate):
    settings = get_backend_settings()
    data = req.dict(exclude_unset=True)
    env_updates: Dict[str, str] = {}
    
    if req.ollama_model:
        os.environ["OLLAMA_MODEL"] = req.ollama_model
        env_updates["OLLAMA_MODEL"] = req.ollama_model
    if req.default_voice:
        settings.tts_voice = req.default_voice
        env_updates["TTS_VOICE"] = req.default_voice
    if req.force_offline is not None:
        val = "true" if req.force_offline else "false"
        os.environ["FORCE_OFFLINE"] = val
        env_updates["FORCE_OFFLINE"] = val
    if req.custom_domain:
        os.environ["CUSTOM_DOMAIN"] = req.custom_domain
        env_updates["CUSTOM_DOMAIN"] = req.custom_domain
    if req.moonshot_api_key:
        os.environ["MOONSHOT_API_KEY"] = req.moonshot_api_key
        settings.moonshot_api_key = req.moonshot_api_key
        env_updates["MOONSHOT_API_KEY"] = req.moonshot_api_key
    if req.moonshot_model:
        os.environ["MOONSHOT_MODEL"] = req.moonshot_model
        settings.moonshot_model = req.moonshot_model
        env_updates["MOONSHOT_MODEL"] = req.moonshot_model
    if req.gemini_key:
        os.environ["GEMINI_API_KEY"] = req.gemini_key
        settings.gemini_api_key = req.gemini_key
        env_updates["GEMINI_API_KEY"] = req.gemini_key

    # Persist updates to .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if env_updates and os.path.exists(os.path.dirname(env_path)):
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            new_lines = []
            seen_keys = set()
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    k = line.split("=", 1)[0].strip()
                    if k in env_updates:
                        new_lines.append(f"{k}={env_updates[k]}\n")
                        seen_keys.add(k)
                        continue
                new_lines.append(line)
            for k, v in env_updates.items():
                if k not in seen_keys:
                    new_lines.append(f"{k}={v}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            pass
        
    return {"status": "success", "settings": data}
