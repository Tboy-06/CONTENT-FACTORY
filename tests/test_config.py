import pytest
from backend.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.video_engine == "ffmpeg"
    assert s.tts_engine == "edge"
    assert s.max_cost_per_video_usd == 2.0


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("MAX_COST_PER_VIDEO_USD", "5.0")
    s = Settings()
    assert s.gemini_model == "gemini-2.5-pro"
    assert s.max_cost_per_video_usd == 5.0


def test_allowed_users_parsing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS_RAW", "123, 456, 789")
    s = Settings()
    assert s.allowed_user_ids == [123, 456, 789]


def test_effective_database_url_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("USE_POSTGRES", "false")
    s = Settings()
    assert s.effective_database_url == "sqlite:///./test.db"


def test_effective_database_url_postgres(monkeypatch):
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("USE_POSTGRES", "true")
    s = Settings()
    assert s.effective_database_url == "postgresql+asyncpg://user:pass@localhost/db"