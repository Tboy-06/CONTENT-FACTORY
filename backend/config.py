from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


def _resolve_default_storage_root() -> str:
    env_override = os.environ.get("CF_STORAGE_ROOT", "").strip()
    if env_override:
        return str(Path(env_override))
    sys_drive = os.environ.get("SystemDrive", "").strip()
    if sys_drive:
        cand = Path(sys_drive + os.sep) / "cf_training"
        if cand.exists() or os.name == "nt":
            return str(cand)
    return str(Path.home() / ".content_factory")


def _resolve_default_models_root() -> str:
    env_override = os.environ.get("CF_MODELS_ROOT", "").strip()
    if env_override:
        return str(Path(env_override))
    sys_drive = os.environ.get("SystemDrive", "").strip()
    if sys_drive:
        cand = Path(sys_drive + os.sep) / "models"
        if cand.exists() or os.name == "nt":
            return str(cand)
    return str(Path(_resolve_default_storage_root()) / "models")


def _resolve_default_llama_bin() -> str:
    bin_name = "llama-server.exe" if os.name == "nt" else "llama-server"
    return str(BASE_DIR / "ollama" / "bin" / bin_name)


def _resolve_default_llm_base_url() -> str:
    host = os.environ.get("LOCAL_LLM_HOST", "127.0.0.1").strip()
    port = int(os.environ.get("LOCAL_LLM_PORT", "11434"))
    return f"http://{host}:{port}"


def _resolve_default_app_domain() -> str:
    host = os.environ.get("FRONTEND_HOST", "localhost").strip()
    port = int(os.environ.get("FRONTEND_PORT", "3000"))
    return f"{host}:{port}"


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
    local_llm_base_url: str = Field(default_factory=_resolve_default_llm_base_url, description="Local LLM base URL")
    ollama_endpoint: str = Field(default_factory=lambda: f"{_resolve_default_llm_base_url()}/api/chat", description="Local Ollama chat endpoint")
    custom_domain: str = Field(default_factory=_resolve_default_app_domain, description="Active studio domain/host")

    # ------------------------------------------------------------------
    # Dynamic Workspace & Model Storage Roots (Zero Hardcoded Drive Paths)
    # ------------------------------------------------------------------
    storage_root: str = Field(default_factory=_resolve_default_storage_root, description="External scratch, cache, and dataset storage root")
    models_root: str = Field(default_factory=_resolve_default_models_root, description="Local model weights root directory")
    llama_server_bin: str = Field(default_factory=_resolve_default_llama_bin, description="Path to llama-server binary")
    spark_gguf_blob: str = Field(default_factory=lambda: str(Path(_resolve_default_models_root()) / "Spark-X2.5-4B-Q4_K_M.gguf"), description="Path to local GGUF weights")
    dataset_file: str = Field(default_factory=lambda: str(Path(_resolve_default_storage_root()) / "dataset.jsonl"), description="Harvester dataset JSONL path")
    harvest_state_file: str = Field(default_factory=lambda: str(Path(_resolve_default_storage_root()) / "harvest_state.json"), description="Harvester state JSON path")
    uploads_dir: str = Field(default_factory=lambda: str(Path(_resolve_default_storage_root()) / "temp" / "uploads"), description="Temporary upload storage")

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
    comfyui_url: str = Field(default="", description="Optional ComfyUI URL")

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
    tts_voice: str = Field(default="en-US-AndrewMultilingualNeural", description="Default TTS voice")

    # ------------------------------------------------------------------
    # Posting (Postiz)
    # ------------------------------------------------------------------
    postiz_url: str = Field(default="", description="Postiz instance URL")
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
    def storage_root_path(self) -> Path:
        return Path(os.environ.get("CF_STORAGE_ROOT", "").strip() or self.storage_root)

    @property
    def models_root_path(self) -> Path:
        return Path(os.environ.get("CF_MODELS_ROOT", "").strip() or self.models_root)

    @property
    def jobs_scratch_dir(self) -> str:
        return str(self.storage_root_path / "jobs")

    @property
    def temp_root_dir(self) -> str:
        return str(self.storage_root_path / "temp")

    @property
    def beat_cache_dir(self) -> str:
        return str(self.storage_root_path / "temp" / "beat_cache")

    @property
    def ai_clips_dir(self) -> str:
        return str(self.storage_root_path / "temp" / "ai_clips")

    @property
    def exports_dir(self) -> str:
        return str(self.storage_root_path / "exports")

    @property
    def archive_outputs_dir(self) -> str:
        return str(self.storage_root_path / "archive_outputs")

    @property
    def harvest_vault_cache_dir(self) -> str:
        return str(self.storage_root_path / "director_vault_cache")

    @property
    def research_temp_dir(self) -> str:
        return str(self.storage_root_path / "temp" / "research")

    @property
    def active_render_lock_file(self) -> str:
        return str(self.storage_root_path / "temp" / "active_render.lock")

    @property
    def reflexion_log_file(self) -> str:
        return str(self.storage_root_path / "reflexion_log.jsonl")

    @property
    def kokoro_models_dir(self) -> str:
        return str(self.models_root_path / "kokoro")

    @property
    def public_app_url(self) -> str:
        dom = (os.environ.get("CUSTOM_DOMAIN") or self.custom_domain or "").strip()
        if not dom:
            return "https://content-factory.local"
        if dom.startswith(("http://", "https://")):
            return dom.rstrip("/")
        return f"http://{dom}".rstrip("/")

    @property
    def cors_origins(self) -> List[str]:
        port = int(os.environ.get("FRONTEND_PORT", "3000"))
        origins = [f"http://localhost:{port}", f"http://127.0.0.1:{port}"]
        pub = self.public_app_url
        if pub and pub not in origins:
            origins.append(pub)
        return origins

    @property
    def effective_database_url(self) -> str:
        if self.use_postgres and self.postgres_url:
            return self.postgres_url
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()