"""
CONTENT-FACTORY Engine: 2-Pass FFmpeg Documentary Assembler
-----------------------------------------------------------
Pass 1: Renders individual beats into beat_XX.mp4 with cosine zoompan,
        documentary color treatments (B&W/Teal/Amber), and transition SFX.
Pass 2: Stitches beats + mixes SFX audio + voiceover + ducked BGM + burns .ASS captions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from backend.engine.ev1_treat import apply_color_grade, build_cosine_zoompan_filter
from backend.engine.motion_cards import render_motion_card
import backend.engine.visual_cortex as visual_cortex
import backend.engine.forensic_canvas as forensic_canvas
import backend.engine.depth_cortex as depth_cortex
import backend.engine.zero_gpu_hook as zero_gpu_hook

logger = logging.getLogger("engine.assembler")


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

    plate_path = os.path.join(beats_dir, f"{beat_id}_plate.png")
    raw_img_path = os.path.join(beats_dir, f"{beat_id}_raw.jpg")
    out_mp4 = os.path.join(beats_dir, f"{beat_id}.mp4")

    # 1. Zero-Cost Visual Cortex Media Ingestion (3 Tiers)
    custom_media = beat.get("custom_media")
    is_video_input = False
    video_source_path = None

    if custom_media and os.path.exists(custom_media):
        # Tier 3: Custom Hero Clip / Image Drop
        norm_output = os.path.join(beats_dir, f"{beat_id}_custom_norm.mp4" if custom_media.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')) else f"{beat_id}_plate.png")
        norm_res = visual_cortex.normalize_custom_media(custom_media, norm_output, aspect_ratio=aspect_ratio, duration=duration)
        if norm_res["type"] == "video" and norm_res["success"]:
            is_video_input = True
            video_source_path = norm_output
        else:
            plate_path = norm_output

    elif beat.get("type") in ("hero_hook", "ai_video") or (beat_id in ("b01", "beat_01") and duration <= 4.0):
        # Engine 1: Free Serverless Cloud GPU for 3-Second Hero Hook (ZeroGPU Spaces via gradio_client)
        hero_dest = os.path.join(beats_dir, f"{beat_id}_zerogpu.mp4")
        prompt = beat.get("visual_prompt") or beat.get("prompt", "cinematic film dramatic hook")
        hero_path = await asyncio.to_thread(
            zero_gpu_hook.generate_zero_gpu_hero_clip,
            prompt=prompt,
            output_path=hero_dest
        )
        if hero_path and os.path.exists(hero_dest):
            is_video_input = True
            video_source_path = hero_dest
        else:
            # Fallback to Pollinations Flux + DepthCortex 3D motion
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
            visual_cortex.fetch_pollinations_flux,
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
    cam_mov = (beat.get("camera_movement") or "push_in").lower()
    if "dolly" in cam_mov or "vertigo" in cam_mov:
        zoom_filter = f"zoompan=z='min(zoom+0.0020,1.24)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"
    elif "orbit" in cam_mov or "rotation" in cam_mov:
        zoom_filter = f"zoompan=z='1.15':d={total_frames}:x='(iw/2-(iw/zoom/2)) + sin(in/{total_frames}*3.14159)*50':y='(ih/2-(ih/zoom/2)) + cos(in/{total_frames}*3.14159)*25':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"
    elif "bokeh" in cam_mov or "focus" in cam_mov:
        zoom_filter = f"zoompan=z='min(zoom+0.0014,1.16)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},unsharp=5:5:0.8:5:5:0.0,trim=duration={duration}"
    else:
        zoom_filter = f"zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps},trim=duration={duration}"

    sfx_name = beat.get("sfx", "whoosh.wav")
    sfx_path = os.path.abspath(os.path.join("assets", "sfx", sfx_name))
    has_sfx = os.path.exists(sfx_path)

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
                "-c:v", "libx264",
                "-preset", "ultrafast",
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
                "-c:v", "libx264",
                "-preset", "ultrafast",
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
                "-c:v", "libx264",
                "-preset", "ultrafast",
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
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-shortest",
                out_mp4
            ]

    def _run_pass1():
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

    try:
        await asyncio.to_thread(_run_pass1)
    except Exception as e:
        logger.error(f"[assembler] Pass 1 timed out or failed on {beat_id}: {e}")

    beat["rendered_path"] = out_mp4
    logger.info(f"[assembler] Pass 1 rendered {beat_id} -> {out_mp4}")
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

    # 3. Remove temporary audio concat list
    audio_concat = os.path.join(job_dir, "audio", "concat_list.txt")
    if os.path.exists(audio_concat):
        try:
            os.remove(audio_concat)
        except Exception:
            pass

    return freed_bytes


async def assemble_final_pass2(
    manifest: Dict[str, Any],
    job_dir: str,
    output_mp4: str
) -> bool:
    """
    Pass 2:
    - Stitches all beats via concat demuxer (preserves synchronized transition SFX)
    - Layers voice_master.mp3 (spoken voiceover)
    - Layers ducked background music
    - Burns .ASS captions
    """
    beats_dir = os.path.join(job_dir, "beats")
    concat_txt = os.path.join(beats_dir, "concat_beats.txt")

    all_beats = []
    for s in manifest.get("sentences", []):
        all_beats.extend(s.get("beats", []))

    # Write concat list
    with open(concat_txt, "w", encoding="utf-8") as f:
        for b in all_beats:
            r_path = b.get("rendered_path")
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
        return subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

    try:
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
    filter_complex = []

    if voice_path and os.path.exists(voice_path):
        cmd_master.extend(["-i", voice_path])
        if os.path.exists(bgm_path):
            # Cap infinite stream loop with -t to guarantee FFmpeg never hangs on 0-byte voice
            cmd_master.extend(["-stream_loop", "-1", "-t", str(target_duration + 3.0), "-i", bgm_path])
            # Inputs: 0=stitched (sfx), 1=voice, 2=bgm
            filter_complex.append("[0:a]volume=0.85[sfx]")
            filter_complex.append("[1:a]volume=1.05[voice]")
            filter_complex.append("[2:a]volume=0.15[bgm]")
            filter_complex.append("[voice][sfx][bgm]amix=inputs=3:duration=first:dropout_transition=2[aout]")
        else:
            # Inputs: 0=stitched (sfx), 1=voice
            filter_complex.append("[0:a]volume=0.85[sfx]")
            filter_complex.append("[1:a]volume=1.05[voice]")
            filter_complex.append("[voice][sfx]amix=inputs=2:duration=first[aout]")
    else:
        # Fallback to SFX audio stream only
        filter_complex.append("[0:a]volume=1.0[aout]")

    # Subtitle burn filter (escaped for Windows)
    if ass_path and os.path.exists(ass_path):
        escaped_ass = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
        filter_complex.append(f"[0:v]subtitles='{escaped_ass}'[vout]")
        map_v = "[vout]"
    else:
        map_v = "0:v"

    cmd_master.extend([
        "-filter_complex", ";".join(filter_complex),
        "-map", map_v,
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_mp4
    ])

    def _run_master():
        return subprocess.run(cmd_master, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)

    try:
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

    if success:
        # Automatic disk cleanup: purge intermediate stitched video and beat clips
        cleanup_job_temp_files(job_dir)
        return True
    return False
