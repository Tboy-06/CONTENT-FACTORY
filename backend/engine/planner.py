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


def generate_fallback_manifest(topic: str, job_id: int, duration_target: float = 45.0) -> Dict[str, Any]:
    """
    Deterministic documentary generator that creates an authentic, topic-tailored
    manifest based on the user's exact subject. Supports short-form (45-60s) and
    long-form (3m-5m+) multi-act documentary narratives.
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

    # If long-form (3m+ or 5m+), expand narrative with Acts 2, 3, and 4
    if duration_target > 60:
        extra_acts = [
            (9, f"Phase two began behind closed doors, where the initial architecture of {topic_clean} was redesigned from scratch.", "stat_counter", "ARCHITECTURAL OVERHAUL", "5X EFFICIENCY MULTIPLIER", "blueprints and architectural drafts", "amber"),
            (10, f"Engineers and strategists worked in total secrecy, knowing that a single flaw could collapse the entire operation.", "treated_image", None, None, f"secret war room strategists analyzing {topic_clean} data graphs", "hard_bw"),
            (11, f"The breakthrough came when they discovered an overlooked vulnerability in the conventional method.", "motion_card", "CRITICAL VULNERABILITY", "EXPLOITING THE GAP", None, "teal_split"),
            (12, f"Within six months, the prototype had demonstrated results that defied all standard predictions.", "stat_counter", "TEST BENCH RESULTS", "99.8% PRECISION RATING", None, "amber"),
            (13, f"Competitors scrambled to decipher how {topic_clean} was achieving such unprecedented speed.", "3_item_list", "COMPETITIVE MOATS", "SPEED · DEFENSE · MOAT", None, "teal_split"),
            (14, f"By the time the market understood the shift, the competitive barrier was already insurmountable.", "treated_image", None, None, f"imposing steel fortress vault symbolizing resilience of {topic_clean}", "hard_bw"),
            (15, f"Then came the turning point: an unexpected crisis that pushed {topic_clean} to its absolute limit.", "red_slam_word", "THE TURNING POINT", "CRITICAL STRESS TEST", None, "amber"),
            (16, f"When external pressure spiked, older legacy systems failed one by one.", "treated_image", None, None, f"dramatic stormy industrial landscape representing systemic stress on {topic_clean}", "teal_split"),
            (17, f"Only the refined methodology of {topic_clean} held firm under the intense scrutiny.", "stat_counter", "UPTIME RESILIENCE", "100% OPERATIONAL", None, "amber"),
            (18, f"This single performance proved that the new paradigm was not just viable—it was inevitable.", "quote_box", "FIELD REPORT", "THE IRREVERSIBLE SHIFT", None, "hard_bw"),
            (19, f"Institutions worldwide took note, beginning the mass transition that defines our current era.", "treated_image", None, None, f"global satellite telemetry grid illuminating worldwide adoption of {topic_clean}", "teal_split"),
            (20, f"The debate was officially settled: {topic_clean} had rewritten the rules permanently.", "motion_card", "FINAL VERDICT", "PARADIGM CONQUERED", None, "amber"),
            (21, f"Looking forward, the lessons forged during the development of {topic_clean} remain more relevant than ever.", "3_item_list", "CORE LESSONS", "ADAPT · ENDURE · SCALE", None, "hard_bw"),
            (22, f"Those who recognize these historical inflection points early are the ones who capture the greatest upside.", "stat_counter", "EXPONENTIAL UPSIDE", "THE 1% ASYMMETRY", None, "teal_split"),
            (23, f"The window of opportunity around {topic_clean} is actively moving right before our eyes.", "treated_image", None, None, f"cinematic sunrise over horizon casting golden illumination on {topic_clean} future", "amber"),
            (24, f"And those who master its principles today will be the ones directing the next decade.", "red_slam_word", "FINAL MASTERY", "DIRECT THE FUTURE", None, "amber"),
        ]

        beat_counter = 17
        for sid, text, card_tpl, hl, val, img_prompt, grade in extra_acts:
            s_beats = []
            if card_tpl in ("red_slam_word", "stat_counter", "3_item_list", "quote_box"):
                s_beats.append({
                    "id": f"beat_{beat_counter:02d}",
                    "type": "motion_card",
                    "template": card_tpl,
                    "headline": hl or "DIRECTOR EVIDENCE",
                    "highlight": val or topic_clean.upper()[:20],
                    "duration": 1.5,
                    "sfx": "thud.wav" if beat_counter % 2 == 0 else "whoosh.wav"
                })
                beat_counter += 1
            if img_prompt or len(s_beats) < 2:
                s_beats.append({
                    "id": f"beat_{beat_counter:02d}",
                    "type": "treated_image",
                    "prompt": f"cinematic documentary still, {img_prompt or topic_clean}, 35mm grain, chiaroscuro",
                    "grade": grade or "teal_split",
                    "duration": 1.6,
                    "sfx": "click.wav"
                })
                beat_counter += 1
            sentences_data.append({"id": sid, "text": text, "beats": s_beats})

    return {
        "job_id": job_id,
        "topic": topic_clean,
        "style": "editor-v1",
        "duration_target": duration_target,
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
    For long-form videos (>60s), generates across 4 sequential Acts to eliminate LLM token truncation.
    Consults the Obsidian director vault for proven hooks and style rules.
    Falls back gracefully if Ollama / cloud models are unreachable.
    """
    format_label = "16:9 horizontal YouTube documentary" if aspect_ratio == "16:9" else "9:16 vertical documentary short"
    logger.info(f"[Planner] Generating {format_label} ({duration_target}s) beat plan for: '{topic}' (Job #{job_id})")

    # Retrieve connected directing principles from Obsidian Second Brain
    vault_context = query_director_vault(topic)

    # -------------------------------------------------------------
    # CASE A: LONG-FORM DOCUMENTARY (>60s) - 4 SEQUENTIAL ACTS
    # -------------------------------------------------------------
    if duration_target > 60:
        logger.info(f"[Planner] Activating 4-Act chapter generation for long-form: '{topic}'")
        acts_plan = [
            (1, "The Inciting Anomaly & Hook", 6),
            (2, "The Hidden Background & Catalyst", 6),
            (3, "The Crisis & Breakthrough Revelation", 6),
            (4, "The Aftermath & Modern Takeaway", 6)
        ]
        all_sentences = []
        global_sent_id = 1
        global_beat_id = 1

        try:
            for act_num, act_title, count in acts_plan:
                act_prompt = (
                    f"Plan Act {act_num}: '{act_title}' for a long-form {format_label} on the topic: '{topic}'.\n"
                    f"Write {count} consecutive spoken sentences. Each sentence must have 2 visual beats (motion_card or treated_image).\n"
                    f"{vault_context}\n"
                    f"Output strictly a JSON object with a 'sentences' array."
                )
                raw_act_json = await ask_brain(
                    prompt=act_prompt,
                    system_prompt=PLANNER_SYSTEM_PROMPT,
                    format_json=True,
                    num_predict=1500
                )
                m = re.search(r'\{.*\}', raw_act_json, re.DOTALL)
                if m:
                    act_data = json.loads(m.group(0))
                    for s in act_data.get("sentences", []):
                        s["id"] = global_sent_id
                        s["act"] = act_num
                        s["chapter"] = act_title
                        for b in s.get("beats", []):
                            b["id"] = f"beat_{global_beat_id:02d}"
                            b["aspect_ratio"] = aspect_ratio
                            global_beat_id += 1
                        all_sentences.append(s)
                        global_sent_id += 1

            if len(all_sentences) >= 12:
                all_beats = [b for s in all_sentences for b in s.get("beats", [])]
                hook_txt = all_sentences[0].get("text", "")
                log_script_to_vault(job_id, topic, hook_txt, "Long-Form Documentary", all_beats)
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "style": "editor-v1",
                    "aspect_ratio": aspect_ratio,
                    "duration_target": duration_target,
                    "sentences": all_sentences
                }
        except Exception as e:
            logger.info(f"[Planner] Multi-act brain loop interrupted ({e}), using long-form fallback manifest")

    # -------------------------------------------------------------
    # CASE B: SHORT-FORM (<=60s) OR FALLBACK
    # -------------------------------------------------------------
    prompt = f"Plan a {int(duration_target)}-second high-retention {format_label} on the topic: '{topic}'.{vault_context}"

    try:
        raw_json_str = await ask_brain(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            format_json=True
        )

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
    manifest = generate_fallback_manifest(topic, job_id, duration_target=duration_target)
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
