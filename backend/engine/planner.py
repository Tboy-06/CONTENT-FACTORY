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
from backend.engine.researcher import research_fact_dossier
from backend.engine.reflexion import audit_and_heal_beats

logger = logging.getLogger("engine.planner")

GENRES = ["auto", "crime_doc", "comedy_skit", "action_hype", "movie_cinema", "viral_edu"]


def detect_genre(topic: str, prompt: str = "") -> str:
    """Auto-detects one of the 5 genre archetypes from topic/prompt."""
    combined = f"{topic} {prompt}".lower()
    
    if any(k in combined for k in ["funny", "skit", "prank", "humor", "comedy", "laugh", "awkward", "parody", "roast", "joke", "meme"]):
        return "comedy_skit"
    if any(k in combined for k in ["action", "fight", "battle", "hype", "beast", "workout", "gym", "combat", "chase", "explosion", "speed", "anime"]):
        return "action_hype"
    if any(k in combined for k in ["movie", "cinema", "trailer", "film", "hollywood", "cinematic", "screenplay", "scene", "monologue", "widescreen"]):
        return "movie_cinema"
    if any(k in combined for k in ["crime", "cia", "kgb", "fbi", "conspiracy", "scandal", "murder", "heist", "classified", "secret", "submarine", "azorian", "espionage", "investigation"]):
        return "crime_doc"
    if any(k in combined for k in ["money", "how to", "why", "tech", "code", "crypto", "business", "science", "economy", "ai", "guide", "tutorial", "explain", "system", "psychology"]):
        return "viral_edu"
    
    return "crime_doc"


def get_genre_rules(genre: str) -> str:
    """Returns strict editorial and physics rules for the active genre."""
    g = genre.lower()
    if g == "comedy_skit":
        return """[GENRE EDITING PHYSICS: COMEDY / SKIT]:
- Pacing: Rapid 25-35 CPM jump-cuts. Short punchy dialogue.
- Visual Mechanics: Sudden 1.35x snap-zooms ("camera_movement": "snap_zoom") on punchline beats.
- Comedic Timing: "pause_before": 0.3 comedic dead-air pause before punchline/twist lines.
- Color Treatment: "skit_warm" (bright, punchy, high-saturation comedy lighting).
- SFX: "pop.wav", "hit.wav", "click.wav", "whoosh.wav"."""
    elif g == "action_hype":
        return """[GENRE EDITING PHYSICS: ACTION / HYPE]:
- Pacing: Ultra-rapid 40-55 CPM (1.0s-1.8s beat cuts). Maximum velocity.
- Visual Mechanics: Handheld camera shake ("camera_movement": "camera_shake") on impact beats.
- Typography: Kinetic bold "red_slam_word" motion cards on climactic beats.
- Color Treatment: "action_crush" (bleach bypass, crushed darks, neon edge contrast).
- SFX: Heavy bass "thud.wav", rapid "whoosh.wav", tension "riser.wav"."""
    elif g == "movie_cinema":
        return """[GENRE EDITING PHYSICS: MOVIE / CINEMA]:
- Pacing: Measured 12-18 CPM. Elegant longer takes allowing visual immersion.
- Visual Mechanics: 2.35:1 widescreen anamorphic cinema letterbox bars ("anamorphic_bars": true).
- Camera Shaders: Slow 3D "rack_focus_bokeh" and "orbital" depth shifts. Minimal UI overlays on story beats.
- Color Treatment: "cinema_scope" (35mm Kodak film emulation, teal-amber anamorphic grading).
- SFX: Subtle cinematic room tone, dramatic low-end "thud.wav"."""
    elif g == "viral_edu":
        return """[GENRE EDITING PHYSICS: VIRAL EDU / EXPLAINER]:
- Pacing: Continuous 28-38 CPM visual switches (1.8s-2.5s intervals).
- Motion Cards: Heavy rotation of "stat_counter", "workflow_stepper", "3_item_list".
- Camera Shaders: Constant cosine punch-ins ("cosine_zoom") to hold viewer focus.
- Color Treatment: "teal_split" or "hard_bw".
- SFX: Crisp interface "click.wav", "whoosh.wav", reveal "thud.wav"."""
    else: # crime_doc
        return """[GENRE EDITING PHYSICS: CRIME / INVESTIGATIVE DOC]:
- Pacing: Deliberate high-tension 18-24 CPM cadence.
- Forensic Canvas: Heavy use of "declassified_scan" (redacted highlighter), "evidence_board" (red yarn suspect pinboard), "map_flyover" (tactical vector radar).
- Audio Texture: Archival radio voice bandpass filter (300Hz-3200Hz) on declassified quote beats.
- Color Treatment: "teal_split" or "hard_bw" (Fincher chiaroscuro).
- SFX: Heavy bass "thud.wav", typewriter "click.wav"."""


