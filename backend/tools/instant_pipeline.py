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
from backend.engine.planner import generate_documentary_plan
from backend.engine.audio_subs import synthesize_documentary_audio_and_subs
from backend.engine.assembler import render_beat_pass1, assemble_final_pass2, cleanup_job_temp_files

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

STYLE_PRESETS = {
    "Dark Documentary": {
        "name": "Dark Documentary",
        "bg": (11, 15, 25),
        "card_bg": (15, 23, 42),
        "card_border": (51, 65, 85),
        "badge_bg": (30, 58, 138),
        "badge_text": (186, 230, 253),
        "text": (248, 250, 252),
        "accent": (217, 119, 6),
        "prompt_vibe": "cinematic dark documentary aesthetic, moody natural lighting, 85mm anamorphic lens, 35mm film grain, desaturated realism"
    },
    "Vintage 35mm": {
        "name": "Vintage 35mm",
        "bg": (24, 20, 18),
        "card_bg": (38, 30, 26),
        "card_border": (87, 65, 52),
        "badge_bg": (120, 53, 15),
        "badge_text": (254, 215, 170),
        "text": (254, 243, 199),
        "accent": (245, 158, 11),
        "prompt_vibe": "vintage 35mm photography, Kodak Portra 400 tones, warm cinematic bloom, subtle organic halation, editorial texture"
    },
    "Cyberpunk Neo-Noir": {
        "name": "Cyberpunk Neo-Noir",
        "bg": (6, 9, 20),
        "card_bg": (13, 20, 38),
        "card_border": (14, 116, 144),
        "badge_bg": (3, 105, 161),
        "badge_text": (56, 189, 248),
        "text": (224, 242, 254),
        "accent": (6, 182, 212),
        "prompt_vibe": "cyberpunk neo-noir, rain-slicked dark atmosphere, volumetric neon blue and cyan rim lighting, high-contrast reflections"
    },
    "Minimalist Studio": {
        "name": "Minimalist Studio",
        "bg": (18, 18, 18),
        "card_bg": (26, 26, 26),
        "card_border": (64, 64, 64),
        "badge_bg": (45, 45, 45),
        "badge_text": (229, 231, 235),
        "text": (255, 255, 255),
        "accent": (163, 163, 163),
        "prompt_vibe": "clean minimalist studio photography, neutral matte backdrop, soft diffused key lighting, architectural precision"
    }
}

def render_scene_card(
    output_path: str,
    topic: str,
    badge: str,
    scene_index: int,
    total_scenes: int,
    text: str,
    style_preset: str = "Dark Documentary",
    image_prompt: Optional[str] = None
):
    """Renders a pixel-perfect, crisp 1080x1920 vertical scene plate."""
    preset = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["Dark Documentary"])
    img = Image.new("RGB", (1080, 1920), color=preset["bg"])
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
    draw.rectangle([40, 40, 1040, 1880], outline=preset["card_border"], width=3)
    draw.rectangle([50, 50, 1030, 1870], outline=preset["card_bg"], width=2)

    # Top Category / Topic Header
    draw.text((80, 100), topic.upper()[:40], fill=(148, 163, 184), font=font_small)

    # Scene Badge pill
    badge_text = f"SCENE {scene_index + 1} OF {total_scenes}: {badge.upper()}"
    draw.rounded_rectangle([80, 160, 80 + len(badge_text) * 18 + 40, 220], radius=8, fill=preset["badge_bg"])
    draw.text((100, 175), badge_text, fill=preset["badge_text"], font=font_badge)

    # Main text content box (centered vertically in middle screen)
    lines = wrap_text(text, max_chars=32)
    start_y = 650
    line_height = 80
    
    # Background accent card for readability
    card_h = len(lines) * line_height + 120
    draw.rounded_rectangle([70, start_y - 60, 1010, start_y - 60 + card_h], radius=16, fill=preset["card_bg"], outline=preset["card_border"], width=2)

    for i, line in enumerate(lines):
        draw.text((110, start_y + (i * line_height)), line, fill=preset["text"], font=font_large)

    # Bottom Branding with style preset
    draw.text((80, 1800), f"CONTENT-FACTORY  |  {preset['name'].upper()}", fill=(100, 116, 139), font=font_small)

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


