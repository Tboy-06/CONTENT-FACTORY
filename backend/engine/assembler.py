"""
CONTENT-FACTORY Engine: 2-Pass FFmpeg Documentary Assembler
-----------------------------------------------------------
Pass 1: Renders individual beats into beat_XX.mp4 with cosine zoompan,
        documentary color treatments (B&W/Teal/Amber), and transition SFX.
Pass 2: Stitches beats + mixes SFX audio + voiceover + ducked BGM + burns .ASS captions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from backend.engine.ev1_treat import (
    apply_color_grade,
    build_cosine_zoompan_filter,
    build_snap_zoom_filter,
    build_camera_shake_filter,
    build_cinema_anamorphic_bars
)
from backend.engine.motion_cards import render_motion_card
import backend.engine.visual_cortex as visual_cortex
import backend.engine.free_visuals as free_visuals
import backend.engine.forensic_canvas as forensic_canvas
import backend.engine.depth_cortex as depth_cortex
import backend.engine.zero_gpu_hook as zero_gpu_hook
from backend.engine.reflexion import audit_and_heal_beats, log_system_fallback

logger = logging.getLogger("engine.assembler")

# 16 GB Laptop Thermal & Concurrency Guard: serialize heavy FFmpeg encodes
_FFMPEG_SEMAPHORE = asyncio.Semaphore(1)

# Beat-Level SHA-256 Render Cache & Scratch Directories on C: drive (0 MB bloat on 8 GB D: partition)
BEAT_CACHE_DIR = r"C:\cf_training\temp\beat_cache"
AI_CLIPS_CACHE_DIR = r"C:\cf_training\temp\ai_clips"
EXPORTS_CACHE_DIR = r"C:\cf_training\exports"
JOBS_SCRATCH_ROOT = r"C:\cf_training\jobs"
ACTIVE_RENDER_LOCK_FILE = r"C:\cf_training\temp\active_render.lock"
MAX_TEMP_CACHE_MB = 500.0

for _d in (BEAT_CACHE_DIR, AI_CLIPS_CACHE_DIR, EXPORTS_CACHE_DIR, JOBS_SCRATCH_ROOT):
    os.makedirs(_d, exist_ok=True)

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
_QSV_AVAILABLE: Optional[bool] = None
FFMPEG_THREADS = "4"

# ZeroGPU Budget Guard: cap automatic ZeroGPU AI video calls to top 3 hero beats per job
MAX_AUTO_HF_CLIPS_PER_JOB = 3
_JOB_HF_CLIP_COUNTS: Dict[str, int] = {}
FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts"))
SFX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sfx"))


def get_job_scratch_dir(job_id: int | str) -> str:
    """
    Returns the job working directory on C:\\cf_training\\jobs\\<job_id>
    so intermediate beat clips, raw sentence MP3s, and stitched_temp.mp4 never touch the 8 GB D: drive.
    Automatically migrates any legacy D:\\CONTENT-FACTORY\\jobs\\<job_id> directory if present.
    """
    target_dir = os.path.join(JOBS_SCRATCH_ROOT, str(job_id))
    legacy_dir = os.path.abspath(os.path.join("jobs", str(job_id)))
    if os.path.exists(legacy_dir) and os.path.abspath(legacy_dir) != os.path.abspath(target_dir):
        try:
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            if not os.path.exists(target_dir):
                shutil.move(legacy_dir, target_dir)
            else:
                shutil.copytree(legacy_dir, target_dir, dirs_exist_ok=True)
                shutil.rmtree(legacy_dir, ignore_errors=True)
        except Exception as e:
            logger.debug(f"[assembler] Legacy job dir migration note: {e}")
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def set_active_render_lock(job_id: int | str, stage: str = "FFMPEG") -> None:
    """Signals the background dataset harvester to auto-pause while a video render job is active."""
    try:
        os.makedirs(os.path.dirname(ACTIVE_RENDER_LOCK_FILE), exist_ok=True)
        with open(ACTIVE_RENDER_LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump({"job_id": str(job_id), "stage": stage, "timestamp": os.path.getmtime(os.path.dirname(ACTIVE_RENDER_LOCK_FILE))}, f)
    except Exception:
        pass


def clear_active_render_lock() -> None:
    """Clears the active render lock so the background dataset harvester can resume."""
    try:
        if os.path.exists(ACTIVE_RENDER_LOCK_FILE):
            os.remove(ACTIVE_RENDER_LOCK_FILE)
    except Exception:
        pass


def is_render_job_active(max_stale_seconds: float = 900.0) -> bool:
    """Returns True if a video render is currently active (lock file present and younger than 15 minutes)."""
    if not os.path.exists(ACTIVE_RENDER_LOCK_FILE):
        return False
    try:
        import time
        age = time.time() - os.path.getmtime(ACTIVE_RENDER_LOCK_FILE)
        if age > max_stale_seconds:
            os.remove(ACTIVE_RENDER_LOCK_FILE)
            return False
        return True
    except Exception:
        return False


def get_optimal_h264_encoder_args() -> List[str]:
    """
    16 GB Laptop / Intel UHD 620 Thermal & CPU Throttling Helper:
    - Always caps FFmpeg encoding threads to `-threads 4` and `-preset veryfast` so Windows and Chrome stay responsive.
    - Optionally uses Intel QuickSync (`h264_qsv`) when `CF_ENABLE_QSV=1` and hardware QSV probe succeeds;
      otherwise uses `libx264 -preset veryfast -threads 4`.
    """
    global _QSV_AVAILABLE
    if os.environ.get("CF_ENABLE_QSV", "0").strip() == "1":
        if _QSV_AVAILABLE is None:
            try:
                probe = subprocess.run(
                    [
                        "ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1",
                        "-c:v", "h264_qsv", "-f", "null", "-"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=4,
                    creationflags=_NO_WIN,
                )
                _QSV_AVAILABLE = (probe.returncode == 0)
            except Exception:
                _QSV_AVAILABLE = False
        if _QSV_AVAILABLE:
            return ["-c:v", "h264_qsv", "-preset", "veryfast", "-threads", FFMPEG_THREADS]
    return ["-c:v", "libx264", "-preset", "veryfast", "-threads", FFMPEG_THREADS]


def enforce_lru_cache_cap(max_mb: float = MAX_TEMP_CACHE_MB) -> Dict[str, Any]:
    """
    Enforces a hard 500 MB LRU cache ceiling across C:\\cf_training\\temp\\beat_cache,
    C:\\cf_training\\temp\\ai_clips, C:\\cf_training\\exports, and local temp/.
    Evicts oldest files first whenever total size exceeds `max_mb`.
    """
    cache_dirs = [BEAT_CACHE_DIR, AI_CLIPS_CACHE_DIR, EXPORTS_CACHE_DIR, os.path.abspath("temp")]
    entries: List[tuple[float, int, str]] = []
    total_bytes = 0

    for d in cache_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for fname in files:
                if fname == "active_render.lock":
                    continue
                fp = os.path.join(root, fname)
                try:
                    st = os.stat(fp)
                    entries.append((st.st_mtime, st.st_size, fp))
                    total_bytes += st.st_size
                except OSError:
                    pass

    max_bytes = int(max_mb * 1024 * 1024)
    evicted_bytes = 0
    evicted_count = 0

    if total_bytes > max_bytes:
        # Sort oldest mtime first (Least Recently Used)
        entries.sort(key=lambda x: x[0])
        for _, fsize, fpath in entries:
            if total_bytes - evicted_bytes <= max_bytes:
                break
            try:
                os.remove(fpath)
                evicted_bytes += fsize
                evicted_count += 1
            except OSError:
                pass

    remaining_mb = round(max(0, total_bytes - evicted_bytes) / (1024 * 1024), 2)
    return {
        "total_before_mb": round(total_bytes / (1024 * 1024), 2),
        "remaining_mb": remaining_mb,
        "evicted_mb": round(evicted_bytes / (1024 * 1024), 2),
        "evicted_count": evicted_count,
        "max_cap_mb": max_mb,
    }


def compute_beat_render_hash(beat: Dict[str, Any], fps: int = 30) -> str:
    """
    Computes a deterministic SHA-256 hash over a beat's visual and audio render parameters.
    Enables Pass 1 to skip FFmpeg completely when an identical beat has already been rendered.
    """
    payload = {
        "type": beat.get("type", "treated_image"),
        "template": beat.get("template", ""),
        "headline": beat.get("headline", ""),
        "highlight": beat.get("highlight", ""),
        "prompt": beat.get("prompt", ""),
        "visual_prompt": beat.get("visual_prompt", ""),
        "text": beat.get("text", ""),
        "grade": beat.get("grade", "hard_bw"),
        "duration": round(float(beat.get("duration", 1.5)), 2),
        "camera_movement": beat.get("camera_movement", "push_in"),
        "aspect_ratio": beat.get("aspect_ratio", "9:16"),
        "genre": beat.get("genre", "crime_doc"),
        "broll_query": beat.get("broll_query", ""),
        "coords": beat.get("coords", ""),
        "location": beat.get("location", ""),
        "nodes": beat.get("nodes", []),
        "sfx": beat.get("sfx", "whoosh.wav"),
        "snap_zoom": bool(beat.get("snap_zoom")),
        "camera_shake": bool(beat.get("camera_shake")),
        "anamorphic_bars": bool(beat.get("anamorphic_bars")),
        "custom_media": beat.get("custom_media", ""),
        "fps": int(fps),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _fetch_archival_image(prompt: str, target_path: str, width: int = 720, height: int = 1280, timeout: float = 6.0) -> bool:
    """Fetches high-quality image from Pollinations Flux with fast timeout."""
    try:
        clean_prompt = prompt.strip()[:180]
        encoded = urllib.parse.quote(f"{clean_prompt}, documentary archival 35mm film still")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true&seed=42"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(target_path, "wb") as f:
            f.write(resp.read())
        if os.path.exists(target_path) and os.path.getsize(target_path) > 5000:
            return True
    except Exception as e:
        logger.warning(f"[assembler] Cloud image fetch skipped ({e}), using archival fallback")
        try:
            log_system_fallback(
                service_name="pollinations_flux",
                context_topic=clean_prompt[:30],
                failed_params={"prompt": clean_prompt[:60], "width": width, "height": height},
                fallback_used="local_cinematic_gradient",
                error_message=str(e)
            )
        except Exception:
            pass
    return False


async def render_beat_pass1(
    beat: Dict[str, Any],
    job_dir: str,
    fps: int = 30
) -> str:
    """Pass 1: Renders a single beat to beat_XX.mp4 with 9:16 vertical or 16:9 horizontal framing, zoom, and transition SFX."""
    beat_id = beat["id"]
    duration = float(beat.get("duration", 1.5))
    aspect_ratio = beat.get("aspect_ratio", "9:16")

    # Dimensions: 16:9 (1920x1080) for YouTube channel vs 9:16 (1080x1920) for Shorts
    if aspect_ratio == "16:9":
        out_w, out_h = 1920, 1080
        fetch_w, fetch_h = 1280, 720
    else:
        out_w, out_h = 1080, 1920
        fetch_w, fetch_h = 720, 1280

    beats_dir = os.path.join(job_dir, "beats")
    os.makedirs(beats_dir, exist_ok=True)
    os.makedirs(BEAT_CACHE_DIR, exist_ok=True)

    beat_hash = compute_beat_render_hash(beat, fps=fps)
    beat["render_hash"] = beat_hash
    local_hash_mp4 = os.path.join(beats_dir, f"{beat_hash}.mp4")
    global_cache_mp4 = os.path.join(BEAT_CACHE_DIR, f"{beat_hash}.mp4")

    plate_path = os.path.join(beats_dir, f"{beat_id}_plate.png")
    raw_img_path = os.path.join(beats_dir, f"{beat_id}_raw.jpg")
    out_mp4 = os.path.join(beats_dir, f"{beat_id}.mp4")

    # 0. Beat-Level SHA-256 Render Cache Check (skips FFmpeg Pass 1 in ~0ms on cache hit)
    if not beat.get("_force_reroll"):
        for cached_candidate in (local_hash_mp4, global_cache_mp4):
            if os.path.exists(cached_candidate) and os.path.getsize(cached_candidate) > 500:
                if os.path.abspath(cached_candidate) != os.path.abspath(out_mp4):
                    shutil.copy2(cached_candidate, out_mp4)
                if not os.path.exists(local_hash_mp4):
                    try:
                        shutil.copy2(cached_candidate, local_hash_mp4)
                    except Exception:
                        pass
                beat["rendered_path"] = out_mp4
                beat["_cache_hit"] = True
                logger.info(f"[assembler] Pass 1 SHA-256 CACHE HIT for {beat_id} ({beat_hash[:12]}) -> {out_mp4}")
                return out_mp4

    beat["_cache_hit"] = False
    beat.pop("_force_reroll", None)

    # 1. Zero-Cost Visual Cortex Media Ingestion (3 Tiers)
    custom_media = beat.get("custom_media")
    is_video_input = False
    video_source_path = None
    reuse_existing_plate = os.path.exists(plate_path) and not beat.get("_force_reroll") and not custom_media

    if reuse_existing_plate:
        logger.info(f"[assembler] Reusing existing plate: {plate_path}")
    elif custom_media and os.path.exists(custom_media):
        # Tier 3: Custom Hero Clip / Image Drop
        norm_output = os.path.join(beats_dir, f"{beat_id}_custom_norm.mp4" if custom_media.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')) else f"{beat_id}_plate.png")
        norm_res = visual_cortex.normalize_custom_media(custom_media, norm_output, aspect_ratio=aspect_ratio, duration=duration)
        if norm_res["type"] == "video" and norm_res["success"]:
            is_video_input = True
            video_source_path = norm_output
        else:
            plate_path = norm_output

    elif beat.get("type") in ("hero_hook", "ai_video") or (beat_id in ("b01", "beat_01") and duration <= 4.0):
        # Beat 1 Intro Priority:
        # 1. Try real HD moving Pexels B-Roll video first (100% real camera footage, zero AI look)
        broll_dest = os.path.join(beats_dir, f"{beat_id}_broll.mp4")
        prompt = beat.get("visual_prompt") or beat.get("prompt", "cinematic documentary")
        broll_query = beat.get("broll_query") or " ".join(prompt.split()[:5])
        fetched_broll = await asyncio.to_thread(
            visual_cortex.fetch_pexels_broll,
            query=broll_query,
            output_path=broll_dest,
            aspect_ratio=aspect_ratio,
            duration=duration
        )
        if fetched_broll and os.path.exists(broll_dest):
            is_video_input = True
            video_source_path = broll_dest
        else:
            # 2. Try Serverless ZeroGPU Moving Video Clip (guarded by MAX_AUTO_HF_CLIPS_PER_JOB)
            used_hf_clips = _JOB_HF_CLIP_COUNTS.get(job_dir, 0)
            hero_dest = os.path.join(beats_dir, f"{beat_id}_zerogpu.mp4")
            hero_path = None
            if used_hf_clips < MAX_AUTO_HF_CLIPS_PER_JOB:
                _JOB_HF_CLIP_COUNTS[job_dir] = used_hf_clips + 1
                hero_path = await asyncio.to_thread(
                    zero_gpu_hook.generate_zero_gpu_hero_clip,
                    prompt=prompt,
                    output_path=hero_dest,
                    image_path=beat.get("reference_image") or beat.get("anchor_image_path"),
                    duration=duration,
                )
            if hero_path and os.path.exists(hero_dest):
                is_video_input = True
                video_source_path = hero_dest
            else:
                # 3. Fallback to natural color-graded documentary photojournalism plate via 6-stage free_visuals router
                intro_grade = beat.get("grade") or ("cinema_scope" if beat.get("genre") == "movie_cinema" else "teal_split")
                fetched = await asyncio.to_thread(
                    free_visuals.resolve_image_plate,
                    prompt=prompt,
                    output_path=raw_img_path,
                    width=fetch_w,
                    height=fetch_h
                )
                if fetched and os.path.exists(raw_img_path):
                    apply_color_grade(raw_img_path, plate_path, grade=intro_grade, target_width=out_w, target_height=out_h)
                else:
                    render_motion_card(
                        template="red_slam_word",
                        headline="BREAKING ARCHIVE",
                        highlight=prompt[:32],
                        output_path=plate_path,
                        width=out_w,
                        height=out_h
                    )

    elif beat.get("type") == "declassified_scan":
        # Engine 2: Forensic Canvas - Declassified CIA Dossier with yellow highlighter sweep
        forensic_canvas.render_declassified_highlighter(
            headline=beat.get("headline", "CONFIDENTIAL INTELLIGENCE MEMORANDUM"),
            body_text=beat.get("text") or beat.get("prompt", "TOP SECRET EVIDENCE RECORD"),
            highlight_phrase=beat.get("highlight", beat.get("headline", "")),
            output_path=plate_path,
            width=out_w,
            height=out_h
        )

    elif beat.get("type") == "evidence_board":
        # Engine 2: Forensic Canvas - Investigation Pinboard with red connecting yarn
        forensic_canvas.render_evidence_board(
            headline=beat.get("headline", "NETWORK INVESTIGATION BOARD"),
            nodes=beat.get("nodes", []),
            output_path=plate_path,
            width=out_w,
            height=out_h
        )

    elif beat.get("type") == "map_flyover":
        # Engine 2: Forensic Canvas - Tactical Geopolitical Vector Map
        forensic_canvas.render_geopolitical_map(
            location_name=beat.get("location", beat.get("headline", "TARGET SECTOR")),
            coords=beat.get("coords", "45.1663° N, 28.7901° E"),
            headline=beat.get("headline", "GEOPOLITICAL TARGET"),
            output_path=plate_path,
            width=out_w,
            height=out_h
        )

    elif beat.get("type") == "motion_card":
        render_motion_card(
            template=beat.get("template", "red_slam_word"),
            headline=beat.get("headline", "CONFIDENTIAL"),
            highlight=beat.get("highlight", "EVIDENCE"),
            output_path=plate_path,
            width=out_w,
            height=out_h
        )

    elif beat.get("type") == "broll_video":
        # Tier 2: Free Moving B-Roll (Pexels / local slicer)
        broll_query = beat.get("broll_query") or beat.get("prompt", "cinematic documentary")
        broll_dest = os.path.join(beats_dir, f"{beat_id}_broll.mp4")
        fetched_broll = await asyncio.to_thread(
            visual_cortex.fetch_pexels_broll,
            query=broll_query,
            output_path=broll_dest,
            aspect_ratio=aspect_ratio,
            duration=duration
        )
        if fetched_broll and os.path.exists(broll_dest):
            is_video_input = True
            video_source_path = broll_dest
        else:
            # Fallback to Tier 1 Pollinations Flux
            prompt = beat.get("visual_prompt") or beat.get("prompt", "cinematic archival photo")
            fetched = await asyncio.to_thread(
                visual_cortex.fetch_pollinations_flux,
                prompt=prompt,
                output_path=raw_img_path,
                width=fetch_w,
                height=fetch_h
            )
            if fetched and os.path.exists(raw_img_path):
                apply_color_grade(raw_img_path, plate_path, grade=beat.get("grade", "hard_bw"))
            else:
                render_motion_card(
                    template="quote_box",
                    headline="ARCHIVAL EVIDENCE",
                    highlight=prompt[:45],
                    output_path=plate_path,
                    width=out_w,
                    height=out_h
                )
                apply_color_grade(plate_path, plate_path, grade=beat.get("grade", "hard_bw"))

    else:
        # Tier 1: Free AI Photorealistic Plates via Pollinations Flux ($0 spend, 0 API keys)
        grade = beat.get("grade", "hard_bw")
        prompt = beat.get("visual_prompt") or beat.get("prompt", "declassified intelligence document archival photo")

        fetched = await asyncio.to_thread(
            free_visuals.resolve_image_plate,
            prompt=prompt,
            output_path=raw_img_path,
            width=fetch_w,
            height=fetch_h
        )
        if fetched and os.path.exists(raw_img_path):
            apply_color_grade(raw_img_path, plate_path, grade=grade)
        else:
            render_motion_card(
                template="quote_box",
                headline="ARCHIVAL EVIDENCE",
                highlight=prompt[:45],
                output_path=plate_path,
                width=out_w,
                height=out_h
            )
            apply_color_grade(plate_path, plate_path, grade=grade)

    # 2. Build Video / Image Filter & Transition SFX
    total_frames = max(30, int(duration * fps))
    genre_type = (beat.get("genre") or "crime_doc").lower()
    cam_mov = (beat.get("camera_movement") or "push_in").lower()

    if "snap" in cam_mov or "punchline" in cam_mov or (genre_type == "comedy_skit" and beat.get("snap_zoom")):
        zoom_filter = f"{build_snap_zoom_filter(duration, zoom_factor=1.35, fps=fps, out_w=out_w, out_h=out_h)},trim=duration={duration}"
    elif "shake" in cam_mov or (genre_type == "action_hype" and beat.get("camera_shake")):
        zoom_filter = f"zoompan=z=1.08:d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},{build_camera_shake_filter(out_w=out_w, out_h=out_h, intensity=10)},trim=duration={duration}"
    elif "dolly" in cam_mov or "vertigo" in cam_mov:
        zoom_filter = f"zoompan=z='min(zoom+0.0020,1.24)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"
    elif "orbit" in cam_mov or "rotation" in cam_mov:
        zoom_filter = f"zoompan=z='1.15':d={total_frames}:x='(iw/2-(iw/zoom/2)) + sin(in/{total_frames}*3.14159)*50':y='(ih/2-(ih/zoom/2)) + cos(in/{total_frames}*3.14159)*25':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"
    elif "bokeh" in cam_mov or "focus" in cam_mov:
        zoom_filter = f"zoompan=z='min(zoom+0.0014,1.16)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},unsharp=5:5:0.8:5:5:0.0,trim=duration={duration}"
    else:
        zoom_filter = f"zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"

    # Movie/Cinema 2.35:1 anamorphic letterbox bars
    if genre_type == "movie_cinema" or beat.get("anamorphic_bars"):
        cinema_bars = build_cinema_anamorphic_bars(width=out_w, height=out_h, target_aspect=2.35)
        zoom_filter = f"{zoom_filter},{cinema_bars}"

    sfx_name = beat.get("sfx", "whoosh.wav")
    sfx_path = os.path.abspath(os.path.join("assets", "sfx", sfx_name))
    has_sfx = os.path.exists(sfx_path)

    enc_args = get_optimal_h264_encoder_args()
    if is_video_input:
        if has_sfx:
            cmd = [
                "ffmpeg", "-y",
                "-t", str(duration),
                "-i", video_source_path,
                "-i", sfx_path,
                "-filter_complex", f"[1:a]apad=whole_dur={duration},atrim=0:{duration}[a]",
                "-map", "0:v",
                "-map", "[a]",
                *enc_args,
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                out_mp4
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-t", str(duration),
                "-i", video_source_path,
                "-f", "lavfi", "-i", f"aevalsrc=0:d={duration}",
                "-map", "0:v",
                "-map", "1:a",
                *enc_args,
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-shortest",
                out_mp4
            ]
    else:
        if has_sfx:
            cmd = [
                "ffmpeg", "-y",
                "-i", plate_path,
                "-i", sfx_path,
                "-vf", zoom_filter,
                "-filter_complex", f"[1:a]apad=whole_dur={duration},atrim=0:{duration}[a]",
                "-map", "0:v",
                "-map", "[a]",
                *enc_args,
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                out_mp4
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", plate_path,
                "-f", "lavfi", "-i", f"aevalsrc=0:d={duration}",
                "-vf", zoom_filter,
                "-map", "0:v",
                "-map", "1:a",
                *enc_args,
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-shortest",
                out_mp4
            ]

    def _run_pass1():
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, creationflags=_NO_WIN)

    try:
        async with _FFMPEG_SEMAPHORE:
            await asyncio.to_thread(_run_pass1)
    except Exception as e:
        logger.error(f"[assembler] Pass 1 timed out or failed on {beat_id}: {e}")

    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 500:
        for cache_dest in (local_hash_mp4, global_cache_mp4):
            try:
                shutil.copy2(out_mp4, cache_dest)
            except Exception:
                pass

    beat["rendered_path"] = out_mp4
    logger.info(f"[assembler] Pass 1 rendered {beat_id} ({beat_hash[:12]}) -> {out_mp4}")
    return out_mp4


def cleanup_job_temp_files(job_dir: str) -> int:
    """
    Purges heavy intermediate files (stitched_temp.mp4, beat_XX.mp4 chunks, concat lists)
    to protect disk space on constrained drives while preserving manifest.json, voice_master.mp3,
    and lightweight plate images for QC1 previews. Returns total bytes freed.
    """
    freed_bytes = 0
    # 1. Remove stitched_temp.mp4
    stitched = os.path.join(job_dir, "stitched_temp.mp4")
    if os.path.exists(stitched):
        try:
            s = os.path.getsize(stitched)
            os.remove(stitched)
            freed_bytes += s
            logger.info(f"[assembler] Cleaned up intermediate stitched video: {stitched} ({s/(1024*1024):.1f} MB freed)")
        except Exception as e:
            logger.warning(f"[assembler] Could not remove {stitched}: {e}")

    # 2. Remove intermediate beat MP4 clips in job_dir/beats/
    beats_dir = os.path.join(job_dir, "beats")
    if os.path.exists(beats_dir):
        for f in os.listdir(beats_dir):
            if f.endswith(".mp4") or f.endswith(".tmp") or f == "concat_beats.txt":
                fp = os.path.join(beats_dir, f)
                try:
                    s = os.path.getsize(fp)
                    os.remove(fp)
                    freed_bytes += s
                except Exception as e:
                    logger.warning(f"[assembler] Could not remove temp beat file {fp}: {e}")
        logger.info(f"[assembler] Cleaned up intermediate beat clips in {beats_dir}")

    # 3. Remove temporary audio concat list and raw sentence MP3 chunks (voice_master.mp3 is already rendered)
    audio_dir = os.path.join(job_dir, "audio")
    if os.path.exists(audio_dir):
        for af in os.listdir(audio_dir):
            if af == "concat_list.txt" or af.startswith("sentence_") or af.endswith(".padded.mp3"):
                afp = os.path.join(audio_dir, af)
                try:
                    s = os.path.getsize(afp)
                    os.remove(afp)
                    freed_bytes += s
                except Exception:
                    pass

    # 4. Enforce hard 500 MB LRU cap across beat_cache, ai_clips, exports, and temp
    try:
        lru_res = enforce_lru_cache_cap(MAX_TEMP_CACHE_MB)
        if lru_res.get("evicted_count", 0) > 0:
            logger.info(
                f"[assembler] 500 MB LRU cache cap evicted {lru_res['evicted_count']} oldest files "
                f"({lru_res['evicted_mb']} MB freed; {lru_res['remaining_mb']} MB remaining)."
            )
    except Exception as e:
        logger.debug(f"[assembler] LRU cache enforcement note: {e}")

    return freed_bytes


def build_xfade_filter_chain(all_beats: List[Dict[str, Any]], max_transitions: int = 4) -> str:
    """
    Constructs an Intel UHD 620 / 16 GB RAM-safe `xfade` video transition filter chain:
    - Caps simultaneous `xfade` nodes to major Act breaks (`act_break`, `is_climax_entry`, or explicit
      `fadeblack` / `wipeleft`, max `max_transitions=4` per video) so FFmpeg never holds 16 1080x1920
      decoders open at once.
    - Appends a unified subtle film contrast + vignette pass so all clips share cohesive lighting.
    """
    n = len(all_beats)
    if n <= 1:
        return "[0:v]eq=contrast=1.04:saturation=1.03,vignette=PI/6[vxf]"

    # Select up to `max_transitions` major Act break indices (or evenly spaced act transitions if none flagged)
    break_indices: List[int] = [
        i for i in range(1, n)
        if all_beats[i].get("act_break")
        or all_beats[i].get("is_climax_entry")
        or str(all_beats[i].get("transition") or "").lower() in ("fadeblack", "wipeleft", "slideleft")
    ]
    if not break_indices:
        step = max(1, n // min(max_transitions, n))
        break_indices = [i for i in range(1, n) if i % step == 0]
    selected_indices = break_indices[:max_transitions]

    parts: List[str] = []
    cum_offset = 0.0
    prev_label = "0:v"

    for idx_pos, i in enumerate(selected_indices):
        # Sum durations up to this act break
        prev_idx = selected_indices[idx_pos - 1] if idx_pos > 0 else 0
        seg_dur = sum(max(0.65, float(all_beats[k].get("duration", 1.5))) for k in range(prev_idx, i))
        beat = all_beats[i]
        tr_type = str(beat.get("transition") or "").lower()
        if not tr_type:
            if beat.get("act_break"):
                tr_type = "fadeblack"
            elif beat.get("sfx") == "whoosh.wav":
                tr_type = "slideleft"
            else:
                tr_type = "fade"
        if tr_type not in ("fadeblack", "slideleft", "wipeleft", "wiperight", "fade", "smoothleft"):
            tr_type = "fade"

        tr_dur = 0.16 if tr_type == "fadeblack" else (0.14 if tr_type == "slideleft" else 0.12)
        tr_dur = min(tr_dur, seg_dur * 0.35)
        cum_offset = round(cum_offset + seg_dur - tr_dur, 3)
        out_label = f"vx{i}" if idx_pos < len(selected_indices) - 1 else "vxf_raw"
        parts.append(
            f"[{prev_label}][{i}:v]xfade=transition={tr_type}:duration={tr_dur:.2f}:offset={max(0.1, cum_offset):.3f}[{out_label}]"
        )
        prev_label = out_label

    parts.append(f"[{prev_label}]eq=contrast=1.04:saturation=1.03,vignette=PI/6[vxf]")
    return ";".join(parts)


def build_pass2_audio_filter_complex(
    all_beats: List[Dict[str, Any]],
    has_voice: bool,
    has_bgm: bool,
    base_input_count: int = 3,
) -> tuple[str, List[str]]:
    """
    Builds the Pass 2 Trailer Sound Design & Sidechain Ducking FFmpeg `filter_complex`:
    1. Places every beat's scheduled SFX (`thud.wav`, `whoosh.wav`, `click.wav`, `riser.wav`)
       onto the master timeline using exact millisecond `adelay` offsets (with `riser.wav`
       pre-offset by 1.1s so it peaks right on the cut).
    2. Inserts a 0.35s dramatic BGM silence drop right before the Act 3 climax reveal.
    3. Replaces flat BGM volume mixing with FFmpeg `sidechaincompress` driven by the mastered
       voice track so background score swells during vocal pauses and ducks cleanly during speech,
       mastered to -14 LUFS.
    """
    sfx_inputs: List[str] = []
    sfx_nodes: List[str] = []
    filter_parts: List[str] = []

    cur_t = 0.0
    climax_t: Optional[float] = None
    for idx, b in enumerate(all_beats):
        dur = max(0.65, float(b.get("duration", 1.5)))
        if b.get("is_climax_entry") and climax_t is None and cur_t > 2.0:
            climax_t = cur_t

        sfx_name = str(b.get("sfx") or "").strip()
        if sfx_name and sfx_name.lower() != "none":
            cand = os.path.join(SFX_DIR, os.path.basename(sfx_name))
            if os.path.exists(cand) and len(sfx_inputs) < 18:
                in_idx = base_input_count + len(sfx_inputs)
                sfx_inputs.append(cand)
                # Offset riser.wav so its swell peaks right on the beat transition
                if "riser" in sfx_name.lower():
                    delay_ms = max(0, int(round((cur_t - 1.1) * 1000)))
                    vol = 0.50
                elif "thud" in sfx_name.lower():
                    delay_ms = max(0, int(round(cur_t * 1000)))
                    vol = 0.62
                else:
                    delay_ms = max(0, int(round(cur_t * 1000)))
                    vol = 0.45
                node_name = f"sfx_d{len(sfx_nodes)}"
                filter_parts.append(f"[{in_idx}:a]adelay={delay_ms}|{delay_ms},volume={vol}[{node_name}]")
                sfx_nodes.append(f"[{node_name}]")
        cur_t += dur

    if climax_t is None and cur_t > 6.0:
        climax_t = round(cur_t * 0.72, 2)

    # Combine stitched base SFX track [0:a] with scheduled timeline SFX nodes
    if sfx_nodes:
        all_sfx_refs = "[0:a]" + "".join(sfx_nodes)
        filter_parts.append(
            f"{all_sfx_refs}amix=inputs={1 + len(sfx_nodes)}:duration=first:dropout_transition=0:normalize=0,volume=0.65[sfx_bus]"
        )
    else:
        filter_parts.append("[0:a]volume=0.55[sfx_bus]")

    if has_voice and has_bgm:
        # Split mastered voice track [1:a] so it both plays and drives the BGM sidechain compressor
        filter_parts.append("[1:a]volume=1.10,asplit=2[voice_main][voice_sc]")
        bgm_chain = "afade=t=in:st=0.6:d=1.4,volume=0.22"
        if climax_t is not None and climax_t > 1.0:
            drop_start = max(0.5, round(climax_t - 0.35, 2))
            drop_end = round(climax_t, 2)
            bgm_chain += f",volume=enable='between(t,{drop_start},{drop_end})':volume=0"
        filter_parts.append(f"[2:a]{bgm_chain}[bgm_pre]")
        filter_parts.append(
            "[bgm_pre][voice_sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[bgm_ducked]"
        )
        filter_parts.append(
            "[voice_main][sfx_bus][bgm_ducked]amix=inputs=3:duration=first:dropout_transition=2:normalize=0,"
            "loudnorm=I=-14:TP=-1.5:LRA=9[aout]"
        )
    elif has_voice:
        filter_parts.append("[1:a]volume=1.10[voice_main]")
        filter_parts.append(
            "[voice_main][sfx_bus]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[aout]"
        )
    else:
        filter_parts.append("[sfx_bus]volume=1.0[aout]")

    return ";".join(filter_parts), sfx_inputs


async def assemble_final_pass2(
    manifest: Dict[str, Any],
    job_dir: str,
    output_mp4: str
) -> bool:
    """
    Pass 2:
    - Explicitly unloads local Spark-X2.5-4B (~3.2 GB) before starting Pass 2 FFmpeg
    - Signals active_render.lock so the background harvester daemon pauses during encoding
    - Stitches all beats via concat demuxer (preserves synchronized transition SFX)
    - Layers voice_master.mp3 (spoken voiceover) + sidechain-ducked background music
    - Burns .ASS captions using bundled studio fonts with 4-thread CPU throttling
    """
    try:
        from backend.engine.brain import unload_local_brain
        unload_local_brain()
    except Exception:
        pass

    set_active_render_lock(manifest.get("job_id", os.path.basename(job_dir)), stage="FFMPEG_PASS2")
    beats_dir = os.path.join(job_dir, "beats")
    os.makedirs(beats_dir, exist_ok=True)
    concat_txt = os.path.join(beats_dir, "concat_beats.txt")

    all_beats = []
    if "beats" in manifest and manifest["beats"]:
        all_beats = manifest["beats"]
    else:
        for s in manifest.get("sentences", []):
            all_beats.extend(s.get("beats", []))

    # Pre-render Reflexion self-critic pass (heals text clipping, sluggish durations, pacing duplicate templates)
    topic = manifest.get("topic", "Documentary")
    all_beats, logged_heals = audit_and_heal_beats(all_beats, topic)
    if logged_heals:
        logger.info(f"[assembler] Reflexion pre-render pass auto-healed {len(logged_heals)} beat defect(s).")

    # Auto-render any missing beat clips from their preserved plates (resilient to post-render cleanup)
    for b in all_beats:
        r_path = b.get("rendered_path") or os.path.join(beats_dir, f"{b['id']}.mp4")
        if not os.path.exists(r_path):
            logger.info(f"[assembler] Auto-rendering missing beat {b.get('id')} from plate...")
            try:
                await render_beat_pass1(b, job_dir)
            except Exception as e:
                logger.warning(f"[assembler] Failed auto-rendering beat {b.get('id')}: {e}")

    # Write concat list
    with open(concat_txt, "w", encoding="utf-8") as f:
        for b in all_beats:
            r_path = b.get("rendered_path") or os.path.join(beats_dir, f"{b['id']}.mp4")
            if r_path and os.path.exists(r_path):
                norm = os.path.abspath(r_path).replace("\\", "/")
                f.write(f"file '{norm}'\n")

    stitched_video = os.path.join(job_dir, "stitched_temp.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        stitched_video
    ]
    def _run_concat():
        return subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, creationflags=_NO_WIN)

    try:
        async with _FFMPEG_SEMAPHORE:
            await asyncio.to_thread(_run_concat)
    except Exception as e:
        logger.error(f"[assembler] Concat failed: {e}")

    # Audio mixing: SFX stream + Spoken Voice + Ducked BGM + Subtitles
    voice_path = manifest.get("voice_master_path")
    ass_path = manifest.get("captions_ass_path")
    
    # Auto-detect BGM across assets/bgm and assets/music (.wav, .mp3, .ogg)
    bgm_candidates = [
        manifest.get("bgm_path"),
        os.path.abspath("assets/bgm/dark_doc_loop.wav"),
        os.path.abspath("assets/music/dark_doc_loop.wav"),
        os.path.abspath("assets/music/dark_doc_loop.mp3"),
        os.path.abspath("assets/bgm/dark_doc_loop.mp3"),
    ]
    bgm_path = None
    for cand in bgm_candidates:
        if cand and os.path.exists(cand):
            bgm_path = cand
            break
    if not bgm_path:
        for folder in ["assets/bgm", "assets/music"]:
            if os.path.exists(folder):
                audio_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
                if audio_files:
                    bgm_path = os.path.abspath(audio_files[0])
                    break
    target_duration = float(manifest.get("actual_duration") or manifest.get("total_duration") or 45.0)

    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)

    cmd_master = ["ffmpeg", "-y", "-i", stitched_video]
    has_voice = bool(voice_path and os.path.exists(voice_path))
    has_bgm = bool(has_voice and bgm_path and os.path.exists(bgm_path))

    if has_voice:
        cmd_master.extend(["-i", voice_path])
        if has_bgm:
            cmd_master.extend(["-stream_loop", "-1", "-t", str(target_duration + 3.0), "-i", bgm_path])

    base_inputs = 1 + (1 if has_voice else 0) + (1 if has_bgm else 0)
    audio_fc, sfx_input_paths = build_pass2_audio_filter_complex(
        all_beats=all_beats,
        has_voice=has_voice,
        has_bgm=has_bgm,
        base_input_count=base_inputs,
    )
    for sfx_p in sfx_input_paths:
        cmd_master.extend(["-i", sfx_p])

    filter_complex = [audio_fc]

    # Unified lighting polish + active-word .ASS subtitle burn with bundled studio fontsdir
    if ass_path and os.path.exists(ass_path):
        escaped_ass = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
        escaped_fonts = os.path.abspath(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
        filter_complex.append(
            f"[0:v]eq=contrast=1.04:saturation=1.03,vignette=PI/6,"
            f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'[vout]"
        )
        map_v = "[vout]"
    else:
        filter_complex.append("[0:v]eq=contrast=1.04:saturation=1.03,vignette=PI/6[vout]")
        map_v = "[vout]"

    enc_args = get_optimal_h264_encoder_args()
    cmd_master.extend([
        "-filter_complex", ";".join(filter_complex),
        "-map", map_v,
        "-map", "[aout]",
        *enc_args,
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_mp4
    ])

    def _run_master():
        return subprocess.run(cmd_master, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, creationflags=_NO_WIN)

    try:
        async with _FFMPEG_SEMAPHORE:
            res = await asyncio.to_thread(_run_master)
    except Exception as e:
        logger.error(f"[assembler] Pass 2 master execution error: {e}")
        res = None

    success = False
    if res and res.returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 0:
        logger.info(f"[assembler] Pass 2 complete! Final documentary MP4: {output_mp4} ({os.path.getsize(output_mp4)/(1024*1024):.1f} MB)")
        success = True
    else:
        err = res.stderr.decode(errors='ignore') if res else 'Execution error or timeout'
        logger.error(f"[assembler] Pass 2 error: {err}")
        # Robust fallback merge
        if voice_path and os.path.exists(voice_path):
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", stitched_video,
                "-i", voice_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_mp4
            ]
            res_fb = await asyncio.to_thread(subprocess.run, cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res_fb.returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 0:
                logger.info(f"[assembler] Pass 2 fallback merge complete: {output_mp4}")
                success = True

    clear_active_render_lock()
    if success:
        # Automatic disk cleanup: purge intermediate stitched video, beat clips, raw sentence MP3s, and enforce 500 MB LRU cap
        cleanup_job_temp_files(job_dir)
        return True
    return False
