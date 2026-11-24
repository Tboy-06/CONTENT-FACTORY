"""
CONTENT-FACTORY Engine: ZeroGPU Serverless Hook Generator (zero_gpu_hook.py)
----------------------------------------------------------------------------
Routes Beat #1 hero video generation through the unified `backend/engine/video_gen.py`
engine (`Lightricks/LTX-2.5` + `Wan 2.2 14B I2V` on Hugging Face ZeroGPU) with
automatic circuit-breaker protection and $0 cost guarantee.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from backend.engine import video_gen

logger = logging.getLogger("engine.zero_gpu_hook")


def generate_zero_gpu_hero_clip(
    prompt: str,
    output_path: str,
    hf_token: Optional[str] = None,
    image_path: Optional[str] = None,
    duration: float = 4.0,
    timeout: float = 28.0,
) -> Optional[str]:
    """
    Generates a moving AI video clip using free Hugging Face ZeroGPU Spaces
    (`Lightricks/LTX-2.5` -> `Wan 2.2 I2V`) via `video_gen.generate_ai_video_clip()`.
    Returns `output_path` on success, or `None` on quota exhaustion/queue so the caller
    can fall back to real moving B-roll.
    """
    res = video_gen.generate_ai_video_clip(
        prompt=prompt,
        image_path=image_path,
        duration=duration,
        mode="free_hf",
        hf_token=hf_token,
        output_path=output_path,
    )
    if res.get("status") == "success":
        final_p = res.get("output_path") or res.get("video_path")
        if final_p and os.path.exists(final_p):
            return final_p
    return None
