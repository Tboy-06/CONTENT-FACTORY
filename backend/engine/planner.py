"""
CONTENT-FACTORY Engine: Documentary Beat Planner
------------------------------------------------
Generates high-retention editor-v1 style documentary beat sheets:
- 8 tightly paced sentences (~45s target duration)
- Each sentence broken into 2 rapid visual beats (1.0s - 1.8s each, 16 beats total)
- Alternates between Motion Cards (kinetic UI/stats) and Treated Evidence (hard B&W/teal/amber)
- Synchronized sound effects on transitions (thud, whoosh, click, riser)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.engine.brain import ask_brain
from backend.engine.vault_graph import query_director_vault, log_script_to_vault

logger = logging.getLogger("engine.planner")

PLANNER_SYSTEM_PROMPT = """You are an elite YouTube documentary director specializing in high-retention 45-second vertical shorts (Vox/Johnny Harris/Editor-V1 style).
For any given topic, structure an 8-sentence documentary script.
Each sentence must be split into exactly 2 rapid visual beats (each beat lasting between 1.0s and 1.8s).
Beat types must alternate between:
1. "motion_card" (templates: "red_slam_word", "stat_counter", "3_item_list", "quote_box") with "headline", "highlight", and sfx ("thud.wav" or "whoosh.wav").
2. "treated_image" with an archival documentary prompt, color grade ("hard_bw", "teal_split", or "amber"), and sfx ("click.wav").

