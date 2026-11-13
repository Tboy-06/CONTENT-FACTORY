"""
CONTENT-FACTORY Engine: Zero-Cost Visual Cortex Adapter (visual_cortex.py)
-------------------------------------------------------------------------
100% Free visual generation and retrieval engine ($0 API spend, 0 MB local GPU load):
- Tier 1: Free AI Photorealistic Plates via Pollinations.ai Flux (0 API keys, $0 cost).
- Tier 2: Free Moving B-Roll via Pexels API (20,000 free clips/mo) + fallback.
- Tier 3: Custom Hero Clip / Image Ingestion (supports custom Veo/Higgsfield/manual uploads).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from backend.engine.ev1_treat import apply_color_grade

logger = logging.getLogger("engine.visual_cortex")


def build_cinematic_visual_prompt(
    text: str,
    topic: str = "",
    style_preset: str = "Dark Documentary",
    lens: str = "35mm anamorphic",
    lighting: str = "volumetric chiaroscuro shadows",
    motion_cue: str = "slow dramatic push-in zoom"
) -> str:
    """
    Expands a simple narration beat into a Higgsfield/Veo style prompt
    with explicit camera, lens, lighting, texture, and movement cues.
    """
    clean_text = text.strip()[:140]
    topic_str = f" in context of {topic.strip()}" if topic else ""
    return (
        f"Cinematic {lens} film shot, {lighting}, {clean_text}{topic_str}, "
        f"35mm Kodak grain, photorealistic documentary archival still, {motion_cue}, 8k UHD"
    )


def fetch_pollinations_flux(
    prompt: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    seed: Optional[int] = None,
    timeout: float = 18.0
) -> bool:
    """
    Tier 1: Fetches 1080x1920 photorealistic plate from Pollinations Flux API.
    Zero API keys required. Completely free.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    clean_prompt = prompt.strip()[:240]
    encoded_prompt = urllib.parse.quote(clean_prompt)
    seed_param = f"&seed={seed}" if seed is not None else "&seed=42"
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true{seed_param}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) > 5000:
                with open(output_path, "wb") as f:
                    f.write(data)
                logger.info(f"[visual_cortex] Fetched Pollinations Flux plate -> {output_path} ({len(data)} bytes)")
                return True
    except Exception as e:
        logger.warning(f"[visual_cortex] Pollinations Flux fetch failed ({e}) for prompt: {prompt[:60]}")
    return False


def fetch_pexels_broll(
    query: str,
    output_path: str,
    aspect_ratio: str = "9:16",
    duration: float = 4.0,
    api_key: Optional[str] = None,
    timeout: float = 20.0
) -> bool:
    """
    Tier 2: Slices a free HD moving B-roll clip from Pexels API (20,000 free requests/month).
    Normalizes resolution to 1080x1920 or 1920x1080 and trims to target duration.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    key = api_key or os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return False

    orientation = "portrait" if aspect_ratio == "9:16" else "landscape"
    clean_query = urllib.parse.quote(query.strip()[:60] or "cinematic documentary")
    search_url = f"https://api.pexels.com/videos/search?query={clean_query}&per_page=5&orientation={orientation}"

    req = urllib.request.Request(
        search_url,
        headers={"Authorization": key, "User-Agent": "ContentFactory/2.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            videos = data.get("videos", [])
            if not videos:
                return False

            # Select best matching video file
            video_files = videos[0].get("video_files", [])
            target_file_url = None
            for vf in video_files:
                if aspect_ratio == "9:16" and (vf.get("width", 0) or 0) < (vf.get("height", 0) or 0):
                    target_file_url = vf.get("link")
                    break
                elif aspect_ratio == "16:9" and (vf.get("width", 0) or 0) >= (vf.get("height", 0) or 0):
                    target_file_url = vf.get("link")
                    break

            if not target_file_url and video_files:
                target_file_url = video_files[0].get("link")

            if not target_file_url:
                return False

            raw_temp = output_path + ".raw.mp4"
            with urllib.request.urlopen(target_file_url, timeout=timeout) as v_resp, open(raw_temp, "wb") as f:
                f.write(v_resp.read())

            target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
            # Normalize with FFmpeg: scale, crop to target aspect, trim duration
            vf_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
            cmd = [
                "ffmpeg", "-y",
                "-ss", "0",
                "-t", str(duration),
                "-i", raw_temp,
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-an",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if os.path.exists(raw_temp):
                try:
                    os.remove(raw_temp)
                except OSError:
                    pass

            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                logger.info(f"[visual_cortex] Fetched and normalized Pexels B-roll -> {output_path}")
                return True

    except Exception as e:
        logger.warning(f"[visual_cortex] Pexels B-roll fetch failed ({e})")
    return False


def normalize_custom_media(
    input_file: str,
    output_path: str,
    aspect_ratio: str = "9:16",
    duration: float = 4.0
) -> Dict[str, Any]:
    """
    Tier 3: Ingests user-uploaded custom media (Veo/Higgsfield clip, phone video, or custom image).
    Converts and normalizes to the pipeline standard.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ext = os.path.splitext(input_file)[1].lower()
    is_video = ext in (".mp4", ".mov", ".mkv", ".webm", ".avi")
    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

    if is_video:
        vf_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-t", str(duration),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
        return {
            "type": "video",
            "path": output_path,
            "success": res.returncode == 0 and os.path.exists(output_path)
        }
    else:
        # Treat as still image
        apply_color_grade(
            image_path=input_file,
            output_path=output_path,
            grade="none",
            target_width=target_w,
            target_height=target_h
        )
        return {
            "type": "image",
            "path": output_path,
            "success": os.path.exists(output_path)
        }
