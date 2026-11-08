import os
import re
import json
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont

import edge_tts
from backend.vault import repository
from backend.vault.models import JobStatus, ApprovalDecision
from backend.tools.nuzky_engine import build_nuzky_project, save_nuzky_project, build_opencut_timeline
from backend.tools.llm import generate_script

logger = logging.getLogger(__name__)

def wrap_text(text: str, max_chars: int = 34) -> List[str]:
    """Wraps text into clean lines for vertical 9:16 layout."""
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 <= max_chars:
            current_line.append(w)
            current_len += len(w) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def render_scene_card(
    output_path: str,
    topic: str,
    badge: str,
    scene_index: int,
    total_scenes: int,
    text: str,
    bg_color=(11, 15, 25)
):
    """Renders a pixel-perfect, crisp 1080x1920 vertical scene plate."""
    img = Image.new("RGB", (1080, 1920), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arialbd.ttf", 64)
        font_medium = ImageFont.truetype("arial.ttf", 46)
        font_small = ImageFont.truetype("arial.ttf", 32)
        font_badge = ImageFont.truetype("arialbd.ttf", 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_badge = font_large

    # Border & frame
    draw.rectangle([40, 40, 1040, 1880], outline=(30, 41, 59), width=3)
    draw.rectangle([50, 50, 1030, 1870], outline=(15, 23, 42), width=2)

    # Top Category / Topic Header
    draw.text((80, 100), topic.upper()[:40], fill=(148, 163, 184), font=font_small)

    # Scene Badge pill
    badge_text = f"SCENE {scene_index + 1} OF {total_scenes}: {badge.upper()}"
    draw.rounded_rectangle([80, 160, 80 + len(badge_text) * 18 + 40, 220], radius=8, fill=(30, 58, 138))
    draw.text((100, 175), badge_text, fill=(186, 230, 253), font=font_badge)

    # Main text content box (centered vertically in middle screen)
    lines = wrap_text(text, max_chars=32)
    start_y = 650
    line_height = 80
    
    # Background accent card for readability
    card_h = len(lines) * line_height + 120
    draw.rounded_rectangle([70, start_y - 60, 1010, start_y - 60 + card_h], radius=16, fill=(15, 23, 42), outline=(51, 65, 85), width=2)

    for i, line in enumerate(lines):
        draw.text((110, start_y + (i * line_height)), line, fill=(248, 250, 252), font=font_large)

    # Bottom Branding
    draw.text((80, 1800), "CONTENT-FACTORY  |  VERIFIED CUT", fill=(71, 85, 105), font=font_small)

    img.save(output_path, quality=95)


def get_audio_duration(file_path: str) -> float:
    """Probes the exact duration of the audio file in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dur = float(result.stdout.strip())
        return max(dur, 2.0)
    except Exception as e:
        logger.warning(f"Could not probe audio duration: {e}. Defaulting to 15.0s")
        return 15.0


async def run_instant_pipeline(job_id: int, topic: str, voice: str = "en-US-AriaNeural") -> Dict[str, Any]:
    """
    Lean, dynamic 4-step execution engine:
    1. Real dynamic script generation (Ollama / Fallback)
    2. Speech synthesis via Edge-TTS (Free) + exact duration probing
    3. High-resolution 1080x1920 scene plates with dynamic typography
    4. FFmpeg multi-clip assembly with Ken Burns zoompan -> Jump directly to QC1
    """
    logger.info(f"[Instant Pipeline] Starting dynamic generation for Job {job_id} on: '{topic}'")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    # -------------------------------------------------------------
    # STEP 1: DYNAMIC SCRIPT GENERATION
    # -------------------------------------------------------------
    await repository.create_stage(job_id, "SCRIPT")
    await repository.update_job_status(job_id, JobStatus.RUNNING, "SCRIPT")

    raw_script = await generate_script(topic)
    title = raw_script.get("title") or topic
    hook = raw_script.get("hook") or f"Here is the truth about {topic}."
    body = raw_script.get("body") or f"Understanding {topic} changes everything. Most people never realize this critical insight."
    cta = raw_script.get("cta") or "Save this video and follow for more."

    # Split body into natural sentences
    body_sentences = [s.strip() for s in re.split(r'[.!?]+', body) if len(s.strip()) > 8]
    if len(body_sentences) >= 2:
        part1 = body_sentences[0] + "."
        part2 = " ".join(body_sentences[1:]) + "."
    else:
        part1 = body
        part2 = "Apply this principle daily to stay ahead."

    # Build structured scenes
    raw_scenes = [
        {"badge": "HOOK", "title": "The Hook", "text": hook},
        {"badge": "INSIGHT", "title": "Core Problem", "text": part1},
        {"badge": "BREAKTHROUGH", "title": "The Breakdown", "text": part2},
        {"badge": "ACTION", "title": "Call To Action", "text": cta},
    ]

    full_narration = " ".join(s["text"] for s in raw_scenes)
    audio_path = f"{output_dir}/audio_{job_id}.mp3"
    subtitles_path = f"{output_dir}/subtitles_{job_id}.srt"

    # -------------------------------------------------------------
    # STEP 2: AUDIO SYNTHESIS & EXACT DURATION PROBING
    # -------------------------------------------------------------
    logger.info(f"[Instant Pipeline] Generating speech with voice {voice}...")
    communicate = edge_tts.Communicate(full_narration, voice)
    submaker = edge_tts.SubMaker()

    with open(audio_path, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    with open(subtitles_path, "w", encoding="utf-8") as f:
        f.write(submaker.get_srt())

    # Probe real audio duration
    total_audio_duration = get_audio_duration(audio_path)
    logger.info(f"[Instant Pipeline] Audio synthesized: {total_audio_duration:.2f}s total duration.")

    # Calculate proportional scene durations based on word counts
    total_words = sum(len(s["text"].split()) for s in raw_scenes) or 1
    scenes = []
    current_time = 0.0

    for i, sc in enumerate(raw_scenes):
        w_count = len(sc["text"].split())
        calc_dur = round((w_count / total_words) * total_audio_duration, 2)
        calc_dur = max(calc_dur, 2.5)  # Minimum 2.5s per scene
        scenes.append({
            "id": i,
            "badge": sc["badge"],
            "title": sc["title"],
            "text": sc["text"],
            "start": round(current_time, 2),
            "duration": calc_dur,
        })
        current_time += calc_dur

    # Scale total durations to match exact audio length
    scale_factor = total_audio_duration / max(current_time, 1.0)
    for s in scenes:
        s["duration"] = round(s["duration"] * scale_factor, 2)

    await repository.add_asset(job_id, "AUDIO", audio_path, {
        "voice": voice,
        "narration": full_narration,
        "duration": total_audio_duration
    })

    # -------------------------------------------------------------
    # STEP 3: HIGH-RESOLUTION SCENE PLATES (Pillow)
    # -------------------------------------------------------------
    palette = [
        (11, 15, 25),    # Dark Navy
        (15, 23, 42),    # Slate
        (18, 20, 32),    # Deep Charcoal
        (10, 22, 36),    # Deep Ocean
    ]
    image_paths: List[str] = []

    for i, sc in enumerate(scenes):
        img_path = f"temp/instant_{job_id}_{i}.jpg"
        render_scene_card(
            output_path=img_path,
            topic=title,
            badge=sc["badge"],
            scene_index=i,
            total_scenes=len(scenes),
            text=sc["text"],
            bg_color=palette[i % len(palette)]
        )
        image_paths.append(img_path)
        sc["image_path"] = img_path

    # -------------------------------------------------------------
    # STEP 4: TIMELINES & ASSEMBLE 9:16 MP4
    # -------------------------------------------------------------
    nuzky_proj = build_nuzky_project(
        job_id=job_id,
        name=f"Instant_{job_id}_{title[:20]}",
        shot_list=scenes,
        audio_path=audio_path,
        aspect_ratio="9:16",
    )
    nuzky_project_path = f"{output_dir}/project_{job_id}.nuzky"
    save_nuzky_project(nuzky_proj, nuzky_project_path)
    await repository.add_asset(job_id, "nuzky_project", nuzky_project_path, nuzky_proj)

    opencut_timeline = build_opencut_timeline(
        job_id=job_id,
        shot_list=scenes,
        audio_path=audio_path,
    )
    opencut_path = f"{output_dir}/opencut_{job_id}.json"
    with open(opencut_path, "w", encoding="utf-8") as f:
        json.dump(opencut_timeline, f, indent=2)
    await repository.add_asset(job_id, "opencut_timeline", opencut_path, opencut_timeline)

    # Render vertical 9:16 MP4 via FFmpeg with proportional scene durations
    final_video_path = f"{output_dir}/video_{job_id}_9x16.mp4"
    logger.info(f"[Instant Pipeline] Rendering final MP4: {final_video_path}")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-i", audio_path])
    for i, sc in enumerate(scenes):
        cmd.extend(["-loop", "1", "-t", str(sc["duration"]), "-i", sc["image_path"]])

    filter_inputs = "".join(f"[{i+1}:v]" for i in range(len(scenes)))
    filter_complex = f"{filter_inputs}concat=n={len(scenes)}:v=1:a=0[v];[v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[outv]"

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        final_video_path
    ])

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"[Instant Pipeline] FFmpeg render error: {stderr.decode()}")
    else:
        logger.info(f"[Instant Pipeline] Video assembled successfully.")

    # Save video asset with full dynamic metadata
    await repository.add_asset(job_id, "video", final_video_path, {
        "aspect_ratio": "9:16",
        "title": title,
        "duration": total_audio_duration,
        "video_url": f"/output/video_{job_id}_9x16.mp4",
        "scenes": scenes,
        "script": {
            "hook": hook,
            "body": f"{part1} {part2}",
            "cta": cta
        },
        "voice": voice,
        "nuzky_project": nuzky_project_path,
        "opencut_timeline": opencut_path,
    })

    # Set job state to QC1 and create pending approval
    await repository.create_stage(job_id, "QC1")
    await repository.update_job_status(job_id, JobStatus.AWAITING_APPROVAL, "QC1")
    await repository.create_approval(job_id, "QC1")

    logger.info(f"[Instant Pipeline] Completed successfully for Job {job_id}. Ready at QC1.")
    return {
        "success": True,
        "job_id": job_id,
        "title": title,
        "duration": total_audio_duration,
        "video_path": final_video_path,
        "stage": "QC1"
    }