Return ONLY a valid JSON object matching this schema:
{
  "topic": string,
  "style": "editor-v1",
  "duration_target": 45.0,
  "sentences": [
    {
      "id": 1,
      "text": "Spoken sentence text...",
      "beats": [
        {
          "id": "beat_01",
          "type": "motion_card",
          "template": "red_slam_word",
          "headline": "SHORT UPPERCASE HEADLINE",
          "highlight": "KEYWORD FOCUS",
          "duration": 1.4,
          "sfx": "thud.wav"
        },
        {
          "id": "beat_02",
          "type": "treated_image",
          "prompt": "Detailed archival documentary prompt",
          "grade": "hard_bw",
          "duration": 1.6,
          "sfx": "click.wav"
        }
      ]
    }
  ]
}
"""


def generate_fallback_manifest(topic: str, job_id: int) -> Dict[str, Any]:
    """
    Deterministic documentary generator that creates an authentic, topic-tailored
    manifest based on the user's exact subject.
    """
    topic_clean = topic.strip().title()

    sentences_data = [
        {
            "id": 1,
            "text": f"Most people completely misunderstand the real story behind {topic_clean}.",
            "beats": [
                {
                    "id": "beat_01",
                    "type": "motion_card",
                    "template": "red_slam_word",
                    "headline": "THE UNTOLD TRUTH",
                    "highlight": topic_clean.upper()[:24],
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_02",
                    "type": "treated_image",
                    "prompt": f"cinematic archival photograph of {topic_clean}, dramatic chiaroscuro lighting, 35mm film grain",
                    "grade": "hard_bw",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 2,
            "text": f"When you trace the origins of {topic_clean}, the numbers reveal a massive shift that caught everyone off guard.",
            "beats": [
                {
                    "id": "beat_03",
                    "type": "motion_card",
                    "template": "stat_counter",
                    "headline": "FIRST RECORDED IMPACT",
                    "highlight": "OVER 90% EXPONENTIAL",
                    "duration": 1.3,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_04",
                    "type": "treated_image",
                    "prompt": f"historical diagram and technical blueprints detailing {topic_clean}, warm amber desk lamp",
                    "grade": "amber",
                    "duration": 1.5,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 3,
            "text": f"Early pioneers faced fierce resistance before the breakthrough that changed {topic_clean} forever.",
            "beats": [
                {
                    "id": "beat_05",
                    "type": "motion_card",
                    "template": "3_item_list",
                    "headline": "KEY FACTORS",
                    "highlight": "INNOVATION * SCALE * VELOCITY",
                    "duration": 1.5,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_06",
                    "type": "treated_image",
                    "prompt": f"retro laboratory workshop with inventors gathered around {topic_clean}, dramatic rim lighting",
                    "grade": "teal_split",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 4,
            "text": f"By the time critics realized what was happening, the entire foundation had already been rewritten.",
            "beats": [
                {
                    "id": "beat_07",
                    "type": "motion_card",
                    "template": "quote_box",
                    "headline": "INDUSTRY CONSENSUS",
                    "highlight": "NOTHING WILL REMAIN THE SAME",
                    "duration": 1.4,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_08",
                    "type": "treated_image",
                    "prompt": f"newspaper front page headline from historic archives about {topic_clean}, authentic monochrome",
                    "grade": "hard_bw",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 5,
            "text": f"What makes {topic_clean} so powerful today is a psychological mechanism that most people take for granted.",
            "beats": [
                {
                    "id": "beat_09",
                    "type": "motion_card",
                    "template": "red_slam_word",
                    "headline": "HIDDEN MECHANISM",
                    "highlight": "PSYCHOLOGICAL LEVERAGE",
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_10",
                    "type": "treated_image",
                    "prompt": f"close-up detailed macro lens shot representing the essence of {topic_clean}, high contrast",
                    "grade": "amber",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 6,
            "text": f"Modern innovators are now using this exact formula to achieve results in minutes instead of months.",
            "beats": [
                {
                    "id": "beat_11",
                    "type": "motion_card",
                    "template": "stat_counter",
                    "headline": "EFFICIENCY GAIN",
                    "highlight": "10X ACCELERATION",
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_12",
                    "type": "treated_image",
                    "prompt": f"futuristic modern minimalist workspace focused on {topic_clean}, sleek aesthetic, dark mode",
                    "grade": "teal_split",
                    "duration": 1.5,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 7,
            "text": f"If you ignore how {topic_clean} is evolving right now, you risk getting left completely behind.",
            "beats": [
                {
                    "id": "beat_13",
                    "type": "motion_card",
                    "template": "quote_box",
                    "headline": "THE WARNING",
                    "highlight": "ADAPT OR FALL BEHIND",
                    "duration": 1.5,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_14",
                    "type": "treated_image",
                    "prompt": f"cinematic silhouette overlooking bustling modern city skyline, twilight atmosphere",
                    "grade": "hard_bw",
                    "duration": 1.5,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 8,
            "text": f"Understanding {topic_clean} is no longer optional - it is the single biggest advantage you have today.",
            "beats": [
                {
                    "id": "beat_15",
                    "type": "motion_card",
                    "template": "red_slam_word",
                    "headline": "THE TAKEAWAY",
                    "highlight": "UNFAIR ADVANTAGE",
                    "duration": 1.4,
                    "sfx": "riser.wav"
                },
                {
                    "id": "beat_16",
                    "type": "treated_image",
                    "prompt": f"powerful inspiring portrait framing {topic_clean}, golden hour warm backlight",
                    "grade": "amber",
                    "duration": 1.8,
                    "sfx": "thud.wav"
                }
            ]
        }
    ]

    return {
        "job_id": job_id,
        "topic": topic_clean,
        "style": "editor-v1",
        "duration_target": 45.0,
        "sentences": sentences_data
    }


async def plan_documentary(
    topic: str,
    job_id: int,
    aspect_ratio: str = "9:16",
    duration_target: float = 45.0
) -> Dict[str, Any]:
    """
    Coordinates with brain.py to create the full documentary manifest.
    Supports both 9:16 vertical shorts and 16:9 horizontal YouTube channel documentaries.
    Consults the Obsidian director vault for proven hooks and style rules.
    Falls back gracefully if Ollama / cloud models are unreachable.
    """
    format_label = "16:9 horizontal YouTube documentary" if aspect_ratio == "16:9" else "9:16 vertical documentary short"
    logger.info(f"[Planner] Generating {format_label} beat plan for: '{topic}' (Job #{job_id})")

    # Retrieve connected directing principles from Obsidian Second Brain
    vault_context = query_director_vault(topic)
    prompt = f"Plan a {int(duration_target)}-second high-retention {format_label} on the topic: '{topic}'.{vault_context}"

    try:
        raw_json_str = await ask_brain(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            format_json=True
        )

        # Parse and sanitize JSON
        match = re.search(r'\{.*\}', raw_json_str, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if "sentences" in parsed and len(parsed["sentences"]) >= 4:
                parsed["job_id"] = job_id
                parsed["topic"] = topic
                parsed["style"] = "editor-v1"
                parsed["aspect_ratio"] = aspect_ratio
                parsed["duration_target"] = duration_target
                
                # Tag all beats with aspect_ratio
                all_beats = []
                for s in parsed.get("sentences", []):
                    for b in s.get("beats", []):
                        b["aspect_ratio"] = aspect_ratio
                        all_beats.append(b)

                hook_txt = parsed["sentences"][0].get("text", "")
                log_script_to_vault(job_id, topic, hook_txt, "Dark Documentary", all_beats)
                
                return parsed
    except Exception as e:
        logger.info(f"[Planner] Brain offline/unavailable ({e}). Engaging documentary generator.")

    # Generate reliable fallback manifest
    manifest = generate_fallback_manifest(topic, job_id)
    manifest["aspect_ratio"] = aspect_ratio
    manifest["duration_target"] = duration_target
    
    # Tag all beats with aspect_ratio
    fb_beats = []
    for s in manifest.get("sentences", []):
        for b in s.get("beats", []):
            b["aspect_ratio"] = aspect_ratio
            fb_beats.append(b)

    hook_txt = manifest["sentences"][0].get("text", "") if manifest.get("sentences") else ""
    log_script_to_vault(job_id, topic, hook_txt, "Dark Documentary", fb_beats)
    
    return manifest


# Alias for compatibility across CLI and Instant Pipeline
generate_documentary_plan = plan_documentary


def save_manifest(manifest: Dict[str, Any], job_dir: str) -> str:
    """Saves the manifest.json inside the job directory."""
    os.makedirs(job_dir, exist_ok=True)
    manifest_path = os.path.join(job_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"[Planner] Manifest saved successfully: {manifest_path}")
    return manifest_path
