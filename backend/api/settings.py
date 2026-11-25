from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from backend.config import get_settings as get_backend_settings
import os

router = APIRouter()

SECRET_FIELD_NAMES = {
    "gemini_key",
    "openai_key",
    "moonshot_api_key",
    "openrouter_api_key",
    "hf_token",
    "telegram_token",
    "youtube_key",
    "pexels_key",
}


def mask_secret(val: Optional[str]) -> str:
    """Masks any secret/API key so plaintext keys are never exposed in GET or POST responses."""
    if not val or not isinstance(val, str):
        return ""
    cleaned = val.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("****"):
        return cleaned
    if len(cleaned) <= 6:
        return "********"
    return f"****{cleaned[-4:]}"


def _is_masked_placeholder(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return True
    s = val.strip()
    return not s or s.startswith("****")


class SettingsUpdate(BaseModel):
    ollama_model: Optional[str] = None
    default_voice: Optional[str] = None
    force_offline: Optional[bool] = None
    custom_domain: Optional[str] = None
    telegram_token: Optional[str] = None
    gemini_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    moonshot_model: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    niche: Optional[str] = None
    format: Optional[str] = None
    platforms: Optional[List[str]] = None
    premium: Optional[bool] = None


@router.get('')
async def get_settings():
    settings = get_backend_settings()
    gemini_val = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    moonshot_val = settings.moonshot_api_key or os.environ.get("MOONSHOT_API_KEY", "")
    openrouter_val = getattr(settings, "openrouter_api_key", "") or os.environ.get("OPENROUTER_API_KEY", "")
    hf_val = getattr(settings, "hf_token", "") or os.environ.get("HF_TOKEN", "")
    telegram_val = settings.telegram_bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    youtube_val = settings.youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")
    pexels_val = settings.pexels_api_key or os.environ.get("PEXELS_API_KEY", "")

    api_host = f"{os.environ.get('BACKEND_HOST', '127.0.0.1').strip()}:{os.environ.get('BACKEND_PORT', '8000').strip()}"
    raw_voice = (settings.tts_voice or "").strip()
    valid_voices = {
        "en-US-AndrewMultilingualNeural",
        "en-US-AvaMultilingualNeural",
        "en-US-BrianMultilingualNeural",
        "am_michael",
    }
    normalized_voice = raw_voice if raw_voice in valid_voices else "en-US-AndrewMultilingualNeural"

    return {
        "ollama_model": os.environ.get("OLLAMA_MODEL", "SparkLLM/Spark-X2.5-4B"),
        "default_voice": normalized_voice,
        "force_offline": os.environ.get("FORCE_OFFLINE", "false").lower() == "true",
        "custom_domain": os.environ.get("CUSTOM_DOMAIN") or settings.custom_domain,
        "api_host": api_host,
        "storage_root": str(settings.storage_root_path),
        "models_root": str(settings.models_root_path),
        "openai_key": mask_secret(gemini_val),
        "gemini_key": mask_secret(gemini_val),
        "moonshot_api_key": mask_secret(moonshot_val),
        "moonshot_model": settings.moonshot_model or os.environ.get("MOONSHOT_MODEL", "kimi-k3"),
        "openrouter_api_key": mask_secret(openrouter_val),
        "hf_token": mask_secret(hf_val),
        "telegram_token": mask_secret(telegram_val),
        "youtube_key": mask_secret(youtube_val),
        "pexels_key": mask_secret(pexels_val),
        "spend_cap": getattr(settings, "monthly_budget_usd", 0.0),
    }


@router.post('')
async def update_settings(req: SettingsUpdate):
    settings = get_backend_settings()
    data = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
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
    if req.moonshot_api_key and not _is_masked_placeholder(req.moonshot_api_key):
        os.environ["MOONSHOT_API_KEY"] = req.moonshot_api_key
        settings.moonshot_api_key = req.moonshot_api_key
        env_updates["MOONSHOT_API_KEY"] = req.moonshot_api_key
    if req.moonshot_model:
        os.environ["MOONSHOT_MODEL"] = req.moonshot_model
        settings.moonshot_model = req.moonshot_model
        env_updates["MOONSHOT_MODEL"] = req.moonshot_model
    if req.gemini_key and not _is_masked_placeholder(req.gemini_key):
        os.environ["GEMINI_API_KEY"] = req.gemini_key
        settings.gemini_api_key = req.gemini_key
        env_updates["GEMINI_API_KEY"] = req.gemini_key
    if req.openrouter_api_key and not _is_masked_placeholder(req.openrouter_api_key):
        os.environ["OPENROUTER_API_KEY"] = req.openrouter_api_key
        settings.openrouter_api_key = req.openrouter_api_key
        env_updates["OPENROUTER_API_KEY"] = req.openrouter_api_key
    if req.hf_token and not _is_masked_placeholder(req.hf_token):
        os.environ["HF_TOKEN"] = req.hf_token
        settings.hf_token = req.hf_token
        env_updates["HF_TOKEN"] = req.hf_token
    if req.telegram_token and not _is_masked_placeholder(req.telegram_token):
        os.environ["TELEGRAM_BOT_TOKEN"] = req.telegram_token
        settings.telegram_bot_token = req.telegram_token
        env_updates["TELEGRAM_BOT_TOKEN"] = req.telegram_token

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

    # Always mask secrets before returning response payload
    safe_response_data = {
        k: (mask_secret(v) if k in SECRET_FIELD_NAMES else v)
        for k, v in data.items()
    }
    return {"status": "success", "settings": safe_response_data}
