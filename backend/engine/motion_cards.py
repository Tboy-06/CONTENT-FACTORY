"""
CONTENT-FACTORY Engine: Documentary Motion Cards
------------------------------------------------
Generates 1080x1920 kinetic typography & stat cards for rapid documentary beats:
1. red_slam_word: Bold title with striking red accent block
2. stat_counter: Huge metric/numeric display with context
3. 3_item_list: 3-point strategic bullet breakdown
4. quote_box: High-contrast quotation with source attribution
"""

from __future__ import annotations

import logging
import os
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("engine.motion_cards")


def get_fonts():
    """Loads system or default fonts safely."""
    try:
        font_huge = ImageFont.truetype("arialbd.ttf", 76)
        font_large = ImageFont.truetype("arialbd.ttf", 54)
        font_medium = ImageFont.truetype("arial.ttf", 38)
        font_mono = ImageFont.truetype("courbd.ttf", 34)
        font_small = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font_huge = ImageFont.load_default()
        font_large = font_huge
        font_medium = font_huge
        font_mono = font_huge
        font_small = font_huge
    return font_huge, font_large, font_medium, font_mono, font_small


def render_motion_card(
    template: str,
    headline: str,
    highlight: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920
) -> str:
    """Renders a documentary-grade 1080x1920 plate based on the chosen template."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    font_huge, font_large, font_medium, font_mono, font_small = get_fonts()

    # Dark documentary base (deep obsidian charcoal)
    img = Image.new("RGB", (width, height), color=(14, 16, 22))
    draw = ImageDraw.Draw(img)

    # Subtle cinematic border lines
    draw.rectangle([48, 60, width - 48, height - 60], outline=(35, 40, 52), width=2)
    draw.line([48, 180, width - 48, 180], fill=(28, 33, 44), width=1)
    draw.line([48, height - 160, width - 48, height - 160], fill=(28, 33, 44), width=1)

    # Top Brand / Header
    draw.text((80, 105), "DOCUMENTARY EVIDENCE ARCHIVE", fill=(100, 116, 139), font=font_small)
    draw.text((width - 240, 105), "CLASSIFIED", fill=(239, 68, 68), font=font_small)

    tpl = template.lower().strip()

    if tpl == "red_slam_word":
        # Headline in white
        draw.text((90, 700), headline.upper()[:36], fill=(148, 163, 184), font=font_medium)

        # Huge red highlight box
        hl_text = highlight.upper()[:28]
        box_y = 820
        box_h = 130
        box_w = min(width - 160, max(420, len(hl_text) * 44 + 60))
        draw.rectangle([80, box_y, 80 + box_w, box_y + box_h], fill=(220, 38, 38))
        draw.text((105, box_y + 26), hl_text, fill=(255, 255, 255), font=font_huge)

    elif tpl == "stat_counter":
        # Category label
        draw.text((90, 680), headline.upper()[:36], fill=(148, 163, 184), font=font_medium)

        # Gigantic stat counter number
        draw.text((90, 780), highlight.upper()[:24], fill=(248, 250, 252), font=font_huge)

        # Underline accent
        draw.rectangle([90, 920, 480, 928], fill=(59, 130, 246))

    elif tpl == "3_item_list":
        draw.text((90, 640), headline.upper()[:36], fill=(248, 250, 252), font=font_large)

        items = [i.strip() for i in highlight.split("·") if i.strip()]
        if not items:
            items = [highlight[:24], "Critical Finding", "Declassified"]

        for idx, item in enumerate(items[:3]):
            y = 770 + (idx * 110)
            # Item badge
            draw.rectangle([90, y, 150, y + 60], fill=(30, 58, 138))
            draw.text((106, y + 12), f"0{idx+1}", fill=(186, 230, 253), font=font_small)
            # Item text
            draw.text((180, y + 10), item[:34], fill=(226, 232, 240), font=font_medium)

    else:  # quote_box or fallback
        draw.text((90, 680), f"“{headline.upper()[:40]}”", fill=(203, 213, 225), font=font_large)
        draw.rectangle([90, 810, width - 100, 960], fill=(20, 24, 33), outline=(51, 65, 85), width=2)
        draw.text((120, 850), highlight[:50], fill=(254, 243, 199), font=font_medium)

    # Bottom Footer
    draw.text((90, height - 120), "EDITOR-V1 DIRECT DEPLOYMENT", fill=(71, 85, 105), font=font_small)

    img.save(output_path, quality=95)
    logger.info(f"[motion_cards] Rendered card '{template}' -> {output_path}")
    return output_path