async def render_video_from_scenes(job_id: int, scenes: List[Dict[str, Any]], audio_path: str, final_video_path: str) -> bool:
    """Assembles final 9:16 vertical MP4 from scene images and video clips with audio via FFmpeg."""
    cmd = ["ffmpeg", "-y", "-i", audio_path]
    for sc in scenes:
        path = sc.get("video_path") or sc.get("image_path")
        dur = float(sc.get("duration", 4.0))
        is_video = sc.get("is_video") or (path and path.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')))
        if is_video:
            cmd.extend(["-t", str(dur), "-i", path])
        else:
            cmd.extend(["-loop", "1", "-t", str(dur), "-i", path])

    filter_inputs = "".join(
        f"[{i+1}:v]setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v{i}];"
        for i in range(len(scenes))
    )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(scenes)))
    filter_complex = f"{filter_inputs}{concat_inputs}concat=n={len(scenes)}:v=1:a=0[outv]"

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

    res = await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        logger.error(f"[Instant Pipeline] FFmpeg render error: {res.stderr.decode(errors='ignore')}")
        return False
    logger.info(f"[Instant Pipeline] Video assembled successfully: {final_video_path}")
    return True


async def run_instant_pipeline(
    job_id: int,
    topic: str,
    voice: str = "en-US-AriaNeural",
    style_preset: str = "Dark Documentary",
    aspect_ratio: str = "9:16",
    duration: str = "45s"
) -> Dict[str, Any]:
    """
    Unified Documentary Engine Pipeline:
    1. Plan documentary beat sheet with rapid visual cuts (planner.py, supports 9:16 Shorts & 16:9 Long-Form)
    2. Edge-TTS narration + word-level timestamps + karaoke .ASS subtitle generation (audio_subs.py)
    3. Render rapid beats with Ken Burns zoom, archival treatments, and transition SFX (assembler.py)
    4. 2-Pass FFmpeg master assembly with ducked BGM, SFX audio mixing, and subtitle burn
    5. Save OpenCut timeline & register SQLite Vault assets -> Route to QC1
    """
    logger.info(f"[Instant Pipeline] Starting high-retention documentary generation for Job {job_id}: '{topic}' ({aspect_ratio}, {duration})")
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(repo_root, "output")
    job_dir = os.path.join(repo_root, "jobs", str(job_id))
    temp_dir = os.path.join(repo_root, "temp")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(job_dir, exist_ok=True)

    # Parse target duration float
    try:
        dur_clean = re.sub(r"[^0-9.]", "", duration)
        duration_target = float(dur_clean) if dur_clean else 45.0
        if "m" in duration.lower():
            duration_target *= 60.0
    except Exception:
        duration_target = 45.0

    try:
        # -------------------------------------------------------------
        # STEP 1: DOCUMENTARY SCRIPT & BEAT PLANNING
        # -------------------------------------------------------------
        await repository.create_stage(job_id, "SCRIPT")
        await repository.update_job_status(job_id, JobStatus.RUNNING, "SCRIPT")
        manifest = await generate_documentary_plan(
            topic=topic,
            job_id=job_id,
            aspect_ratio=aspect_ratio,
            duration_target=duration_target
        )

        # -------------------------------------------------------------
        # STEP 2: AUDIO SYNTHESIS & KARAOKE SUBTITLES
        # -------------------------------------------------------------
        await repository.create_stage(job_id, "AUDIO")
        await repository.update_job_status(job_id, JobStatus.RUNNING, "AUDIO")
        manifest = await synthesize_documentary_audio_and_subs(manifest, job_dir, voice=voice)

        voice_path = manifest.get("voice_master_path", f"{job_dir}/voice_master.mp3")
        total_audio_duration = float(manifest.get("actual_duration") or 45.0)

        await repository.add_asset(job_id, "AUDIO", voice_path, {
            "voice": voice,
            "duration": total_audio_duration,
            "captions_ass": manifest.get("captions_ass_path")
        })

        # -------------------------------------------------------------
        # STEP 3: RENDER 16 RAPID VISUAL BEATS (PASS 1)
        # -------------------------------------------------------------
        await repository.create_stage(job_id, "PLATES")
        await repository.update_job_status(job_id, JobStatus.RUNNING, "PLATES")
        scenes = []
        for s_idx, s in enumerate(manifest.get("sentences", [])):
            s_text = s.get("text", "")
            for b_idx, b in enumerate(s.get("beats", [])):
                rendered_path = await render_beat_pass1(b, job_dir)
                plate_png = os.path.join(job_dir, "beats", f"{b['id']}_plate.png")
                preview_img = plate_png if os.path.exists(plate_png) else rendered_path
                scenes.append({
                    "scene_index": len(scenes),
                    "badge": b.get("headline") or f"BEAT {len(scenes) + 1}",
                    "title": b.get("headline") or f"Beat {len(scenes) + 1}",
                    "text": s_text if b_idx == 0 else "",
                    "prompt": b.get("prompt") or b.get("highlight", ""),
                    "image_path": preview_img.replace("\\", "/"),
                    "duration": float(b.get("duration", 1.5))
                })

        # -------------------------------------------------------------
        # STEP 4: TIMELINES & 2-PASS MASTER ASSEMBLY (FFMPEG)
        # -------------------------------------------------------------
        await repository.create_stage(job_id, "FFMPEG")
        await repository.update_job_status(job_id, JobStatus.RUNNING, "FFMPEG")

        final_video_path = f"{output_dir}/instant_{job_id}.mp4"
        assembled = await assemble_final_pass2(manifest, job_dir, final_video_path)
        if not assembled or not os.path.exists(final_video_path):
            logger.warning(f"[Instant Pipeline] Fallback render engaging for Job {job_id}")
            await render_video_from_scenes(job_id, scenes, voice_path, final_video_path)

        # Verify master MP4 and ensure intermediate build files are purged to protect D: drive
        if os.path.exists(final_video_path) and os.path.getsize(final_video_path) > 0:
            freed = cleanup_job_temp_files(job_dir)
            logger.info(f"[Instant Pipeline] Master verified ({final_video_path}). Cleaned intermediate chunks ({freed/(1024*1024):.1f} MB freed).")

        # Build OpenCut timeline for web editor scrubbing
        opencut_timeline = build_opencut_timeline(
            job_id=job_id,
            shot_list=scenes,
            audio_path=voice_path,
        )
        opencut_path = f"{output_dir}/opencut_{job_id}.json"
        with open(opencut_path, "w", encoding="utf-8") as f:
            json.dump(opencut_timeline, f, indent=2)
        await repository.add_asset(job_id, "opencut_timeline", opencut_path, opencut_timeline)

        # Save master video asset with rich QC1 metadata
        hook_sentence = manifest["sentences"][0]["text"] if manifest.get("sentences") else f"The truth about {topic}"
        full_narration = " ".join(s.get("text", "") for s in manifest.get("sentences", []))

        await repository.add_asset(job_id, "VIDEO", final_video_path, {
            "aspect_ratio": "9:16",
            "title": topic,
            "duration": total_audio_duration,
            "video_url": f"/output/instant_{job_id}.mp4",
            "scenes": scenes,
            "style_preset": style_preset,
            "script": {
                "hook": hook_sentence,
                "body": full_narration,
                "cta": "Follow for more declassified files."
            },
            "voice": voice,
            "opencut_timeline": opencut_path,
            "manifest_path": os.path.join(job_dir, "manifest.json"),
        })

        # Advance stage to QC1 with pending approval
        await repository.create_stage(job_id, "QC1")
        await repository.update_job_status(job_id, JobStatus.RUNNING, "QC1")
        await repository.create_approval(job_id, "QC1")

        logger.info(f"[Instant Pipeline] Completed successfully for Job {job_id}. Ready at QC1.")
        return {
            "success": True,
            "job_id": job_id,
            "title": topic,
            "duration": total_audio_duration,
            "video_path": final_video_path,
            "stage": "QC1"
        }
    except Exception as e:
        logger.error(f"[Instant Pipeline] CRASHED on Job {job_id}: {e}", exc_info=True)
        await repository.update_job_status(job_id, JobStatus.FAILED, "ERROR")
        try:
            await repository.log_event(job_id, "ERROR", f"Instant pipeline error: {str(e)[:200]}")
        except Exception:
            pass
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "stage": "FAILED"
        }
