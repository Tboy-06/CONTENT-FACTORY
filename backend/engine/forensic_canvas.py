"""
CONTENT-FACTORY Engine: Forensic Canvas Renderer (forensic_canvas.py)
---------------------------------------------------------------------
Whisper-synced forensic micro-simulations (Vox / Johnny Harris / Coffeezilla style):
1. declassified_scan: Aged CIA memo / court filing with redacted black bars and
   translucent yellow highlighter sweep synced to narration timestamps.
2. evidence_board: Dark-mode investigation pinboard with entity cards and connecting
   red strings drawn between key figures.
3. map_flyover: Tactical geopolitical vector grid with targeting reticle, radar sweep,
   and coordinates counter.

$0 cost, 0 MB GPU load, rendered directly via Pillow + FFmpeg.
"""

from __future__ import annotations

import logging
import math
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger("engine.forensic_canvas")


def _get_fonts() -> Tuple[ImageFont.ImageFont, ...]:
    """Loads system or fallback fonts safely."""
    try:
        font_stamp = ImageFont.truetype("arialbd.ttf", 64)
        font_title = ImageFont.truetype("courbd.ttf", 46)
        font_body = ImageFont.truetype("cour.ttf", 34)
        font_bold = ImageFont.truetype("arialbd.ttf", 38)
        font_mono_small = ImageFont.truetype("courbd.ttf", 26)
    except Exception:
        fallback = ImageFont.load_default()
        font_stamp = fallback
        font_title = fallback
        font_body = fallback
        font_bold = fallback
        font_mono_small = fallback
    return font_stamp, font_title, font_body, font_bold, font_mono_small


