from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from backend.config import get_settings

settings = get_settings()


class GeminiVision:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self._configured = False

    def _ensure_configured(self):
        if not self._configured and self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True

    def _encode_video_frames(self, video_path: str, max_frames: int = 20) -> List[str]:
        """Extract and base64-encode frames from video for vision analysis."""
        import subprocess
        import tempfile

        frames_b64 = []
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract frames using ffmpeg
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", video_path,
                "-vf", f"fps={max_frames}/30,scale=512:-1",
                "-frames:v", str(max_frames),
                f"{tmpdir}/frame_%03d.jpg"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")

            # Read and encode frames
            for f in sorted(os.listdir(tmpdir)):
                if f.endswith(".jpg"):
                    with open(os.path.join(tmpdir, f), "rb") as img:
                        frames_b64.append(base64.b64encode(img.read()).decode())

        return frames_b64

    async def analyze_video_style(
        self,
        video_path: str,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a reference video and extract style DNA."""
        self._ensure_configured()

        frames_b64 = self._encode_video_frames(video_path, max_frames=15)

        default_prompt = """
        Analyze this video and extract its STYLE DNA for replication. Return JSON:

        {
            "hook_formula": {
                "pattern": "e.g., Problem → Agitate → Solution → Proof → CTA",
                "first_3_seconds": "exact hook structure",
                "emotional_triggers": ["curiosity", "fear", "hope"]
            },
            "pacing": {
                "avg_scene_duration_sec": 0,
                "cut_frequency": "fast/medium/slow",
                "loop_point_sec": 0,
                "energy_curve": "rising/falling/wave"
            },
            "visual_style": {
                "color_palette": ["hex1", "hex2"],
                "lighting": "natural/studio/dramatic",
                "camera_style": "static/handheld/smooth/gimbal",
                "composition_rules": ["rule_of_thirds", "centered", "negative_space"]
            },
            "character_design": {
                "style": "cartoon/realistic/anime/minimalist",
                "proportions": "normal/exaggerated/chibi",
                "key_features": ["oversized_head", "expressive_eyes", "flat_colors"],
                "consistency_markers": ["color_scheme", "silhouette", "accessories"]
            },
            "scene_structure": {
                "typical_scenes": ["intro", "problem", "solution", "demo", "cta"],
                "transition_style": "cut/fade/zoom/swipe",
                "text_overlay_style": "minimal/heavy/animated"
            },
            "audio_style": {
                "music_genre": "upbeat/lofi/cinematic/none",
                "voice_style": "energetic/calm/authoritative/friendly",
                "sfx_usage": "minimal/moderate/heavy"
            },
            "platform_optimizations": {
                "tiktok": {"duration_sec": 15, "hook_at": 0, "loop_at": 15},
                "youtube_shorts": {"duration_sec": 60, "hook_at": 0, "loop_at": 15},
                "instagram_reels": {"duration_sec": 30, "hook_at": 0, "loop_at": 15}
            }
        }

        Be specific. Extract exact patterns, not generic advice.
        """

        prompt = custom_prompt or default_prompt

        # Prepare parts for vision model
        parts = [prompt]
        for frame_b64 in frames_b64:
            parts.append({
                "mime_type": "image/jpeg",
                "data": frame_b64
            })

        model = genai.GenerativeModel(settings.gemini_vision_model)
        response = await model.generate_content_async(
            parts,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
                response_mime_type="application/json",
            )
        )

        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse vision response", "raw": response.text}

    async def analyze_image_style(self, image_path: str) -> Dict[str, Any]:
        """Analyze a single image for style reference."""
        self._ensure_configured()

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        prompt = """
        Analyze this image for character/visual style reference. Return JSON:
        {
            "style": "cartoon/anime/realistic/minimalist",
            "color_palette": ["hex1", "hex2"],
            "character_traits": ["oversized_head", "expressive_eyes"],
            "composition": "centered/rule_of_thirds",
            "lighting": "flat/soft/dramatic",
            "usable_as_character_ref": true/false
        }
        """

        model = genai.GenerativeModel(settings.gemini_vision_model)
        response = await model.generate_content_async([
            prompt,
            {"mime_type": "image/jpeg", "data": img_b64}
        ], generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ))

        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse", "raw": response.text}


_gemini_vision: Optional[GeminiVision] = None


def get_gemini_vision() -> GeminiVision:
    global _gemini_vision
    if _gemini_vision is None:
        _gemini_vision = GeminiVision()
    return _gemini_vision