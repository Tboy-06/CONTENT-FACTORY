import asyncio
import json
import pytest
from fastapi import HTTPException

from backend.engine.vault_graph import format_topic_title, detect_genre as vg_detect_genre
from backend.engine.planner import detect_genre as planner_detect_genre, generate_fallback_manifest
from backend.engine.researcher import research_fact_dossier
from backend.engine.thumbnail_engine import generate_ab_titles
from backend.api.settings import mask_secret
from backend.api.copilot import validate_safe_video_path
from backend.main import app


def test_acronym_preserving_title():
    raw = "how the cia and fbi used ai and llm systems at nasa in the usa"
    formatted = format_topic_title(raw)
    assert "CIA" in formatted
    assert "FBI" in formatted
    assert "AI" in formatted
    assert "LLM" in formatted
    assert "NASA" in formatted
    assert "USA" in formatted
    assert "Cia" not in formatted
    assert "Ai" not in formatted


def test_detect_genre_deduplicated():
    assert planner_detect_genre is vg_detect_genre
    assert planner_detect_genre("CIA covert submarine heist") == "crime_doc"
    assert planner_detect_genre("funny awkward comedy skit") == "comedy_skit"
    assert planner_detect_genre("explosive high speed car chase battle") == "action_hype"
    assert planner_detect_genre("35mm anamorphic cinema film scene") == "movie_cinema"
    assert planner_detect_genre("how to build an AI system step by step") == "viral_edu"


@pytest.mark.asyncio
async def test_researcher_zero_fabricated_facts(monkeypatch):
    # Force offline/empty external lookups so fallback path is tested
    monkeypatch.setattr("backend.engine.researcher._fetch_json", lambda url, timeout=5.0: None)
    monkeypatch.setattr("backend.engine.researcher._search_yt_dlp_facts", lambda topic, max_results=2: [])

    dossier = await research_fact_dossier("cia quantum encryption")
    assert dossier["canonical_title"] == "CIA Quantum Encryption"
    assert dossier["verification_status"] == "UNVERIFIED"
    assert dossier["key_metrics"] == []
    assert dossier["key_dates"] == []
    assert dossier["coordinates"] == "UNVERIFIED"
    assert dossier["verified_quote"] == "UNVERIFIED"
    assert isinstance(dossier.get("claims"), list)

    dumped = json.dumps(dossier)
    for forbidden in ["$3.8 Billion", "99.8%", "14,000 Personnel", "10X Acceleration", "38.8977", "1974", "1992", "Central Intelligence"]:
        assert forbidden not in dumped


def test_fallback_manifest_unverified_draft_has_no_fake_numbers():
    manifest = generate_fallback_manifest("cia quantum encryption", job_id=101, duration_target=45.0, fact_dossier={})
    assert manifest["topic"] == "CIA Quantum Encryption"
    assert manifest["unverified_draft"] is True
    assert manifest["verification_status"] == "UNVERIFIED_DRAFT"

    dumped = json.dumps(manifest)
    for forbidden in [
        "$20,000,000",
        "$3.8 Billion",
        "38.8977",
        "1974",
        "99.8%",
        "OVER 90% EXPONENTIAL",
        "10X ACCELERATION",
        "Most people completely misunderstand",
        "FAILED IN 42 SECONDS",
    ]:
        assert forbidden not in dumped

    ab_titles = generate_ab_titles("CIA Quantum Encryption", {})
    ab_dumped = " ".join(ab_titles)
    assert "$3.8" not in ab_dumped
    assert "1974" not in ab_dumped


def test_cors_locked_to_localhost():
    cors_mw = None
    for mw in app.user_middleware:
        if "CORSMiddleware" in str(mw.cls):
            cors_mw = mw
            break
    assert cors_mw is not None
    origins = cors_mw.kwargs.get("allow_origins", [])
    assert "*" not in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_settings_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret(None) == ""
    masked = mask_secret("sk-or-v1-1234567890abcdef")
    assert masked.startswith("****")
    assert masked.endswith("cdef")
    assert "1234567890" not in masked


def test_validate_safe_video_path_rejects_traversal():
    with pytest.raises(HTTPException) as exc1:
        validate_safe_video_path("../../Windows/System32/cmd.exe")
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        validate_safe_video_path(r"C:\Windows\win.ini")
    assert exc2.value.status_code == 400

    with pytest.raises(HTTPException) as exc3:
        validate_safe_video_path(r"C:\cf_training\temp\uploads\malicious.exe")
    assert exc3.value.status_code == 400


def test_brain_locks_and_shutdown_hooks():
    from backend.engine import brain, openrouter_discovery
    assert hasattr(brain, "_LOCAL_BRAIN_LOCK")
    assert hasattr(brain, "shutdown_local_brain")
    assert callable(brain.shutdown_local_brain)
    assert hasattr(openrouter_discovery, "_STATE_LOCK")


@pytest.mark.asyncio
async def test_publish_job_refuses_fake_published_without_provider(monkeypatch):
    from types import SimpleNamespace
    from backend.api.jobs import publish_job, PublishRequest

    recorded_stages = []

    async def fake_get_job(job_id: int):
        return SimpleNamespace(id=job_id, niche="CIA Quantum Encryption")

    async def fake_update_job_status(job_id: int, status, current_stage=None):
        recorded_stages.append((job_id, status, current_stage))
        return True

    monkeypatch.setattr("backend.api.jobs.repository.get_job", fake_get_job)
    monkeypatch.setattr("backend.api.jobs.repository.update_job_status", fake_update_job_status)
    monkeypatch.setenv("POSTIZ_API_KEY", "")

    res = await publish_job(42, PublishRequest(platforms=["YouTube Shorts", "TikTok"]))
    assert res["status"] == "READY_TO_PUBLISH"
    assert res["published"] is False
    assert res["post_id"] is None
    assert recorded_stages[-1][2] == "READY_TO_PUBLISH"
    assert recorded_stages[-1][2] != "PUBLISHED"

