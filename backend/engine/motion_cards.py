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
    margin_x = 48
    header_line_y = int(height * 0.12)
    footer_line_y = height - int(height * 0.10)
    header_text_y = int(height * 0.06)
    footer_text_y = height - int(height * 0.06)
    center_y = height // 2

    draw.rectangle([margin_x, margin_x, width - margin_x, height - margin_x], outline=(35, 40, 52), width=2)
    draw.line([margin_x, header_line_y, width - margin_x, header_line_y], fill=(28, 33, 44), width=1)
    draw.line([margin_x, footer_line_y, width - margin_x, footer_line_y], fill=(28, 33, 44), width=1)

    # Top Brand / Header
    draw.text((80, header_text_y), "DOCUMENTARY EVIDENCE ARCHIVE", fill=(100, 116, 139), font=font_small)
    draw.text((width - 240, header_text_y), "CLASSIFIED", fill=(239, 68, 68), font=font_small)

    tpl = template.lower().strip()

    if tpl == "red_slam_word":
        # Headline in white above center
        headline_y = center_y - 80
        draw.text((90, headline_y), headline.upper()[:40], fill=(148, 163, 184), font=font_medium)

        # Huge red highlight box centered vertically
        hl_text = highlight.upper()[:32]
        box_y = center_y + 10
        box_h = 120
        box_w = min(width - 160, max(420, len(hl_text) * 44 + 60))
        draw.rectangle([80, box_y, 80 + box_w, box_y + box_h], fill=(220, 38, 38))
        draw.text((105, box_y + 20), hl_text, fill=(255, 255, 255), font=font_huge)

    elif tpl == "stat_counter":
        # Category label above center
        headline_y = center_y - 90
        stat_y = center_y - 10
        underline_y = center_y + 110
        draw.text((90, headline_y), headline.upper()[:40], fill=(148, 163, 184), font=font_medium)

        # Gigantic stat counter number
        draw.text((90, stat_y), highlight.upper()[:24], fill=(248, 250, 252), font=font_huge)

        # Underline accent
        draw.rectangle([90, underline_y, min(width - 160, 480), underline_y + 8], fill=(59, 130, 246))

    elif tpl == "3_item_list":
        item_step = 80 if height < 1200 else 110
        start_y = center_y - 40
        headline_y = start_y - 85
        draw.text((90, headline_y), headline.upper()[:40], fill=(248, 250, 252), font=font_large)

        items = [i.strip() for i in highlight.split("·") if i.strip()]
        if not items:
            items = [highlight[:24], "Critical Finding", "Declassified"]

        for idx, item in enumerate(items[:3]):
            y = start_y + (idx * item_step)
            # Item badge
            draw.rectangle([90, y, 150, y + 55], fill=(30, 58, 138))
            draw.text((106, y + 10), f"0{idx+1}", fill=(186, 230, 253), font=font_small)
            # Item text
            draw.text((180, y + 8), item[:42], fill=(226, 232, 240), font=font_medium)

    elif tpl in ("workflow_stepper", "dev_stepper"):
        # Video 1 Matt Pocock multi-step pill stepper
        headline_y = center_y - 120
        draw.text((90, headline_y), headline.upper()[:40], fill=(248, 250, 252), font=font_large)

        # Parse steps from highlight (e.g. "install > setup > grill > spec > tickets > implement > review")
        raw_steps = [s.strip() for s in highlight.replace(">", ",").replace("·", ",").split(",") if s.strip()]
        if not raw_steps:
            raw_steps = ["install", "setup", "grill", "spec", "tickets", "implement", "review"]

        start_y = center_y - 20
        pill_w = min(220, (width - 180) // 2)
        pill_h = 52
        for idx, step_name in enumerate(raw_steps[:6]):
            col = idx % 2
            row = idx // 2
            px = 90 + col * (pill_w + 24)
            py = start_y + row * (pill_h + 18)

            # Active/completed state vs pending
            is_done = idx < 2
            is_active = idx == 2
            bg_color = (22, 101, 52) if is_done else ((30, 58, 138) if is_active else (30, 41, 59))
            border_color = (74, 222, 128) if is_done else ((96, 165, 250) if is_active else (51, 65, 85))
            txt_prefix = "✓ " if is_done else ("► " if is_active else "  ")

            draw.rectangle([px, py, px + pill_w, py + pill_h], fill=bg_color, outline=border_color, width=2)
            draw.text((px + 14, py + 12), f"{txt_prefix}{step_name.upper()[:12]}", fill=(255, 255, 255), font=font_small)

    elif tpl in ("star_badge", "metric_hook"):
        # Glowing star metric badge (e.g. ★ 320,000 STARS)
        headline_y = center_y - 100
        draw.text((90, headline_y), headline.upper()[:40], fill=(148, 163, 184), font=font_medium)

        badge_y = center_y - 20
        badge_w = min(width - 160, 580)
        badge_h = 100
        draw.rectangle([80, badge_y, 80 + badge_w, badge_y + badge_h], fill=(15, 23, 42), outline=(245, 158, 11), width=3)
        draw.text((105, badge_y + 16), f"★ {highlight.upper()[:24]}", fill=(251, 191, 36), font=font_huge)

    else:  # quote_box or fallback
        box_y = center_y
        box_h = 120
        headline_y = center_y - 85
        draw.text((90, headline_y), f"“{headline.upper()[:45]}”", fill=(203, 213, 225), font=font_large)
        draw.rectangle([90, box_y, width - 100, box_y + box_h], fill=(20, 24, 33), outline=(51, 65, 85), width=2)
        draw.text((120, box_y + 35), highlight[:60], fill=(254, 243, 199), font=font_medium)

    # Bottom Footer
    draw.text((90, footer_text_y), "EDITOR-V1 DIRECT DEPLOYMENT", fill=(71, 85, 105), font=font_small)

    img.save(output_path, quality=95)
    logger.info(f"[motion_cards] Rendered card '{template}' -> {output_path}")
    return output_path
