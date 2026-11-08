import os
import logging
import asyncio

logger = logging.getLogger(__name__)

async def generate_audio(text: str, output_path: str, voice: str = "en-US-AriaNeural") -> bool:
    """
    Uses edge-tts to generate an MP3 audio file from the provided text.
    Returns True if successful, False otherwise.
    """
    logger.info(f"Generating TTS audio to {output_path} using voice {voice}...")
    
    # Clean text of any quotes that might break command line
    safe_text = text.replace('"', "'")
    
    # We use subprocess to call the edge-tts CLI
    # Command: edge-tts --voice "en-US-AriaNeural" --text "Hello world" --write-media "output.mp3"
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--text", safe_text,
        "--write-media", output_path
    ]
    
    try:
        # Run process asynchronously to not block the FastAPI event loop
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"TTS generation successful: {output_path}")
            return True
        else:
            logger.error(f"TTS generation failed. Code: {process.returncode}")
            logger.error(f"Stderr: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to execute edge-tts: {e}")
        return False
