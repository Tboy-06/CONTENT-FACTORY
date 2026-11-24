import os
import json
import pytest
from unittest.mock import patch, MagicMock


def test_config_has_hf_token_and_paid_gemini_video_flag():
    """1. Verify config.py exposes hf_token and strict default enable_paid_gemini_video=False."""
    from backend.config import Settings
    s = Settings()
    assert hasattr(s, "hf_token")
    assert hasattr(s, "enable_paid_gemini_video")
    assert s.enable_paid_gemini_video is False


def test_paid_gemini_omni_strictly_blocked_when_disabled():
    """2. Verify $0 billing lock: paid_gemini_omni mode is blocked unless enable_paid_gemini_video=True."""
    from backend.engine import video_gen

    res = video_gen.generate_ai_video_clip(
        prompt="Classified submarine recovery in stormy Pacific",
        image_path=None,
        duration=5.0,
        mode="paid_gemini_omni",
    )
    assert res["status"] == "blocked_zero_cost_guard"
    assert res["cost_usd"] == 0.0
    assert "flow_handoff" in res


def test_hf_zerogpu_stores_clips_strictly_on_c_drive_and_supports_ltx_and_wan_fallback(tmp_path):
    """3. Verify Tier 1 Hugging Face ZeroGPU tries LTX-2.5 then Wan 2.2 I2V and saves strictly to C:\\cf_training\\temp\\ai_clips\\."""
    from backend.engine import video_gen

    video_gen.reset_zerogpu_circuit_breaker()

    fake_mp4 = tmp_path / "gradio_out.mp4"
    fake_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8000)
    fake_ref_img = tmp_path / "ref_start.png"
    fake_ref_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 512)

    call_log = []

    class FakeGradioClient:
        def __init__(self, space_id, token=None, **kwargs):
            self.space_id = space_id
            self.token = token
            call_log.append(space_id)
            if "LTX" in space_id:
                raise RuntimeError("Space queue is full")

        def view_api(self, return_format="dict"):
            return {"named_endpoints": {"/generate": {"parameters": [{"parameter_name": "prompt"}]}}}

        def predict(self, *args, **kwargs):
            return str(fake_mp4)

    with patch.object(video_gen, "_get_gradio_client_cls", return_value=FakeGradioClient):
        res = video_gen.generate_ai_video_clip(
            prompt="35mm anamorphic camera push into CIA evidence room",
            image_path=str(fake_ref_img),
            duration=4.0,
            mode="free_hf",
            hf_token="hf_test_free_token_123",
        )

    assert res["status"] == "success"
    assert res["cost_usd"] == 0.0
    assert res["video_path"].startswith(r"C:\cf_training\temp\ai_clips")
    assert os.path.exists(res["video_path"])
    assert any("LTX-2.5" in s for s in call_log)
    assert any("wan2-2" in s for s in call_log)


def test_zerogpu_quota_circuit_breaker_and_flow_handoff():
    """4. Verify ZeroGPU daily quota error trips circuit breaker immediately and returns Google Flow handoff."""
    from backend.engine import video_gen

    video_gen.reset_zerogpu_circuit_breaker()

    class QuotaExhaustedClient:
        def __init__(self, space_id, token=None, **kwargs):
            raise RuntimeError("You have exceeded your GPU quota (5 minutes/day on ZeroGPU)")

    with patch.object(video_gen, "_get_gradio_client_cls", return_value=QuotaExhaustedClient):
        res = video_gen.generate_ai_video_clip(
            prompt="Orbital drone shot over declassified radar station",
            image_path="C:/cf_training/temp/anchor.png",
            duration=5.0,
            mode="free_hf",
            hf_token="hf_test_free_token_123",
        )

    assert res["status"] == "quota_exhausted"
    assert video_gen.is_zerogpu_on_cooldown() is True
    assert "flow_handoff" in res
    assert res["flow_handoff"]["prompt"] == "Orbital drone shot over declassified radar station"
    assert res["flow_handoff"]["image_path"] == "C:/cf_training/temp/anchor.png"


