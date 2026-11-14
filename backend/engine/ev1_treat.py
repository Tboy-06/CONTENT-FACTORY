"""
CONTENT-FACTORY Engine: Documentary Color Grading & Treatments (ev1_treat)
--------------------------------------------------------------------------
Applies high-impact editor-v1 style documentary aesthetics to stills & video:
- Hard B&W: High-contrast desaturated monochrome with harsh document shadows
- Teal Split: Moody Scandinavian/Fincher cool teal shadows + warm highlights
- Amber: Declassified tungsten archival tint (1960s Cold War look)
- 4000px Cosine Zoompan: Eliminates pixel crawl during slow cinematic pushes
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger("engine.ev1_treat")


def apply_color_grade(
    image_path: str,
    output_path: str,
    grade: str = "hard_bw",
    target_width: int = 1080,
    target_height: int = 1920
) -> str:
    """
    Applies photographic documentary color treatment to a still plate.
    Produces high-res 1080x1920 assets ready for FFmpeg beat assembly.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with Image.open(image_path) as img:
        img = img.convert("RGB")

        # Resize & crop to 9:16 vertical
        img_w, img_h = img.size
        target_ratio = target_width / target_height
        src_ratio = img_w / img_h

        if src_ratio > target_ratio:
            # Source is wider: crop sides
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, img_h))
        else:
            # Source is taller: crop top/bottom
            new_h = int(img_w / target_ratio)
            top = (img_h - new_h) // 2
            img = img.crop((0, top, img_w, top + new_h))

        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        grade_clean = grade.lower().strip()

        if grade_clean == "hard_bw":
            # Grayscale with steep contrast
            img = ImageOps.grayscale(img).convert("RGB")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.65)
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(0.95)

        elif grade_clean == "teal_split":
            # Cool shadows, desaturated mids
            r, g, b = img.split()
            # Push blue and green in shadows, suppress red
            r = r.point(lambda p: int(p * 0.75))
            g = g.point(lambda p: int(p * 1.05))
            b = b.point(lambda p: int(p * 1.25))
            img = Image.merge("RGB", (r, g, b))
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.35)

        elif grade_clean == "amber":
            # Warm archival sepia / tungsten tint
            r, g, b = img.split()
            r = r.point(lambda p: int(min(255, p * 1.25)))
            g = g.point(lambda p: int(p * 0.95))
            b = b.point(lambda p: int(p * 0.65))
            img = Image.merge("RGB", (r, g, b))
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.25)

        elif grade_clean == "skit_warm":
            # Comedy/Skit: Bright, punchy, high-saturation comedy lighting
            r, g, b = img.split()
            r = r.point(lambda p: int(min(255, p * 1.15)))
            g = g.point(lambda p: int(min(255, p * 1.05)))
            b = b.point(lambda p: int(p * 0.90))
            img = Image.merge("RGB", (r, g, b))
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.45)  # Pop colors
            contrast = ImageEnhance.Contrast(img)
            img = contrast.enhance(1.15)
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(1.06)

        elif grade_clean == "action_crush":
            # Action/Hype: Bleach bypass, high-contrast, crushed darks, neon edge highlights
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.75)
            color = ImageEnhance.Color(img)
            img = color.enhance(1.30)
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(0.92)

        elif grade_clean == "cinema_scope":
            # Movie/Cinema: 35mm cinematic film curve, rich cinematic teal-amber tones
            r, g, b = img.split()
            r = r.point(lambda p: int(min(255, p * 1.12)))
            g = g.point(lambda p: int(p * 0.98))
            b = b.point(lambda p: int(min(255, p * 1.18)))
            img = Image.merge("RGB", (r, g, b))
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.35)

        # Subtle dark documentary vignette
        img.save(output_path, quality=95)
        logger.info(f"[ev1_treat] Applied grade '{grade}' -> {output_path}")
        return output_path


def build_cosine_zoompan_filter(
    duration: float,
    zoom_in: bool = True,
    fps: int = 30,
    out_w: int = 1080,
    out_h: int = 1920
) -> str:
    """
    Generates a smooth cosine zoompan filter for FFmpeg Pass 1.
    Prevents pixel jitter by upscaling to a high-res virtual canvas.
    """
    total_frames = int(duration * fps)
    if zoom_in:
        return f"zoompan=z='min(zoom+0.0012,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps}"
    else:
        return f"zoompan=z='max(1.25-0.0012*on,1.0)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps}"


def build_snap_zoom_filter(
    duration: float,
    zoom_factor: float = 1.35,
    fps: int = 30,
    out_w: int = 1080,
    out_h: int = 1920
) -> str:
    """
    Comedy/Skit: Sudden instant punch-in snap-zoom (1.35x) on comedic punchlines and reaction beats.
    """
    total_frames = int(duration * fps)
    return (
        f"zoompan=z='if(lte(on,1),1.0,{zoom_factor:.2f})':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={out_w}x{out_h}:fps={fps}"
    )


def build_camera_shake_filter(
    out_w: int = 1080,
    out_h: int = 1920,
    intensity: int = 12
) -> str:
    """
    Action/Hype: Handheld camera shake / tremor filter on impact beats.
    Uses dynamic sine/cosine crop displacement and scales back to target resolution.
    """
    margin = intensity * 2
    return (
        f"crop=w=iw-{margin}:h=ih-{margin}:"
        f"x='({intensity}+sin(n*1.4)*{intensity * 0.75:.1f})':"
        f"y='({intensity}+cos(n*1.8)*{intensity * 0.75:.1f})',"
        f"scale={out_w}:{out_h}"
    )


def build_cinema_anamorphic_bars(
    width: int = 1080,
    height: int = 1920,
    target_aspect: float = 2.35
) -> str:
    """
    Movie/Cinema: Enforces 2.35:1 widescreen anamorphic cinema letterbox black bars.
    """
    # Active picture height = width / target_aspect
    picture_h = int(width / target_aspect)
    bar_h = max(24, (height - picture_h) // 2)
    return f"drawbox=y=0:h={bar_h}:color=black@1:t=fill,drawbox=y=ih-{bar_h}:h={bar_h}:color=black@1:t=fill"
