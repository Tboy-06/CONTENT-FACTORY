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

logger = logging.getLogger("engine.assembler")


def _fetch_archival_image(prompt: str, target_path: str, timeout: float = 6.0) -> bool:
    """Fetches high-quality 9:16 vertical image from Pollinations Flux with fast timeout."""
    try:
        clean_prompt = prompt.strip()[:180]
        encoded = urllib.parse.quote(f"{clean_prompt}, documentary archival 35mm film still")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=720&height=1280&model=flux&nologo=true&seed=42"
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
    """Pass 1: Renders a single beat to beat_XX.mp4 with 9:16 framing, zoom, and transition SFX."""
    beat_id = beat["id"]
    duration = float(beat.get("duration", 1.5))
    beats_dir = os.path.join(job_dir, "beats")
    os.makedirs(beats_dir, exist_ok=True)

    plate_path = os.path.join(beats_dir, f"{beat_id}_plate.png")
    raw_img_path = os.path.join(beats_dir, f"{beat_id}_raw.jpg")
    out_mp4 = os.path.join(beats_dir, f"{beat_id}.mp4")

    # 1. Render or Fetch base plate
    if beat.get("type") == "motion_card":
        render_motion_card(
            template=beat.get("template", "red_slam_word"),
            headline=beat.get("headline", "CONFIDENTIAL"),
            highlight=beat.get("highlight", "EVIDENCE"),
            output_path=plate_path
        )
    else:
        # Treated archival image plate
        grade = beat.get("grade", "hard_bw")
        prompt = beat.get("prompt", "declassified intelligence document archival photo")

        # Try online image fetch
        fetched = await asyncio.to_thread(_fetch_archival_image, prompt, raw_img_path)
        if fetched and os.path.exists(raw_img_path):
            apply_color_grade(raw_img_path, plate_path, grade=grade)
        else:
            # Check local broll vault or generate typographic archival plate
            render_motion_card(
                template="quote_box",
                headline="ARCHIVAL EVIDENCE",
                highlight=prompt[:45],
                output_path=plate_path
            )
            apply_color_grade(plate_path, plate_path, grade=grade)

    # 2. Build Cosine Zoompan Filter
    total_frames = max(30, int(duration * fps))
    zoom_filter = f"zoompan=z='min(zoom+0.0012,1.20)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},trim=duration={duration}"

    # 3. Locate transition SFX
    sfx_name = beat.get("sfx", "whoosh.wav")
    sfx_path = os.path.abspath(os.path.join("assets", "sfx", sfx_name))

    if os.path.exists(sfx_path):
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
        # Render with silent audio track so all beats have compatible streams for concat
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
    if res.returncode == 0 and os.path.exists(output_mp4):
        logger.info(f"[assembler] Pass 2 complete! Final documentary MP4: {output_mp4}")
        return True
    else:
        logger.error(f"[assembler] Pass 2 error: {res.stderr.decode(errors='ignore')}")
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
            return res_fb.returncode == 0
        return False