def render_declassified_highlighter(
    headline: str,
    body_text: str,
    highlight_phrase: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    doc_id: str = "DOC-1974-B89",
    date_str: str = "OCTOBER 14, 1974"
) -> str:
    """
    Renders an authentic declassified government dossier plate with redacted
    black bars, top-secret stamps, and a translucent yellow highlighter pass.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    font_stamp, font_title, font_body, font_bold, font_mono = _get_fonts()

    # Aged archival paper background (warm vintage vellum)
    base = Image.new("RGBA", (width, height), color=(235, 227, 212, 255))
    draw = ImageDraw.Draw(base)

    # Subtle aged paper vignette / edge darkening
    margin = 54
    draw.rectangle([margin, margin, width - margin, height - margin], outline=(180, 170, 150), width=3)
    draw.rectangle([margin + 12, margin + 12, width - margin - 12, height - margin - 12], outline=(200, 190, 172), width=1)

    # Document Header
    header_y = int(height * 0.08)
    draw.text((margin + 30, header_y), f"CENTRAL INTELLIGENCE AGENCY // {doc_id}", fill=(80, 75, 68), font=font_mono)
    draw.text((margin + 30, header_y + 36), f"DATE OF DECLASSIFICATION: {date_str}", fill=(110, 105, 95), font=font_mono)

    # Red rubber stamp "TOP SECRET // DECLASSIFIED" with angle
    stamp_img = Image.new("RGBA", (580, 130), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp_img)
    stamp_draw.rectangle([6, 6, 570, 120], outline=(205, 38, 38, 220), width=6)
    stamp_draw.text((28, 26), "DECLASSIFIED", fill=(205, 38, 38, 225), font=font_stamp)
    rotated_stamp = stamp_img.rotate(-11, expand=True, resample=Image.BICUBIC)
    base.paste(rotated_stamp, (width - 560, header_y - 20), rotated_stamp)

    # Memo Divider Line
    divider_y = header_y + 110
    draw.line([margin + 30, divider_y, width - margin - 30, divider_y], fill=(160, 150, 135), width=2)

    # Title Subject
    subject_y = divider_y + 50
    draw.text((margin + 30, subject_y), f"SUBJECT: {headline.upper()[:44]}", fill=(30, 28, 26), font=font_title)

    # Body Paragraph with simulated redactions and yellow highlighter sweep
    start_body_y = subject_y + 110
    lines = []
    # Break body_text into lines of ~36 characters for typewriter typewriter look
    words = (body_text or headline).split()
    current_line = []
    for w in words:
        if sum(len(x) + 1 for x in current_line) + len(w) > 34:
            lines.append(" ".join(current_line))
            current_line = [w]
        else:
            current_line.append(w)
    if current_line:
        lines.append(" ".join(current_line))

    # Add filler confidential lines if text is short
    if len(lines) < 6:
        lines.append("INTERNAL MEMORANDUM FOR RECORD ONLY.")
        lines.append("FIELD DIRECTIVE RECORDING SPECIAL ACTIVITIES.")
        lines.append("DISTRIBUTION STRICTLY RESTRICTED TO CHIEF OF STATION.")

    line_y = start_body_y
    hl_phrase_lower = highlight_phrase.lower().strip()

    # Create highlighter overlay layer for alpha blending
    hl_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(hl_overlay)

    for i, line_text in enumerate(lines[:14]):
        draw.text((margin + 30, line_y), line_text, fill=(40, 36, 32), font=font_body)

        # Highlight match
        if hl_phrase_lower and any(kw in line_text.lower() for kw in hl_phrase_lower.split() if len(kw) > 3):
            # Translucent yellow marker sweep with ragged edges
            box_x0 = margin + 24
            box_x1 = min(width - margin - 30, margin + 30 + len(line_text) * 22)
            box_y0 = line_y - 4
            box_y1 = line_y + 44
            hl_draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(255, 235, 59, 135))

        # Add black redaction bars on certain confidential lines
        if i in (2, 5, 8) and len(line_text) > 12:
            redact_x = margin + 180
            redact_w = 320
            draw.rectangle([redact_x, line_y + 6, redact_x + redact_w, line_y + 36], fill=(20, 20, 20))

        line_y += 62

    # Merge highlighter overlay onto base
    final_img = Image.alpha_composite(base, hl_overlay)

    # Footer barcode / clearance note
    footer_draw = ImageDraw.Draw(final_img)
    footer_y = height - int(height * 0.11)
    footer_draw.line([margin + 30, footer_y, width - margin - 30, footer_y], fill=(160, 150, 135), width=1)
    footer_draw.text((margin + 30, footer_y + 20), "NATIONAL ARCHIVES RECORD ADMINISTRATION - UNCLASSIFIED", fill=(120, 115, 105), font=font_mono)

    rgb_img = final_img.convert("RGB")
    rgb_img.save(output_path, "JPEG", quality=92)
    logger.info(f"[forensic_canvas] Rendered declassified dossier plate -> {output_path}")
    return output_path


def render_evidence_board(
    headline: str,
    nodes: List[Dict[str, str]],
    output_path: str,
    width: int = 1080,
    height: int = 1920
) -> str:
    """
    Renders an investigation evidence pinboard with suspect/entity polaroids
    and connecting red yarn lines.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    _, font_title, font_body, font_bold, font_mono = _get_fonts()

    # Dark forensic pinboard background (obsidian slate with faint pinholes)
    img = Image.new("RGBA", (width, height), color=(18, 20, 26, 255))
    draw = ImageDraw.Draw(img)

    # Top Case File Header
    header_y = int(height * 0.08)
    draw.text((70, header_y), "SPECIAL INVESTIGATION DIVISION // CASE FILE", fill=(148, 163, 184), font=font_mono)
    draw.text((70, header_y + 40), headline.upper()[:36], fill=(248, 250, 252), font=font_title)
    draw.line([70, header_y + 105, width - 70, header_y + 105], fill=(35, 42, 56), width=2)

    # Setup 3 pinboard cards with robust node parsing (supports dicts or plain strings)
    def _parse_node(idx: int, default_title: str, default_desc: str):
        if idx >= len(nodes):
            return default_title, default_desc
        item = nodes[idx]
        if isinstance(item, dict):
            return str(item.get("title") or default_title), str(item.get("desc") or default_desc)
        elif isinstance(item, str):
            return item, default_desc
        return default_title, default_desc

    t1, d1 = _parse_node(0, "TARGET ORG", "OFFSHORE ACCOUNTS")
    t2, d2 = _parse_node(1, "KEY SUSPECT", "KNOWN OPERATOR")
    t3, d3 = _parse_node(2, "SECRET WIRE", "$42,000,000 TRANSFER")

    card_positions = [
        (120, 480, "ENTITY 01", t1, d1),
        (540, 840, "ENTITY 02", t2, d2),
        (160, 1260, "ENTITY 03", t3, d3)
    ]

    # Draw Red Connecting Yarn Lines between nodes first
    yarn_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    yarn_draw = ImageDraw.Draw(yarn_overlay)
    # Line 1 -> Line 2
    yarn_draw.line([(card_positions[0][0] + 180, card_positions[0][1] + 120),
                    (card_positions[1][0] + 180, card_positions[1][1] + 120)],
                   fill=(239, 68, 68, 220), width=5)
    # Line 2 -> Line 3
    yarn_draw.line([(card_positions[1][0] + 180, card_positions[1][1] + 120),
                    (card_positions[2][0] + 180, card_positions[2][1] + 120)],
                   fill=(239, 68, 68, 220), width=5)

    img = Image.alpha_composite(img, yarn_overlay)
    draw = ImageDraw.Draw(img)

    # Render Polaroid/Index Cards
    for x, y, tag, title, desc in card_positions:
        card_w, card_h = 380, 220
        # Card shadow
        draw.rectangle([x + 6, y + 6, x + card_w + 6, y + card_h + 6], fill=(10, 12, 16))
        # Card body (aged off-white cardstock)
        draw.rectangle([x, y, x + card_w, y + card_h], fill=(241, 245, 249), outline=(203, 213, 225), width=2)
        # Red pushpin at top-center of card
        pin_cx, pin_cy = x + card_w // 2, y + 12
        draw.ellipse([pin_cx - 9, pin_cy - 9, pin_cx + 9, pin_cy + 9], fill=(220, 38, 38))
        draw.ellipse([pin_cx - 4, pin_cy - 4, pin_cx + 4, pin_cy + 4], fill=(254, 202, 202))

        # Card Text
        draw.text((x + 24, y + 36), tag, fill=(100, 116, 139), font=font_mono)
        draw.text((x + 24, y + 74), title[:18].upper(), fill=(15, 23, 42), font=font_bold)
        draw.text((x + 24, y + 130), desc[:26], fill=(51, 65, 85), font=font_body)

    # Footer note
    footer_y = height - int(height * 0.08)
    draw.text((70, footer_y), "EVIDENCE TAMPERING IS PUNISHABLE BY FEDERAL LAW", fill=(100, 116, 139), font=font_mono)

    rgb_img = img.convert("RGB")
    rgb_img.save(output_path, "JPEG", quality=92)
    logger.info(f"[forensic_canvas] Rendered evidence pinboard plate -> {output_path}")
    return output_path


