"""
CONTENT-FACTORY Engine: Zero-Cost Visuals & OpenRouter Hybrid Media Adapter (free_visuals.py)
---------------------------------------------------------------------------------------------
Bridges `openrouter_discovery.py` and `visual_cortex.py`:
- Video stage (`resolve_video_clip`): checks `get_free_models_for("video")`. When empty (0 free video models),
  immediately skips OpenRouter (0 wasted API calls, zero 402 errors) and uses local Pexels/yt-dlp B-roll
  + 2-pass FFmpeg cosine zoompan / Depth Cortex + motion HUD cards.
- Image stage (`resolve_image_plate`): keeps unlimited `Pollinations Flux` as primary for bulk beats to
  preserve the 50/day OpenRouter free cap, while offering `fetch_openrouter_free_image` (e.g.
  `recraft/recraft-v4.1-flash-v2:free`) for hero thumbnails or when Pollinations fails.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from backend.engine import openrouter_discovery
from backend.engine.visual_cortex import (
    fetch_wikimedia_commons_image,
    fetch_pollinations_flux,
    fetch_pexels_broll,
    build_cinematic_visual_prompt,
)

logger = logging.getLogger("engine.free_visuals")


def check_openrouter_video_stage() -> Dict[str, Any]:
    """
    Checks if OpenRouter currently offers any strictly-free ($0.00 :free) video generation models.
    When none exist (or on circuit-breaker cooldown), immediately returns `auto_skip_to_local`
    with 0 API requests made.
    """
    free_video_models = openrouter_discovery.get_free_models_for("video")
    if not free_video_models:
        return {
            "stage": "video",
            "status": "auto_skip_to_local",
            "free_models_available": [],
            "openrouter_calls_made": 0,
            "active_engine": "local_ffmpeg_zoompan_and_broll",
        }
    return {
        "stage": "video",
        "status": "openrouter_free_available",
        "free_models_available": free_video_models,
        "openrouter_calls_made": 0,
        "active_engine": free_video_models[0],
    }


def fetch_openrouter_free_image(
    prompt: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    timeout: float = 22.0,
) -> bool:
    """
    Attempts to generate a $0.00 image using an active strictly-free OpenRouter image model
    (such as `recraft/recraft-v4.1-flash-v2:free` via `/api/v1/images` or `/api/v1/chat/completions`).
    Immediately skips and returns False (0 calls) if no strictly-free image model is live or on cooldown.
    """
    if openrouter_discovery.is_openrouter_on_cooldown():
        return False

    api_key = openrouter_discovery.resolve_openrouter_api_key()
    if not api_key:
        return False

    free_image_models = openrouter_discovery.get_free_models_for("image")
    if not free_image_models:
        return False

    model_id = free_image_models[0]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    payload = {
        "model": model_id,
        "prompt": prompt.strip()[:400],
        "n": 1,
        "size": "1024x1024",
    }

    req = urllib.request.Request(
        openrouter_discovery.OPENROUTER_IMAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": openrouter_discovery.get_app_referer_url(),
            "X-Title": "CONTENT-FACTORY Studio",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            items = raw.get("data") or []
            if items and isinstance(items[0], dict):
                b64_data = items[0].get("b64_json")
                img_url = items[0].get("url")
                if b64_data:
                    img_bytes = base64.b64decode(b64_data)
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    logger.info(f"[free_visuals] Generated $0 OpenRouter image ({model_id}) -> {output_path}")
                    return True
                elif img_url:
                    with urllib.request.urlopen(img_url, timeout=timeout) as img_resp:
                        img_bytes = img_resp.read()
                        if len(img_bytes) > 4000:
                            with open(output_path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"[free_visuals] Downloaded $0 OpenRouter image ({model_id}) -> {output_path}")
                            return True
    except urllib.error.HTTPError as he:
        if he.code in (402, 429):
            openrouter_discovery.record_openrouter_status(he.code, f"Image endpoint HTTP {he.code}")
        logger.debug(f"[free_visuals] OpenRouter free image skipped/fallback (HTTP {he.code})")
    except Exception as e:
        logger.debug(f"[free_visuals] OpenRouter free image fallback to Pollinations: {e}")

    return False


def resolve_image_plate(
    prompt: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    prefer_openrouter: bool = False,
    prefer_archival: bool = True,
) -> bool:
    """
    Hybrid image plate resolver:
    1. When `prefer_archival=True`, queries real Wikimedia Commons archival photography first so
       historical/documentary subjects use authentic archival stills before falling back to AI generation.
    2. By default (`prefer_openrouter=False`), uses unlimited `Pollinations Flux` next to save the
       50/day OpenRouter free quota for Brain/Script/Vision tasks, falling back to OpenRouter `:free`
       image models if Pollinations fails.
    3. When `prefer_openrouter=True` (e.g. hero thumbnail generation), tries OpenRouter `:free` image
       generation first and falls back to `Pollinations Flux`.
    """
    if prefer_archival and not prefer_openrouter:
        if fetch_wikimedia_commons_image(prompt, output_path, width=width, height=height):
            return True

    if prefer_openrouter:
        if fetch_openrouter_free_image(prompt, output_path, width=width, height=height):
            return True
        return fetch_pollinations_flux(prompt, output_path, width=width, height=height)

    if fetch_pollinations_flux(prompt, output_path, width=width, height=height):
        return True
    return fetch_openrouter_free_image(prompt, output_path, width=width, height=height)
