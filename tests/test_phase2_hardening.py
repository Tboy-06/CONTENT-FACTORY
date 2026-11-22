import asyncio
import inspect
import json
import os
import shutil
import subprocess
import zipfile
from types import SimpleNamespace
import pytest

from backend.main import app
from backend.vault.models import JobStatus
import backend.vault as vault_pkg
from backend.vault import repository
from backend.engine import assembler, brain


def test_phase1_leftovers_and_hidden_crashes():
    # 1. Confirm frontend/backend is completely deleted
    assert not os.path.exists(r"D:\CONTENT-FACTORY\frontend\backend")

    # 2. Confirm duplicate jobs_router mount at /api is removed (only /api/jobs/... exists for job routes)
    duplicate_publish_routes = [
        r for r in app.routes if getattr(r, "path", "") == "/api/{job_id}/publish"
    ]
    assert len(duplicate_publish_routes) == 0

    # 3. Confirm update_asset_metadata and find_hook_formula are in repository and exported in backend.vault
    assert hasattr(repository, "update_asset_metadata")
    assert hasattr(vault_pkg, "update_asset_metadata")
    assert hasattr(repository, "find_hook_formula")
    assert hasattr(vault_pkg, "find_hook_formula")

    # 4. Confirm JobStatus.AWAITING_PREMIUM exists
    assert JobStatus.AWAITING_PREMIUM.value == "awaiting_premium"

    # 5. Confirm AnalystAgent._update_hook_formulas uses find_hook_formula (not 1-arg get_hook_formula with 2 args)
    from backend.agents.analyst import AnalystAgent
    src = inspect.getsource(AnalystAgent._update_hook_formulas)
    assert "find_hook_formula(" in src
    assert "get_hook_formula(niche," not in src

    # 6. Confirm database.py configures WAL mode and busy_timeout=5000
    from backend.vault import database
    db_src = inspect.getsource(database)
    assert "journal_mode=WAL" in db_src
    assert "busy_timeout=5000" in db_src

    # 7. Confirm ask_brain enforces overall <= 45s timeout budget
    assert getattr(brain, "MAX_BRAIN_DEADLINE_SECS", 0) == 45.0


def test_google_genai_v3_migration():
    from backend.agents import llm_client
    from backend.tools import gemini_vision

    for mod in (llm_client, gemini_vision, brain):
        src = inspect.getsource(mod)
        assert "google.generativeai" not in src, f"Deprecated google.generativeai still in {mod.__name__}"

    req_txt = open(r"D:\CONTENT-FACTORY\requirements.txt", encoding="utf-8").read()
    assert "google-generativeai" not in req_txt
    assert "google-genai" in req_txt


