import os
from typing import List

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class _BaseSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
except ImportError:
    class _BaseSettings:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

class Settings(_BaseSettings):
    gemini_api_key: str = "test_key"
    gemini_model: str = "gemini-3.7-flash"
    gemini_pro_model: str = "gemini-2.5-pro"
    gemini_vision_model: str = "gemini-3.7-flash"
    
    youtube_api_key: str = ""
    tavily_api_key: str = ""
    serpapi_key: str = ""
    firecrawl_key: str = ""
    pexels_api_key: str = ""
    
    postiz_url: str = "http://localhost:3000"
    postiz_api_key: str = ""
    
    telegram_bot_token: str = "test_token"
    telegram_allowed_users_raw: str = ""
    
    database_url: str = "sqlite+aiosqlite:///./vault.db"
    daily_budget_usd: float = 5.0
    scheduler_tick_minutes: int = 5

    def __init__(self, **kwargs):
        # Set defaults from class attributes if not using pydantic BaseSettings
        if not hasattr(super(), "model_config"):
            self.gemini_api_key = kwargs.get("gemini_api_key", os.getenv("GEMINI_API_KEY", "test_key"))
            self.gemini_model = kwargs.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-3.7-flash"))
            self.gemini_pro_model = kwargs.get("gemini_pro_model", os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro"))
            self.gemini_vision_model = kwargs.get("gemini_vision_model", os.getenv("GEMINI_VISION_MODEL", "gemini-3.7-flash"))
            self.youtube_api_key = kwargs.get("youtube_api_key", os.getenv("YOUTUBE_API_KEY", ""))
            self.tavily_api_key = kwargs.get("tavily_api_key", os.getenv("TAVILY_API_KEY", ""))
            self.serpapi_key = kwargs.get("serpapi_key", os.getenv("SERPAPI_KEY", ""))
            self.firecrawl_key = kwargs.get("firecrawl_key", os.getenv("FIRECRAWL_KEY", ""))
            self.pexels_api_key = kwargs.get("pexels_api_key", os.getenv("PEXELS_API_KEY", ""))
            self.postiz_url = kwargs.get("postiz_url", os.getenv("POSTIZ_URL", "http://localhost:3000"))
            self.postiz_api_key = kwargs.get("postiz_api_key", os.getenv("POSTIZ_API_KEY", ""))
            self.telegram_bot_token = kwargs.get("telegram_bot_token", os.getenv("TELEGRAM_BOT_TOKEN", "test_token"))
            self.telegram_allowed_users_raw = kwargs.get("telegram_allowed_users_raw", os.getenv("TELEGRAM_ALLOWED_USERS_RAW", ""))
            self.database_url = kwargs.get("database_url", os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vault.db"))
            self.daily_budget_usd = float(kwargs.get("daily_budget_usd", os.getenv("DAILY_BUDGET_USD", 5.0)))
            self.scheduler_tick_minutes = int(kwargs.get("scheduler_tick_minutes", 5))
        else:
            super().__init__(**kwargs)

    @property
    def allowed_user_ids(self) -> List[int]:
        if not self.telegram_allowed_users_raw:
            return []
        return [int(x.strip()) for x in self.telegram_allowed_users_raw.split(',') if x.strip().isdigit()]

    @property
    def effective_database_url(self) -> str:
        return self.database_url

settings = Settings()
