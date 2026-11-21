"""
TDD Test Suite for Zero-Cost Dynamic OpenRouter Capability Discovery & Hybrid Fallback Router
---------------------------------------------------------------------------------------------
"""

import pytest

from backend.engine.openrouter_discovery import (
    is_strictly_free,
    classify_catalog_into_stages,
    get_free_models_for,
    record_openrouter_status,
    is_openrouter_on_cooldown,
    reset_circuit_breaker,
    get_capabilities_report,
)


def test_is_strictly_free_rejects_paid_and_sentinel_and_untagged():
    # 1. Sentinel -1 router (openrouter/auto) -> MUST REJECT
    assert is_strictly_free({
        "id": "openrouter/auto",
        "pricing": {"prompt": "-1", "completion": "-1"}
    }) is False

    # 2. Paid model -> MUST REJECT
    assert is_strictly_free({
        "id": "anthropic/claude-3.7-sonnet",
        "pricing": {"prompt": "0.000003", "completion": "0.000015"}
    }) is False

    # 3. Sneaky model with :free suffix but non-zero request/image price -> MUST REJECT
    assert is_strictly_free({
        "id": "sneaky/model:free",
        "pricing": {"prompt": "0", "completion": "0", "request": "0.01"}
    }) is False

    # 4. Preview model with $0 pricing but NO :free suffix -> MUST REJECT
    assert is_strictly_free({
        "id": "google/lyria-3-pro-preview",
        "pricing": {"prompt": "0", "completion": "0"}
    }) is False

    # 5. Missing pricing object -> MUST REJECT
    assert is_strictly_free({"id": "google/gemma-4-31b-it:free"}) is False


def test_is_strictly_free_accepts_verified_free_models():
    assert is_strictly_free({
        "id": "openrouter/free",
        "pricing": {"prompt": "0", "completion": "0"}
    }) is True

    assert is_strictly_free({
        "id": "nvidia/nemotron-3.5-lightning:free",
        "pricing": {"prompt": "0", "completion": "0", "request": None, "image": "0"}
    }) is True

    assert is_strictly_free({
        "id": "google/gemma-4-31b-it:free",
        "pricing": {"prompt": "0", "completion": "0"}
    }) is True


def test_classify_catalog_into_6_stages_and_priority_order():
    mock_catalog = [
        {
            "id": "openrouter/auto",
            "pricing": {"prompt": "-1", "completion": "-1"},
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}
        },
        {
            "id": "google/gemma-4-31b-it:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text", "image", "video"], "output_modalities": ["text"]}
        },
        {
            "id": "nvidia/nemotron-3.5-lightning:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}
        },
        {
            "id": "nvidia/nemotron-3.5-super-vl:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text", "image", "video"], "output_modalities": ["text"]}
        },
        {
            "id": "recraft/recraft-v4.1-flash-v2:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}
        },
        {
            "id": "fish-audio/s2.1-pro-free:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"], "output_modalities": ["speech"]}
        },
        {
            "id": "openrouter/free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]}
        },
    ]

    stages = classify_catalog_into_stages(mock_catalog)

    assert stages["text"][0] == "nvidia/nemotron-3.5-lightning:free"
    assert "google/gemma-4-31b-it:free" in stages["text"]
    assert stages["text"][-1] == "openrouter/free"
    assert "openrouter/auto" not in stages["text"]

    assert stages["vision"][0] == "nvidia/nemotron-3.5-super-vl:free"
    assert "google/gemma-4-31b-it:free" in stages["vision"]

    assert stages["image"] == ["recraft/recraft-v4.1-flash-v2:free"]
    assert stages["speech"] == ["fish-audio/s2.1-pro-free:free"]

    assert stages["audio"] == []
    assert stages["video"] == []


def test_circuit_breaker_cooldown_on_402_and_429():
    reset_circuit_breaker()
    assert is_openrouter_on_cooldown() is False

    record_openrouter_status(429, "Rate limit exceeded")
    assert is_openrouter_on_cooldown() is True

    reset_circuit_breaker()
    record_openrouter_status(402, "Payment required / daily free limit reached")
    assert is_openrouter_on_cooldown() is True

    reset_circuit_breaker()
    assert is_openrouter_on_cooldown() is False


def test_free_visuals_video_stage_auto_skips_when_no_free_video_model(monkeypatch):
    from backend.engine import free_visuals
    monkeypatch.setattr("backend.engine.openrouter_discovery.get_free_models_for", lambda cap, force_refresh=False: [])
    res = free_visuals.check_openrouter_video_stage()
    assert res["status"] == "auto_skip_to_local"
    assert res["openrouter_calls_made"] == 0


def test_audio_subs_music_stage_auto_skips_when_no_free_audio_model(monkeypatch):
    from backend.engine.audio_subs import resolve_music_sfx_stage
    monkeypatch.setattr("backend.engine.openrouter_discovery.get_free_models_for", lambda cap, force_refresh=False: [])
    res = resolve_music_sfx_stage()
    assert res["status"] == "auto_skip_to_local"
    assert res["openrouter_calls_made"] == 0


@pytest.mark.asyncio
async def test_brain_openrouter_free_engine_mode_and_gemini_35_candidates(monkeypatch):
    from backend.engine import brain
    assert "models/gemini-3.5-flash-lite" in brain.GEMINI_FREE_CANDIDATE_MODELS
    assert "models/gemini-3.5-flash" in brain.GEMINI_FREE_CANDIDATE_MODELS

    async def fake_call_or(prompt, system_prompt=None, format_json=True, timeout=25.0):
        return '{"ok": true, "provider": "openrouter_free"}'

    monkeypatch.setattr(brain, "call_openrouter_free", fake_call_or)
    out = await brain.ask_brain("Test prompt", format_json=True, engine_mode="openrouter_free")
    assert '"provider": "openrouter_free"' in out


@pytest.mark.asyncio
async def test_copilot_openrouter_capabilities_endpoint():
    from backend.api.copilot import get_openrouter_capabilities
    report = await get_openrouter_capabilities()
    assert report["strict_zero_cost_lock"] is True
    assert "stages" in report
    for stage in ("text", "vision", "image", "speech", "audio", "video"):
        assert stage in report["stages"]
        assert "local_fallback_engine" in report["stages"][stage]
