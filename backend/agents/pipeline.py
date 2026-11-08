import asyncio
import logging
import time
from pathlib import Path

from backend.tools.llm import generate_script
from backend.tools.tts import generate_audio
from backend.tools.ffmpeg_engine import assemble_video
from backend.state import ACTIVE_JOBS

logger = logging.getLogger(__name__)

# Ensure output directory exists
OUTPUT_DIR = Path("D:/CONTENT-FACTORY/backend/vault/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def run_content_pipeline(job_id: str, niche: str, pipeline_mode: str = "Generate from Scratch", reference_url: str = None) -> dict:
    """
    Orchestrates the entire AI pipeline:
    1. LLM generates script.
    2. Edge-TTS generates audio.
    3. FFmpeg generates final video (with a placeholder image/video for now).
    """
    try:
        logger.info(f"Starting pipeline {job_id} for niche: {niche}")
        
        # 1. GENERATE SCRIPT
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id]["stage"] = "Script Generation"
            ACTIVE_JOBS[job_id]["progress"] = "10%"
            
        logger.info("[Step 1/3] Generating script...")
        script_data = await generate_script(niche, pipeline_mode, reference_url)
        
        full_text = f"{script_data.get('hook', '')} {script_data.get('body', '')} {script_data.get('cta', '')}"
        logger.info(f"Generated script (Title: {script_data.get('title')})")
        
        # 2. GENERATE AUDIO
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id]["stage"] = "Audio Generation (TTS)"
            ACTIVE_JOBS[job_id]["progress"] = "40%"
            
        logger.info("[Step 2/3] Generating TTS audio...")
        audio_path = str(OUTPUT_DIR / f"{job_id}_narration.mp3")
        audio_success = await generate_audio(full_text, audio_path)
        
        if not audio_success:
            if job_id in ACTIVE_JOBS:
                ACTIVE_JOBS[job_id]["status"] = "error"
                ACTIVE_JOBS[job_id]["stage"] = "Failed at Audio"
                ACTIVE_JOBS[job_id]["completed_at"] = time.time() * 1000
            return {"status": "error", "message": "Failed to generate audio."}
            
        # 3. ASSEMBLE VIDEO
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id]["stage"] = "Video Assembly (FFmpeg)"
            ACTIVE_JOBS[job_id]["progress"] = "70%"
            
        logger.info("[Step 3/3] Assembling video with FFmpeg...")
        bg_path = str(OUTPUT_DIR / f"{job_id}_bg.jpg")
        try:
            from PIL import Image
            img = Image.new('RGB', (1080, 1920), color = 'black')
            img.save(bg_path)
        except ImportError:
            logger.warning("Pillow not installed, skipping background generation. FFmpeg might fail.")
            
        video_path = str(OUTPUT_DIR / f"{job_id}_final.mp4")
        video_success = await assemble_video(audio_path, bg_path, video_path, add_vfx=True)
        
        if video_success:
            if job_id in ACTIVE_JOBS:
                ACTIVE_JOBS[job_id]["stage"] = "Complete"
                ACTIVE_JOBS[job_id]["progress"] = "100%"
                ACTIVE_JOBS[job_id]["status"] = "success"
                ACTIVE_JOBS[job_id]["completed_at"] = time.time() * 1000
                
            logger.info(f"Pipeline {job_id} completed successfully!")
            return {
                "status": "success",
                "job_id": job_id,
                "script": script_data,
                "outputs": {
                    "audio": audio_path,
                    "video": video_path
                }
            }
        else:
            if job_id in ACTIVE_JOBS:
                ACTIVE_JOBS[job_id]["status"] = "error"
                ACTIVE_JOBS[job_id]["stage"] = "Failed at Video"
                ACTIVE_JOBS[job_id]["completed_at"] = time.time() * 1000
            return {"status": "error", "message": "Failed to assemble video."}
    except Exception as e:
        logger.error(f"Pipeline {job_id} crashed: {str(e)}")
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id]["status"] = "error"
            ACTIVE_JOBS[job_id]["stage"] = f"Crashed: {str(e)}"
            ACTIVE_JOBS[job_id]["completed_at"] = time.time() * 1000
        return {"status": "error", "message": f"Crashed: {str(e)}"}
