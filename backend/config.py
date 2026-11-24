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
    # LLM & Vision (Google AI Studio FREE tier & OpenRouter :free tier)
    # ------------------------------------------------------------------
    gemini_api_key: str = Field(default="", description="Google AI Studio API key")
    gemini_model: str = Field(default="models/gemini-3.5-flash-lite", description="Default LLM model")
    gemini_pro_model: str = Field(default="models/gemini-3.8-flash", description="Pro model for complex tasks")
    gemini_vision_model: str = Field(default="models/gemini-3.8-flash", description="Vision model for video analysis")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key for strictly-free ($0.00 :free) tier")
    hf_token: str = Field(default="", description="Hugging Face token for free 5-min/day ZeroGPU video generation (LTX-2.5 / Wan 2.2)")
    enable_paid_gemini_video: bool = Field(default=False, description="Strict opt-in flag for paid gemini-omni-1.2-flash video generation (default False for $0 lock)")
    ollama_model: str = Field(default="copilot-brain:latest", description="Local Ollama model name")
    ollama_endpoint: str = Field(default="http://localhost:11434/api/chat", description="Local Ollama endpoint")

    # ------------------------------------------------------------------
    # Local Brain & C: Storage Paths (0 MB bloat on D:)
    # ------------------------------------------------------------------
    llama_server_bin: str = Field(default=r"D:\CONTENT-FACTORY\ollama\bin\llama-server.exe", description="Path to llama-server.exe")
    spark_gguf_blob: str = Field(default=r"C:\models\Spark-X2.5-4B-Q4_K_M.gguf", description="Path to local GGUF weights on C:")
    dataset_file: str = Field(default=r"C:\cf_training\dataset.jsonl", description="Harvester dataset JSONL path on C:")
    harvest_state_file: str = Field(default=r"C:\cf_training\harvest_state.json", description="Harvester state JSON path on C:")
    uploads_dir: str = Field(default=r"C:\cf_training\temp\uploads", description="Temporary upload storage on C:")

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
    # Cost Control (Zero-Cost $0 API Spend Rule by default)
    # ------------------------------------------------------------------
    max_cost_per_video_usd: float = Field(default=0.0, ge=0)
    daily_budget_usd: float = Field(default=0.0, ge=0)
    monthly_budget_usd: float = Field(default=0.0, ge=0)
    elevenlabs_api_key: str = Field(default="", description="Optional ElevenLabs API key (unused under $0 rule)")

    # ------------------------------------------------------------------
    # Approval, Niches, Paths & Automation
    # ------------------------------------------------------------------
    default_approval_mode: str = Field(default="manual", description="manual | auto_after_first | full_auto")
    auto_approve_after_n_success: int = Field(default=3, ge=0)
    approval_timeout_hours: int = Field(default=24, ge=1)
    max_concurrent_jobs: int = Field(default=2, ge=1)
    default_niches: str = Field(default="crime_doc,viral_edu,movie_cinema", description="Comma-separated default niches")
    data_dir: str = Field(default=str(BASE_DIR), description="Base data directory")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR")
    log_json: bool = Field(default=True, description="JSON structured logs")

    # ------------------------------------------------------------------
    # Derived / Computed
    # ------------------------------------------------------------------
    @property
    def niches_list(self) -> List[str]:
        return [x.strip() for x in (self.default_niches or "").split(",") if x.strip()]

    @property
    def output_dir(self) -> Path:
        return Path(self.data_dir) / "output"

    @property
    def temp_dir(self) -> Path:
        return Path(self.data_dir) / "temp"

    @property
    def styles_dir(self) -> Path:
        return Path(self.data_dir) / "styles"

    @property
    def skills_dir(self) -> Path:
        return Path(self.data_dir) / "skills"

    @property
    def effective_database_url(self) -> str:
        if self.use_postgres and self.postgres_url:
            return self.postgres_url
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()