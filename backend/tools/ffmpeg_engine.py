import os
import logging
import asyncio

logger = logging.getLogger(__name__)

async def assemble_video(audio_path: str, background_path: str, output_path: str, add_vfx: bool = False) -> bool:
    """
    Uses FFmpeg to merge an audio file with a background video (or image).
    If background_path is an image, it loops it for the duration of the audio.
    """
    logger.info(f"Assembling video {output_path}...")
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file missing: {audio_path}")
        return False
        
    is_image = background_path.lower().endswith(('.png', '.jpg', '.jpeg'))
    
    cmd = ["ffmpeg", "-y"]
    
    if is_image:
        cmd.extend(["-loop", "1", "-i", background_path])
    else:
        cmd.extend(["-i", background_path])
        
    cmd.extend(["-i", audio_path])
    
    # Calculate shortest stream (which will be the audio length if looping an image)
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-shortest"])
    
    # Apply VFX if requested (e.g., a simple slow zoom effect for images)
    if add_vfx and is_image:
        cmd.extend(["-vf", "zoompan=z='min(zoom+0.0015,1.5)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"])
    elif is_image:
        # Scale to standard shorts resolution if just an image
        cmd.extend(["-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"])
        
    cmd.append(output_path)
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"Video assembly successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg failed with code {process.returncode}")
            logger.error(f"FFmpeg stderr: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"Exception executing FFmpeg: {e}")
        return False
