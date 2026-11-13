from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # LLM & Vision (Google AI Studio FREE tier)
    # ------------------------------------------------------------------
    gemini_api_key: str = Field(default="", description="Google AI Studio API key")
    gemini_model: str = Field(default="models/gemini-3.1-flash-lite", description="Default LLM model")
    gemini_pro_model: str = Field(default="gemini-2.5-flash", description="Pro model for complex tasks")
    gemini_vision_model: str = Field(default="gemini-2.5-flash", description="Vision model for video analysis")

    # ------------------------------------------------------------------
    # Kimi K3 / Moonshot AI
    # ------------------------------------------------------------------
    moonshot_api_key: str = Field(default="", description="Moonshot AI API key for Kimi K3 / Kimi models")
    moonshot_model: str = Field(default="kimi-k3", description="kimi-k3 | moonshot-v1-auto | moonshot-v1-128k")
    kimi_endpoint: str = Field(default="https://api.moonshot.cn/v1/chat/completions", description="Kimi / Moonshot API endpoint")

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------
    image_provider: str = Field(default="pexels", description="pexels | comfyui | nanobanana")
    pexels_api_key: str = Field(default="", description="Pexels API key")
    comfyui_url: str = Field(default="http://127.0.0.1:8188", description="ComfyUI local URL")

    # ------------------------------------------------------------------
    # Video & Editors (FFmpeg, Nuzky, OpenCut)
    # ------------------------------------------------------------------
    video_engine: str = Field(default="nuzky", description="nuzky | ffmpeg | veo (manual)")
    ffmpeg_path: str = Field(default="ffmpeg", description="FFmpeg binary path")
    nuzky_cli_path: str = Field(default="nuzky-cli", description="Nuzky CLI binary path")
    opencut_url: str = Field(default="https://opencut.app", description="OpenCut web editor URL or local instance")

    # ------------------------------------------------------------------
    # Voice (Edge-TTS)
    # ------------------------------------------------------------------
    tts_engine: str = Field(default="edge", description="TTS engine")
    tts_voice: str = Field(default="en-US-AriaNeural", description="Edge-TTS voice")

    # ------------------------------------------------------------------
    # Posting (Postiz)
    # ------------------------------------------------------------------
    postiz_url: str = Field(default="http://localhost:3000", description="Postiz instance URL")
    postiz_api_key: str = Field(default="", description="Postiz API key")

    # ------------------------------------------------------------------
    # Telegram
    # ------------------------------------------------------------------
    telegram_bot_token: str = Field(default="", description="Bot token from @BotFather")
    telegram_chat_id: str = Field(default="", description="Primary chat ID for approvals")
    telegram_allowed_users_raw: str = Field(default="", description="Allowed user chat IDs (comma-separated)")

    @property
    def telegram_allowed_users(self) -> List[str]:
        v = self.telegram_allowed_users_raw
        if not v:
            return []
        try:
            import json
            return json.loads(v)
        except json.JSONDecodeError:
            return [x.strip() for x in v.split(",") if x.strip()]

    @property
    def allowed_user_ids(self) -> List[int]:
        return [int(x) for x in self.telegram_allowed_users if x.isdigit()]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(default=f"sqlite:///{ (BASE_DIR / 'vault.db').as_posix() }", description="SQLite URL")
    postgres_url: str = Field(default="", description="PostgreSQL URL (optional)")
    use_postgres: bool = Field(default=False, description="Use Postgres instead of SQLite")

    # ------------------------------------------------------------------
    # External APIs
    # ------------------------------------------------------------------
    serpapi_key: str = Field(default="", description="SerpAPI key")
    tavily_api_key: str = Field(default="", description="Tavily API key")
    firecrawl_api_key: str = Field(default="", description="Firecrawl API key")
    jina_api_key: str = Field(default="", description="Jina AI API key")
    youtube_api_key: str = Field(default="", description="YouTube Data API v3 key")

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    daily_research_hour: int = Field(default=6, ge=0, le=23)
    pipeline_tick_interval_minutes: int = Field(default=5, ge=1, le=60)
    analytics_fetch_hour: int = Field(default=2, ge=0, le=23)

    # ------------------------------------------------------------------
    # Cost Control
    # ------------------------------------------------------------------
    max_cost_per_video_usd: float = Field(default=2.0, gt=0)
    daily_budget_usd: float = Field(default=10.0, gt=0)
    monthly_budget_usd: float = Field(default=200.0, gt=0)

    # ------------------------------------------------------------------
    # Approval & Automation
    # ------------------------------------------------------------------
    default_approval_mode: str = Field(default="manual", description="manual | auto_after_first | full_auto")
    auto_approve_after_n_success: int = Field(default=3, ge=0)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR")
    log_json: bool = Field(default=True, description="JSON structured logs")

    # ------------------------------------------------------------------
    # Derived / Computed
    # ------------------------------------------------------------------
    @property
    def effective_database_url(self) -> str:
        if self.use_postgres and self.postgres_url:
            return self.postgres_url
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()