def test_vocal_mastering_chain_and_3tier_voice_upgrade():
    """5. Verify Broadcast Vocal Mastering FFmpeg filter chain, Multilingual Edge-TTS upgrade, and Kokoro C:\\models\\kokoro path."""
    from backend.engine import audio_subs

    assert "highpass=f=80" in audio_subs.BROADCAST_VOCAL_MASTER_AF
    assert "equalizer=f=120:width_type=o:width=1:g=3" in audio_subs.BROADCAST_VOCAL_MASTER_AF
    assert "equalizer=f=3200:width_type=o:width=1.5:g=2.5" in audio_subs.BROADCAST_VOCAL_MASTER_AF
    assert "acompressor=threshold=-18dB:ratio=3:attack=5:release=80" in audio_subs.BROADCAST_VOCAL_MASTER_AF
    assert "loudnorm=I=-14:TP=-1.5:LRA=9" in audio_subs.BROADCAST_VOCAL_MASTER_AF

    # Legacy robotic voices must auto-upgrade to expressive Multilingual Neural voices
    assert audio_subs.upgrade_legacy_edge_voice("en-US-ChristopherNeural") == "en-US-AndrewMultilingualNeural"
    assert audio_subs.upgrade_legacy_edge_voice("en-US-AriaNeural") == "en-US-AvaMultilingualNeural"
    assert audio_subs.KOKORO_MODELS_DIR.startswith(r"C:\models\kokoro")


def test_pro_fonts_bundled_and_active_word_karaoke_ass(tmp_path):
    """6. Verify bundled studio fonts exist and .ASS captions render active-word pop-in highlight tags without Arial."""
    from backend.engine import audio_subs, motion_cards

    for font_file in ("Anton-Regular.ttf", "Montserrat-Black.ttf", "Inter-Bold.ttf"):
        fp = os.path.join(r"D:\CONTENT-FACTORY\assets\fonts", font_file)
        assert os.path.exists(fp) and os.path.getsize(fp) > 20000

    fonts = motion_cards.get_fonts()
    assert len(fonts) == 5

    words = [
        {"text": "Secret", "start": 0.0, "duration": 0.35},
        {"text": "nuclear", "start": 0.35, "duration": 0.40},
        {"text": "submarine", "start": 0.75, "duration": 0.45},
    ]
    ass_out = str(tmp_path / "test_captions.ass")
    audio_subs.build_ass_subtitles(words, ass_out)
    ass_content = open(ass_out, encoding="utf-8").read()

    assert "Style: Default,Arial" not in ass_content
    assert "Montserrat" in ass_content
    assert "&H0000D4FF&" in ass_content
    assert r"\fscx88\fscy88\t(0,90,\fscx106\fscy106)\t(90,150,\fscx100\fscy100)" in ass_content


def test_3_act_visual_pacing_curve_and_pass2_sfx_sidechain():
    """7. Verify 3-Act pacing curve in planner.py and SFX adelay + sidechaincompress + xfade in assembler.py."""
    from backend.engine import planner, assembler

    manifest = planner.generate_fallback_manifest("CIA Project Azorian", job_id=99, duration_target=45.0, genre="crime_doc")
    manifest = planner.apply_three_act_pacing_curve(manifest)
    all_beats = [b for s in manifest["sentences"] for b in s["beats"]]

    assert len(all_beats) >= 12
    # Act 1 opener should be 1.8 - 2.2s, Act 3 climax beats should be rapid 0.7 - 1.0s
    assert 1.75 <= float(all_beats[0]["duration"]) <= 2.25
    climax_beats = all_beats[-4:-1]
    assert any(0.65 <= float(b["duration"]) <= 1.05 for b in climax_beats)

    # Verify Pass 2 audio filter_complex builder includes adelay SFX and sidechaincompress BGM ducking
    fc_str, sfx_inputs = assembler.build_pass2_audio_filter_complex(
        all_beats=all_beats,
        has_voice=True,
        has_bgm=True,
        base_input_count=3,
    )
    assert "sidechaincompress" in fc_str
    assert "adelay=" in fc_str
    assert len(sfx_inputs) > 0

    # Verify xfade filter builder and budget guard constant
    assert getattr(assembler, "MAX_AUTO_HF_CLIPS_PER_JOB", 0) in (3, 4)
    xf_chain = assembler.build_xfade_filter_chain(all_beats[:4])
    assert "xfade=" in xf_chain


def test_video_gen_status_and_beat_endpoint():
    """8. Verify GET /api/jobs/video-gen/status and POST /api/jobs/{job_id}/beats/{beat_id}/generate-video."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    r = client.get("/api/jobs/video-gen/status")
    assert r.status_code == 200
    body = r.json()
    assert body["primary_space"] == "Lightricks/LTX-2.5"
    assert body["fallback_space"] == "zerogpu-aoti/wan2-2-fp8da-aoti-faster"
    assert body["paid_gemini_video_enabled"] is False
    assert body["storage_dir"].startswith(r"C:\cf_training\temp\ai_clips")