def render_geopolitical_map(
    location_name: str,
    coords: str,
    headline: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920
) -> str:
    """
    Renders a tactical vector map flyover plate with crosshairs, coordinate
    reticle, and radar beacon (Vox / Johnny Harris geopolitical style).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    _, font_title, font_body, font_bold, font_mono = _get_fonts()

    # Dark tactical radar grid background
    img = Image.new("RGB", (width, height), color=(11, 15, 25))
    draw = ImageDraw.Draw(img)

    # Tactical Coordinate Grid
    grid_step = 120
    for gx in range(0, width, grid_step):
        draw.line([(gx, 0), (gx, height)], fill=(20, 28, 44), width=1)
    for gy in range(0, height, grid_step):
        draw.line([(0, gy), (width, gy)], fill=(20, 28, 44), width=1)

    # Header Telemetry
    header_y = int(height * 0.08)
    draw.text((70, header_y), "GEOSPATIAL INTELLIGENCE // SATELLITE FLYOVER", fill=(56, 189, 248), font=font_mono)
    draw.text((70, header_y + 36), f"TARGET COORDINATES: {coords or '45.1663° N, 28.7901° E'}", fill=(148, 163, 184), font=font_mono)
    draw.line([70, header_y + 90, width - 70, header_y + 90], fill=(30, 41, 59), width=2)

    # Center Target Reticle & Radar Rings
    cx, cy = width // 2, height // 2 - 40
    for radius in (80, 180, 300):
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(38, 56, 89), width=2)

    # Crosshair lines
    draw.line([(cx - 340, cy), (cx - 40, cy)], fill=(56, 189, 248), width=2)
    draw.line([(cx + 40, cy), (cx + 340, cy)], fill=(56, 189, 248), width=2)
    draw.line([(cx, cy - 340), (cx, cy - 40)], fill=(56, 189, 248), width=2)
    draw.line([(cx, cy + 40), (cx, cy + 340)], fill=(56, 189, 248), width=2)

    # Target Pulse Point
    draw.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(239, 68, 68))
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 255, 255))

    # Target Location Callout Box
    box_x0 = cx - 240
    box_y0 = cy + 120
    box_x1 = cx + 240
    box_y1 = box_y0 + 130
    draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((box_x0 + 20, box_y0 + 18), "ACTIVE ZONE", fill=(56, 189, 248), font=font_mono)
    draw.text((box_x0 + 20, box_y0 + 54), location_name.upper()[:22], fill=(248, 250, 252), font=font_bold)

    # Headline Context Banner
    footer_y = height - int(height * 0.16)
    draw.rectangle([70, footer_y, width - 70, footer_y + 110], fill=(15, 23, 42), outline=(30, 41, 59), width=1)
    draw.text((95, footer_y + 20), "INTEL BRIEF:", fill=(148, 163, 184), font=font_mono)
    draw.text((95, footer_y + 54), headline[:36].upper(), fill=(226, 232, 240), font=font_title)

    img.save(output_path, "JPEG", quality=92)
    logger.info(f"[forensic_canvas] Rendered geopolitical map plate -> {output_path}")
    return output_path
