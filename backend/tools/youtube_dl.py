import asyncio
import subprocess
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def extract_video_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Extracts metadata from a YouTube/TikTok video URL using yt-dlp with timeout.
    """
    def _run_ytdlp():
        process = subprocess.Popen(
            ["yt-dlp", "-J", "--no-playlist", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        try:
            return process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError("yt-dlp metadata extraction timed out after 30s")

    try:
        stdout, stderr = await asyncio.to_thread(_run_ytdlp)
        data = json.loads(stdout)
        return {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "duration": data.get("duration", 0),
            "view_count": data.get("view_count", 0),
            "channel": data.get("uploader", ""),
        }
    except Exception as e:
        logger.error(f"Failed to extract video metadata: {e}")
        return None
