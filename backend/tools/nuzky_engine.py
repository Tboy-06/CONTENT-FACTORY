"""
Nuzky & OpenCut Video Integration Engine
----------------------------------------
Provides programmatic project generation, headless rendering via Nuzky CLI,
style-learning hooks, and OpenCut web-timeline interoperability.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import get_settings
from backend.tools.ffmpeg_engine import assemble_video

logger = logging.getLogger(__name__)
settings = get_settings()


def build_nuzky_project(
    job_id: int,
    name: str,
    shot_list: List[Dict[str, Any]],
    audio_path: str,
    captions: Optional[List[Dict[str, Any]]] = None,
    aspect_ratio: str = "9:16",
) -> Dict[str, Any]:
    """
    Constructs a valid Nuzky project JSON matching Nuzky Engine's model schema.
    Times are measured in integer microseconds (*_us).
    """
    if aspect_ratio == "16:9":
        width, height = 1920, 1080
    elif aspect_ratio == "1:1":
        width, height = 1080, 1080
    else:  # 9:16 default
        width, height = 1080, 1920

    assets: List[Dict[str, Any]] = []
    main_track_items: List[Dict[str, Any]] = []
    current_timeline_us = 0

    # 1. Main visual track items
    for i, shot in enumerate(shot_list):
        duration_sec = float(shot.get("duration", 3.0))
        duration_us = int(duration_sec * 1_000_000)
        asset_id = f"visual_{job_id}_{i}"
        file_path = shot.get("image_path") or shot.get("video_path") or shot.get("path", "")

        assets.append({
            "id": asset_id,
            "path": os.path.abspath(file_path) if file_path else "",
            "kind": "video" if str(file_path).endswith((".mp4", ".mov", ".webm")) else "image",
        })

        main_track_items.append({
            "id": f"clip_{i}",
            "assetId": asset_id,
            "timelineStartUs": current_timeline_us,
            "timelineDurationUs": duration_us,
            "sourceStartUs": 0,
            "sourceDurationUs": duration_us,
        })
        current_timeline_us += duration_us

    # 2. Audio track
    audio_track_items = []
    if audio_path and os.path.exists(audio_path):
        audio_asset_id = f"audio_{job_id}"
        assets.append({
            "id": audio_asset_id,
            "path": os.path.abspath(audio_path),
            "kind": "audio",
        })
        audio_track_items.append({
            "id": "main_voiceover",
            "assetId": audio_asset_id,
            "timelineStartUs": 0,
            "timelineDurationUs": current_timeline_us,
            "sourceStartUs": 0,
            "sourceDurationUs": current_timeline_us,
        })

    # 3. Captions / Text Track
    text_track_items = []
    if captions:
        for idx, cap in enumerate(captions):
            start_s = float(cap.get("start", idx * 2.5))
            end_s = float(cap.get("end", start_s + 2.5))
            text = cap.get("text", "")
            text_track_items.append({
                "id": f"caption_{idx}",
                "text": text,
                "timelineStartUs": int(start_s * 1_000_000),
                "timelineDurationUs": int((end_s - start_s) * 1_000_000),
                "style": {
                    "fontSize": 48,
                    "color": "#FFFFFF",
                    "outlineColor": "#000000",
                    "outlineWidth": 4,
                    "position": {"x": 0.5, "y": 0.8},
                },
            })

    project_data = {
        "version": 1,
        "name": name or f"ContentFactory_Job_{job_id}",
        "canvas": {
            "width": width,
            "height": height,
            "fps": 30,
        },
        "assets": assets,
        "tracks": [
            {
                "id": "track_video",
                "kind": "video",
                "isMain": True,
                "items": main_track_items,
            },
            {
                "id": "track_audio",
                "kind": "audio",
                "isMain": False,
                "items": audio_track_items,
            },
            {
                "id": "track_captions",
                "kind": "text",
                "isMain": False,
                "items": text_track_items,
            },
        ],
        "wordCorrections": [],
        "thumbnails": [],
        "reelCandidates": [],
    }

    return project_data


def save_nuzky_project(project_data: Dict[str, Any], output_path: str) -> str:
    """Saves the project data to a .nuzky JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2)
    logger.info(f"Saved Nuzky project to {output_path}")
    return output_path


async def render_with_nuzky_or_ffmpeg(
    project_path: str,
    output_mp4_path: str,
    preset: str = "reels",
    audio_fallback_path: Optional[str] = None,
    image_fallback_path: Optional[str] = None,
) -> bool:
    """
    Renders project via nuzky-cli if installed, otherwise uses robust FFmpeg fallback.
    """
    nuzky_bin = shutil.which(settings.nuzky_cli_path) or shutil.which("nuzky")

    if nuzky_bin:
        cmd = [nuzky_bin, "render", project_path, output_mp4_path, "--preset", preset]
        logger.info(f"Rendering via Nuzky CLI: {' '.join(cmd)}")
        try:
            res = await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(output_mp4_path):
                logger.info(f"Nuzky CLI render succeeded: {output_mp4_path}")
                return True
            else:
                logger.warning(f"Nuzky CLI render failed (code {res.returncode}): {res.stderr.decode(errors='ignore')}")
        except Exception as e:
            logger.warning(f"Error executing Nuzky CLI: {e}. Falling back to FFmpeg.")

    # Fallback to FFmpeg assembly
    if audio_fallback_path and image_fallback_path:
        logger.info("Using FFmpeg fallback assembly...")
        return await assemble_video(
            audio_path=audio_fallback_path,
            background_path=image_fallback_path,
            output_path=output_mp4_path,
            add_vfx=True,
        )

    logger.error("No valid rendering path succeeded.")
    return False


def build_opencut_timeline(
    job_id: int,
    shot_list: List[Dict[str, Any]],
    audio_path: str,
    captions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generates an OpenCut web-timeline compatible JSON structure.
    Used for embedding into OpenCut web editor or OTIO exchange.
    """
    tracks = []
    
    # Video track
    video_clips = []
    cur_time = 0.0
    for i, shot in enumerate(shot_list):
        dur = float(shot.get("duration", 3.0))
        video_clips.append({
            "id": f"clip_{i}",
            "name": shot.get("title", f"Shot {i+1}"),
            "src": shot.get("image_path") or shot.get("video_path", ""),
            "start": cur_time,
            "duration": dur,
        })
        cur_time += dur
        
    tracks.append({
        "type": "video",
        "name": "Main Visuals",
        "clips": video_clips,
    })

    # Audio track
    if audio_path:
        tracks.append({
            "type": "audio",
            "name": "Voiceover",
            "clips": [{
                "id": "audio_track",
                "name": "Narrator Audio",
                "src": audio_path,
                "start": 0,
                "duration": cur_time,
            }],
        })

    # Captions track
    if captions:
        caption_clips = []
        for idx, cap in enumerate(captions):
            start = float(cap.get("start", idx * 2.5))
            end = float(cap.get("end", start + 2.5))
            caption_clips.append({
                "id": f"cap_{idx}",
                "text": cap.get("text", ""),
                "start": start,
                "duration": end - start,
            })
        tracks.append({
            "type": "text",
            "name": "Captions",
            "clips": caption_clips,
        })

    return {
        "editor": "OpenCut",
        "version": "1.0",
        "jobId": job_id,
        "totalDuration": cur_time,
        "tracks": tracks,
    }
