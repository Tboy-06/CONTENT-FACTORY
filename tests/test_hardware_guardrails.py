import asyncio
import json
import os
import shutil

from backend.engine.assembler import (
    JOBS_SCRATCH_ROOT,
    build_xfade_filter_chain,
    clear_active_render_lock,
    enforce_lru_cache_cap,
    get_job_scratch_dir,
    get_optimal_h264_encoder_args,
    is_render_job_active,
    set_active_render_lock,
)
from backend.engine.audio_subs import resolve_kokoro_model_paths
from backend.engine.brain import unload_local_brain
from backend.api.copilot import rollback_job_manifest, save_manifest_history_snapshot


def test_job_scratch_dir_on_c_drive():
    j_dir = get_job_scratch_dir(999901)
    assert os.path.abspath(j_dir).lower().startswith(os.path.abspath(JOBS_SCRATCH_ROOT).lower())
    assert os.path.exists(j_dir)
    shutil.rmtree(j_dir, ignore_errors=True)


def test_lru_cache_cap_enforcement():
    res = enforce_lru_cache_cap(500.0)
    assert res["max_cap_mb"] == 500.0
    assert res["remaining_mb"] <= 500.0


def test_ffmpeg_threads_and_act_break_xfade_cap():
    enc_args = get_optimal_h264_encoder_args()
    assert "-threads" in enc_args
    assert "4" in enc_args
    assert "-preset" in enc_args
    assert "veryfast" in enc_args

    # 16 beats should be capped to at most 4 xfade transitions (Act breaks only)
    beats = [
        {"id": f"b{i:02d}", "duration": 2.0, "act_break": (i in (4, 8, 12))}
        for i in range(16)
    ]
    chain = build_xfade_filter_chain(beats, max_transitions=4)
    assert chain.count("xfade=") <= 4
    assert "vignette=PI/6[vxf]" in chain


def test_active_render_lock_harvester_pause_signal():
    clear_active_render_lock()
    assert not is_render_job_active()
    set_active_render_lock(77, stage="FFMPEG_PASS2")
    assert is_render_job_active()
    clear_active_render_lock()
    assert not is_render_job_active()


def test_unload_local_brain_and_kokoro_int8_weights():
    assert unload_local_brain() is True
    kokoro_paths = resolve_kokoro_model_paths()
    assert kokoro_paths is not None
    onnx_p, voices_p = kokoro_paths
    assert os.path.exists(onnx_p)
    assert os.path.exists(voices_p)


def test_manifest_history_snapshot_and_rollback():
    test_job_id = 999902
    j_dir = get_job_scratch_dir(test_job_id)
    try:
        m_v1 = {"job_id": test_job_id, "topic": "Original Timeline", "beats": [{"id": "b01", "headline": "ORIG"}]}
        snap1 = save_manifest_history_snapshot(test_job_id, m_v1, action_label="before_edit_1")
        assert os.path.exists(snap1) and snap1.endswith("v1.json")

        m_v2 = {"job_id": test_job_id, "topic": "Edited Timeline", "beats": [{"id": "b01", "headline": "EDITED"}]}
        with open(os.path.join(j_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(m_v2, f)

        res = asyncio.run(rollback_job_manifest(test_job_id, version=1, re_render=False))
        assert res["status"] == "success"
        assert res["restored_version"] == 1
        assert res["manifest"]["topic"] == "Original Timeline"
    finally:
        shutil.rmtree(j_dir, ignore_errors=True)