PLANNER_SYSTEM_PROMPT = """You are an elite YouTube documentary director specializing in high-retention vertical shorts (Vox/Johnny Harris/Editor-V1 style).
For any given topic, structure an 8-sentence documentary script.
Each sentence must be split into exactly 2 rapid visual beats (each beat lasting between 1.0s and 1.8s, total 16 beats).

Strict Visual Choreography Rules:
1. Beat #1 MUST be "hero_hook": A high-tension 3-second moving cinematic video hook or 3D camera move.
2. Beat types to balance across the 16 beats:
   - "hero_hook": Beat 1 moving video opening.
   - "declassified_scan": Aged government memo / CIA dossier with redacted black bars and translucent yellow highlighter sweep.
   - "evidence_board": Dark forensic pinboard with entity suspect nodes and connecting red yarn lines.
   - "map_flyover": Tactical geopolitical vector grid with targeting reticle, coordinates, and radar beacon.
   - "motion_card" (templates: "red_slam_word", "stat_counter", "3_item_list", "quote_box", "workflow_stepper", "star_badge") with "headline", "highlight", and sfx ("thud.wav" or "whoosh.wav").
   - "treated_image": With explicit "visual_prompt", "grade" ("hard_bw"|"teal_split"|"amber"|"skit_warm"|"action_crush"|"cinema_scope"), and "camera_movement" ("orbital"|"dolly_vertigo"|"rack_focus_bokeh"|"snap_zoom"|"camera_shake").
   - "broll_video": Free moving B-roll with "broll_query" and "visual_prompt".

Ensure high visual variety: every 2-3 beats must alternate between motion cards/highlighters and 3D treated imagery.

Return ONLY a valid JSON object matching this schema:
{
  "topic": string,
  "style": "editor-v1",
  "genre": "crime_doc",
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
          "visual_prompt": "Cinematic 35mm anamorphic archival film shot, volumetric chiaroscuro shadows, 35mm Kodak grain, slow dramatic push-in zoom, 8k UHD",
          "prompt": "Detailed archival documentary prompt",
          "grade": "hard_bw",
          "camera_movement": "slow_zoom_in",
          "duration": 1.6,
          "sfx": "click.wav"
        }
      ]
    }
  ]
}
"""


