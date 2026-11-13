"""
CONTENT-FACTORY Engine: ZeroGPU Serverless Hook Generator (zero_gpu_hook.py)
----------------------------------------------------------------------------
Uses free serverless ZeroGPU public instances on Hugging Face (Wan2.1 / LTX-Video)
via `gradio_client` to generate the 3-second viral hero hook (Beat #1) for $0.

Zero local CUDA VRAM and zero local GPU compute.
Includes instant fallback to Pollinations Flux + DepthCortex 3D parallax if the
public Space is busy or queuing.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Optional

logger = logging.getLogger("engine.zero_gpu_hook")


def generate_zero_gpu_hero_clip(
    prompt: str,
    output_path: str,
    hf_token: Optional[str] = None,
    timeout: float = 28.0
) -> Optional[str]:
    """
    Attempts to generate a 3-second cinematic moving video hook using free public
    Hugging Face ZeroGPU Spaces via gradio_client.
    Returns output_path on success, or None on queue/timeout.
    """
    try:
        from gradio_client import Client
    except ImportError:
        logger.warning("[zero_gpu_hook] gradio_client not installed, skipping serverless hero clip.")
        return None

    token = hf_token or os.environ.get("HF_TOKEN") or None
    clean_prompt = prompt.strip()[:180]

    # Candidate public ZeroGPU Spaces for fast video generation
    spaces = [
        ("Wan-AI/Wan2.1-T2V-1.3B", "/generate"),
        ("Lightricks/LTX-Video", "/generate_video"),
    ]

    for space_id, api_name in spaces:
        try:
            logger.info(f"[zero_gpu_hook] Attempting ZeroGPU hook generation via {space_id}...")
            client = Client(space_id, token=token) if token else Client(space_id)
            # Predict with fast parameters
            result = client.predict(
                prompt=clean_prompt,
                api_name=api_name
            )
            # Result is usually a dict or tuple with video path
            res_path = None
            if isinstance(result, str) and os.path.exists(result):
                res_path = result
            elif isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], str) and os.path.exists(result[0]):
                res_path = result[0]
            elif isinstance(result, dict) and "video" in result:
                res_path = result["video"]

            if res_path and os.path.exists(res_path):
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                shutil.copyfile(res_path, output_path)
                logger.info(f"[zero_gpu_hook] ZeroGPU video generated successfully -> {output_path}")
                return output_path
        except Exception as e:
            logger.info(f"[zero_gpu_hook] Space {space_id} unavailable or queued ({e}). Trying next or fallback...")

    logger.info("[zero_gpu_hook] Falling back gracefully to Tier 1 Pollinations Flux + 3D Camera Motion.")
    return None