@pytest.mark.asyncio
async def test_beat_sha256_cache_and_ffmpeg_semaphore_and_e2e_video():
    assert hasattr(assembler, "_FFMPEG_SEMAPHORE")
    assert isinstance(assembler._FFMPEG_SEMAPHORE, asyncio.Semaphore)
    assert hasattr(assembler, "compute_beat_render_hash")

    test_job_dir = r"C:\cf_training\temp\test_e2e_phase2_job"
    shutil.rmtree(test_job_dir, ignore_errors=True)
    os.makedirs(test_job_dir, exist_ok=True)

    beat1 = {
        "id": "beat_01",
        "type": "motion_card",
        "template": "red_slam_word",
        "headline": "PHASE 2 TEST",
        "highlight": "SHA256 CACHE",
        "duration": 1.0,
        "aspect_ratio": "9:16",
        "genre": "crime_doc",
        "sfx": "thud.wav",
    }
    beat2 = {
        "id": "beat_02",
        "type": "declassified_scan",
        "headline": "DECLASSIFIED RECORD",
        "text": "VERIFIED E2E SMOKE TEST DOCUMENTARY PAYLOAD",
        "highlight": "VERIFIED E2E",
        "duration": 1.0,
        "aspect_ratio": "9:16",
        "genre": "crime_doc",
        "sfx": "click.wav",
    }

    h1 = assembler.compute_beat_render_hash(beat1)
    h2 = assembler.compute_beat_render_hash(beat2)
    assert len(h1) == 64 and len(h2) == 64 and h1 != h2

    # Remove any prior cached file for h1 to test fresh render -> cache hit
    cache_mp4_1 = os.path.join(assembler.BEAT_CACHE_DIR, f"{h1}.mp4")
    if os.path.exists(cache_mp4_1):
        os.remove(cache_mp4_1)

    # First Pass 1 run: renders via FFmpeg and populates cache
    out1 = await assembler.render_beat_pass1(beat1, test_job_dir)
    assert os.path.exists(out1) and os.path.getsize(out1) > 0
    assert beat1.get("_cache_hit") is False
    assert os.path.exists(cache_mp4_1)

    # Second Pass 1 run with identical beat: must hit SHA-256 cache and skip FFmpeg
    out1_cached = await assembler.render_beat_pass1(beat1, test_job_dir)
    assert os.path.exists(out1_cached) and os.path.getsize(out1_cached) > 0
    assert beat1.get("_cache_hit") is True

    # Render Beat 2
    out2 = await assembler.render_beat_pass1(beat2, test_job_dir)
    assert os.path.exists(out2) and os.path.getsize(out2) > 0

    # Create a tiny valid captions.ass file
    ass_path = os.path.join(test_job_dir, "captions.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,380,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:00.00,0:00:01.80,Default,,0,0,0,,Phase 2 E2E Smoke Test\n"
        )

    manifest = {
        "job_id": 99902,
        "topic": "CIA Quantum Encryption",
        "actual_duration": 2.0,
        "total_duration": 2.0,
        "captions_ass_path": ass_path,
        "beats": [beat1, beat2],
    }
    with open(os.path.join(test_job_dir, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf)

    final_mp4 = os.path.join(test_job_dir, "final_9x16.mp4")
    ok = await assembler.assemble_final_pass2(manifest, test_job_dir, final_mp4)
    assert ok is True
    assert os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 1000

    # Verify via ffprobe that video + audio streams exist and duration > 0s
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", final_mp4,
    ]
    res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
    assert res.returncode == 0
    probe_data = json.loads(res.stdout)
    streams = probe_data.get("streams", [])
    codec_types = {s.get("codec_type") for s in streams}
    assert "video" in codec_types
    assert "audio" in codec_types
    dur = float(probe_data.get("format", {}).get("duration") or 0.0)
    assert dur > 0.5


@pytest.mark.asyncio
async def test_export_pack_zip_bundle(monkeypatch):
    from backend.api.jobs import build_job_export_zip

    test_job_dir = r"C:\cf_training\temp\test_e2e_phase2_job"
    final_mp4 = os.path.join(test_job_dir, "final_9x16.mp4")
    ass_path = os.path.join(test_job_dir, "captions.ass")

    async def fake_get_job(job_id: int):
        return SimpleNamespace(
            id=job_id,
            niche="CIA Quantum Encryption",
            status=JobStatus.COMPLETED,
            current_stage="READY_TO_PUBLISH",
            config_json={"genre": "crime_doc", "format": "9:16"},
        )

    async def fake_get_job_assets(job_id: int):
        return [
            SimpleNamespace(
                id=1,
                asset_type="VIDEO",
                path=final_mp4,
                metadata_json={
                    "title": "CIA Quantum Encryption",
                    "hook": "The documented history behind CIA Quantum Encryption.",
                    "captions_ass_path": ass_path,
                },
            )
        ]

    monkeypatch.setattr("backend.api.jobs.repository.get_job", fake_get_job)
    monkeypatch.setattr("backend.api.jobs.repository.get_job_assets", fake_get_job_assets)

    zip_path = await build_job_export_zip(99902, job_dir_override=test_job_dir)
    assert os.path.exists(zip_path)
    assert zip_path.startswith(r"C:\cf_training\exports")

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert "final_9x16.mp4" in names
        assert "captions.ass" in names
        assert "captions.srt" in names
        assert "upload_copy.txt" in names
        copy_txt = zf.read("upload_copy.txt").decode("utf-8")
        assert "CIA Quantum Encryption" in copy_txt