def generate_fallback_manifest(
    topic: str,
    job_id: int,
    duration_target: float = 45.0,
    fact_dossier: Optional[Dict[str, Any]] = None,
    genre: str = "crime_doc"
) -> Dict[str, Any]:
    """
    Deterministic documentary generator that creates an authentic, topic-tailored
    manifest based on the user's exact subject, verified FactDossier, and selected Genre physics.
    Supports short-form (45-60s) and long-form (3m-5m+) multi-act narratives.
    """
    genre_clean = (genre or "crime_doc").lower()
    if genre_clean not in GENRES:
        genre_clean = "crime_doc"
    topic_clean = topic.strip().title()

    # Genre physics styling defaults
    if genre_clean == "comedy_skit":
        default_grade = "skit_warm"
        hero_cam = "snap_zoom"
        impact_sfx = "hit.wav"
        whoosh_sfx = "whoosh.wav"
    elif genre_clean == "action_hype":
        default_grade = "action_crush"
        hero_cam = "camera_shake"
        impact_sfx = "thud.wav"
        whoosh_sfx = "whoosh.wav"
    elif genre_clean == "movie_cinema":
        default_grade = "cinema_scope"
        hero_cam = "rack_focus_bokeh"
        impact_sfx = "thud.wav"
        whoosh_sfx = "click.wav"
    elif genre_clean == "viral_edu":
        default_grade = "teal_split"
        hero_cam = "dolly_vertigo"
        impact_sfx = "thud.wav"
        whoosh_sfx = "whoosh.wav"
    else:  # crime_doc
        default_grade = "hard_bw"
        hero_cam = "dolly_vertigo"
        impact_sfx = "thud.wav"
        whoosh_sfx = "click.wav"

    # Pull real-world facts from dossier if available
    facts = fact_dossier or {}
    metric_1 = (facts.get("key_metrics") or ["OVER 90% EXPONENTIAL"])[0].upper()
    metric_2 = (facts.get("key_metrics") or ["10X ACCELERATION"])[-1].upper()
    date_1 = (facts.get("key_dates") or ["1974"])[0]
    coords = facts.get("coordinates") or "38.8977° N, 77.0365° W"
    loc_name = facts.get("location_name") or topic_clean[:18].upper()
    quote_text = facts.get("verified_quote") or "NOTHING WILL REMAIN THE SAME"
    summary_text = facts.get("summary") or f"CLASSIFIED MEMORANDUM REGARDING THE HISTORIC EMERGENCE OF {topic_clean.upper()}."

    # Build entity nodes for evidence_board
    ent_list = facts.get("key_entities") or [topic_clean[:16], "CENTRAL INTELLIGENCE", "GLOBAL IMPACT"]
    evidence_nodes = [
        {"title": ent_list[0][:16], "desc": "CORE OPERATION"},
        {"title": ent_list[1][:16] if len(ent_list) > 1 else "AGENCY DIRECTIVE", "desc": "OVERSIGHT TASKFORCE"},
        {"title": ent_list[2][:16] if len(ent_list) > 2 else "GLOBAL IMPACT", "desc": "SYSTEMIC REVELATION"}
    ]

    sentences_data = [
        {
            "id": 1,
            "text": f"Most people completely misunderstand the real story behind {topic_clean}.",
            "beats": [
                {
                    "id": "beat_01",
                    "type": "hero_hook",
                    "visual_prompt": f"Cinematic 35mm anamorphic film shot, dramatic volumetric lighting, {topic_clean} in high tension atmosphere, slow push-in zoom, 8k UHD",
                    "headline": "THE UNTOLD TRUTH",
                    "highlight": topic_clean.upper()[:24],
                    "camera_movement": "dolly_vertigo",
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_02",
                    "type": "treated_image",
                    "visual_prompt": f"Cinematic 35mm photograph of {topic_clean}, dramatic chiaroscuro lighting, 35mm film grain, orbital rotation",
                    "prompt": f"cinematic archival photograph of {topic_clean}, dramatic chiaroscuro lighting, 35mm film grain",
                    "grade": "hard_bw",
                    "camera_movement": "orbital",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 2,
            "text": f"When you trace the origins of {topic_clean} back to {date_1}, the verified numbers reveal a massive shift that caught everyone off guard.",
            "beats": [
                {
                    "id": "beat_03",
                    "type": "motion_card",
                    "template": "stat_counter",
                    "headline": f"RECORDED SCALE // {date_1}",
                    "highlight": metric_1[:24],
                    "duration": 1.3,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_04",
                    "type": "declassified_scan",
                    "headline": f"DEPOSITED RECORD // {date_1}",
                    "text": summary_text[:120].upper(),
                    "highlight": metric_1[:20],
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
                    "highlight": f"{ent_list[0][:10].upper()} * IMPACT * {date_1}",
                    "duration": 1.5,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_06",
                    "type": "broll_video",
                    "broll_query": f"{topic_clean} laboratory research",
                    "visual_prompt": f"retro laboratory workshop with inventors gathered around {topic_clean}, dramatic rim lighting",
                    "grade": "teal_split",
                    "camera_movement": "rack_focus_bokeh",
                    "duration": 1.6,
                    "sfx": "whoosh.wav"
                }
            ]
        },
        {
            "id": 4,
            "text": f"Declassified archives confirm the primary witness statement: \"{quote_text[:80]}\".",
            "beats": [
                {
                    "id": "beat_07",
                    "type": "motion_card",
                    "template": "quote_box",
                    "headline": "VERIFIED ARCHIVE",
                    "highlight": quote_text[:34].upper(),
                    "duration": 1.4,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_08",
                    "type": "evidence_board",
                    "headline": f"{topic_clean.upper()[:16]} TARGET NETWORK",
                    "nodes": evidence_nodes,
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 5,
            "text": f"What makes {topic_clean} so critical today is a geographical and geopolitical footprint spanning {loc_name}.",
            "beats": [
                {
                    "id": "beat_09",
                    "type": "map_flyover",
                    "location": loc_name,
                    "coords": coords,
                    "headline": f"COVERT LOCATION // {loc_name[:14]}",
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_10",
                    "type": "treated_image",
                    "visual_prompt": f"close-up detailed macro lens shot representing the essence of {topic_clean}, high contrast, 35mm Kodak grain",
                    "prompt": f"close-up detailed macro lens shot representing the essence of {topic_clean}, high contrast",
                    "grade": "amber",
                    "camera_movement": "dolly_vertigo",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 6,
            "text": f"Modern innovators are now using this exact formula to achieve results with {metric_2} velocity.",
            "beats": [
                {
                    "id": "beat_11",
                    "type": "motion_card",
                    "template": "stat_counter",
                    "headline": "EFFICIENCY METRIC",
                    "highlight": metric_2[:24],
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_12",
                    "type": "treated_image",
                    "visual_prompt": f"futuristic modern minimalist workspace focused on {topic_clean}, sleek aesthetic, dark mode, volumetric cyan glow",
                    "prompt": f"futuristic modern minimalist workspace focused on {topic_clean}, sleek aesthetic, dark mode",
                    "grade": "teal_split",
                    "camera_movement": "rack_focus_bokeh",
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
                    "visual_prompt": f"cinematic silhouette overlooking bustling modern city skyline, twilight volumetric fog, 35mm grain",
                    "prompt": f"cinematic silhouette overlooking bustling modern city skyline, twilight atmosphere",
                    "grade": "hard_bw",
                    "camera_movement": "orbital",
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
                    "visual_prompt": f"powerful inspiring portrait framing {topic_clean}, golden hour warm backlight, 85mm anamorphic flare",
                    "prompt": f"powerful inspiring portrait framing {topic_clean}, golden hour warm backlight",
                    "grade": "amber",
                    "camera_movement": "dolly_vertigo",
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
        "genre": genre_clean,
        "duration_target": duration_target,
        "sentences": sentences_data
    }


async def plan_documentary(
    topic: str,
    job_id: int,
    aspect_ratio: str = "9:16",
    duration_target: float = 45.0,
    fact_dossier: Optional[Dict[str, Any]] = None,
    genre: str = "auto"
) -> Dict[str, Any]:
    """
    Coordinates with brain.py to create the full documentary manifest across 5 genre archetypes:
    ("crime_doc", "comedy_skit", "action_hype", "movie_cinema", "viral_edu").
    Enforces distinct editing physics, camera movements, and color treatments for each genre.
    Prepends [HOUSE: HOUSE_2_SCREENWRITER_ARC | GENRE: <GENRE>] to prevent cross-genre confusion.
    """
    resolved_genre = detect_genre(topic) if (not genre or genre == "auto") else genre.lower()
    if resolved_genre not in GENRES:
        resolved_genre = "crime_doc"

    genre_rules = get_genre_rules(resolved_genre)
    namespace_header = f"[HOUSE: HOUSE_2_SCREENWRITER_ARC | GENRE: {resolved_genre.upper()}]"

    format_label = "16:9 horizontal YouTube documentary" if aspect_ratio == "16:9" else "9:16 vertical documentary short"
    logger.info(f"[Planner] Generating {format_label} ({duration_target}s) [{resolved_genre.upper()}] for: '{topic}' (Job #{job_id})")

    # 1. Fact Dossier Grounding Pre-Step (zero-key research)
    if not fact_dossier:
        try:
            fact_dossier = await research_fact_dossier(topic)
        except Exception as e:
            logger.warning(f"[Planner] Researcher pre-step error: {e}")
            fact_dossier = {}

    fact_context = ""
    if fact_dossier:
        metrics_str = ", ".join(fact_dossier.get("key_metrics", []))
        dates_str = ", ".join(fact_dossier.get("key_dates", []))
        entities_str = ", ".join(fact_dossier.get("key_entities", []))
        fact_context = (
            f"\n[VERIFIED FACT DOSSIER - GROUND ALL CARDS IN THIS DATA]:\n"
            f"• Canonical Title: {fact_dossier.get('canonical_title')}\n"
            f"• Description: {fact_dossier.get('description')}\n"
            f"• Real Metrics ($ & %): {metrics_str}\n"
            f"• Verified Dates: {dates_str}\n"
            f"• Key Suspects / Entities: {entities_str}\n"
            f"• Coordinates: {fact_dossier.get('coordinates', '38.8977° N, 77.0365° W')} ({fact_dossier.get('location_name', 'TARGET SECTOR')})\n"
            f"• Archival Record Quote: \"{fact_dossier.get('verified_quote', '')}\"\n"
            f"MANDATORY FACT INSTRUCTIONS:\n"
            f"1. Any 'stat_counter' beat MUST use one of the Real Metrics above.\n"
            f"2. Any 'map_flyover' beat MUST use the Coordinates and Location above.\n"
            f"3. Any 'evidence_board' beat MUST list the Key Entities above in 'nodes'.\n"
            f"4. Any 'quote_box' or 'declassified_scan' beat MUST feature the Archival Record Quote.\n"
        )

    # 2. Retrieve connected directing principles from Obsidian Second Brain & Harvester Dataset via BM25
    vault_context = query_director_vault(topic)

    # -------------------------------------------------------------
    # CASE A: LONG-FORM DOCUMENTARY (>60s) - 4 SEQUENTIAL ACTS
    # -------------------------------------------------------------
    if duration_target > 60:
        logger.info(f"[Planner] Activating 4-Act chapter generation for long-form [{resolved_genre.upper()}]: '{topic}'")
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
                    f"{namespace_header}\n"
                    f"Plan Act {act_num}: '{act_title}' for a long-form {format_label} on the topic: '{topic}'.\n"
                    f"{genre_rules}\n"
                    f"Write {count} consecutive spoken sentences. Each sentence must have 2 visual beats.\n"
                    f"{vault_context}\n"
                    f"{fact_context}\n"
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
                            b["genre"] = resolved_genre
                            global_beat_id += 1
                        all_sentences.append(s)
                        global_sent_id += 1

            if len(all_sentences) >= 12:
                all_beats = [b for s in all_sentences for b in s.get("beats", [])]
                hook_txt = all_sentences[0].get("text", "")
                log_script_to_vault(job_id, topic, hook_txt, f"{resolved_genre.title()} Documentary", all_beats)
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "style": "editor-v1",
                    "genre": resolved_genre,
                    "aspect_ratio": aspect_ratio,
                    "duration_target": duration_target,
                    "fact_dossier": fact_dossier,
                    "sentences": all_sentences
                }
        except Exception as e:
            logger.info(f"[Planner] Multi-act brain loop interrupted ({e}), using long-form fallback manifest")

    # -------------------------------------------------------------
    # CASE B: SHORT-FORM (<=60s) OR FALLBACK
    # -------------------------------------------------------------
    prompt = (
        f"{namespace_header}\n"
        f"Plan a {int(duration_target)}-second high-retention {format_label} on the topic: '{topic}'.\n"
        f"Target Genre: {resolved_genre.upper()}\n"
        f"{genre_rules}\n"
        f"{vault_context}\n"
        f"{fact_context}"
    )

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
                parsed["genre"] = resolved_genre
                parsed["aspect_ratio"] = aspect_ratio
                parsed["duration_target"] = duration_target
                parsed["fact_dossier"] = fact_dossier

                # Tag all beats with aspect_ratio & genre & run Reflexion Auto-Critic
                all_beats = []
                for s in parsed.get("sentences", []):
                    for b in s.get("beats", []):
                        b["aspect_ratio"] = aspect_ratio
                        b["genre"] = resolved_genre
                        all_beats.append(b)

                healed_beats, logged = audit_and_heal_beats(all_beats, topic)
                h_idx = 0
                for s in parsed.get("sentences", []):
                    num_b = len(s.get("beats", []))
                    s["beats"] = healed_beats[h_idx : h_idx + num_b]
                    h_idx += num_b
                parsed["beats"] = healed_beats

                hook_txt = parsed["sentences"][0].get("text", "")
                log_script_to_vault(job_id, topic, hook_txt, f"{resolved_genre.title()} Short", healed_beats)

                return parsed
    except Exception as e:
        logger.info(f"[Planner] Brain offline/unavailable ({e}). Engaging documentary generator.")

    # Generate reliable fallback manifest with fact dossier & genre physics
    manifest = generate_fallback_manifest(
        topic,
        job_id,
        duration_target=duration_target,
        fact_dossier=fact_dossier,
        genre=resolved_genre
    )
    manifest["aspect_ratio"] = aspect_ratio
    manifest["duration_target"] = duration_target
    manifest["fact_dossier"] = fact_dossier
    manifest["genre"] = resolved_genre

    # Tag all beats with aspect_ratio & genre & run Reflexion Auto-Critic
    fb_beats = []
    for s in manifest.get("sentences", []):
        for b in s.get("beats", []):
            b["aspect_ratio"] = aspect_ratio
            b["genre"] = resolved_genre
            fb_beats.append(b)

    healed_fb, logged_fb = audit_and_heal_beats(fb_beats, topic)
    h_idx = 0
    for s in manifest.get("sentences", []):
        num_b = len(s.get("beats", []))
        s["beats"] = healed_fb[h_idx : h_idx + num_b]
        h_idx += num_b
    manifest["beats"] = healed_fb

    hook_txt = manifest["sentences"][0].get("text", "") if manifest.get("sentences") else ""
    log_script_to_vault(job_id, topic, hook_txt, f"{resolved_genre.title()} Fallback", healed_fb)

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
