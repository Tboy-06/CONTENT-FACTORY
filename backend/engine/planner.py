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
from backend.engine.vault_graph import (
    query_director_vault,
    log_script_to_vault,
    detect_genre,
    format_topic_title,
)
from backend.engine.researcher import research_fact_dossier
from backend.engine.reflexion import audit_and_heal_beats

logger = logging.getLogger("engine.planner")

GENRES = ["auto", "crime_doc", "comedy_skit", "action_hype", "movie_cinema", "viral_edu"]


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
    topic_clean = format_topic_title(topic)

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

    # Pull real-world facts from dossier ONLY if verified (never fabricate numbers or coordinates)
    facts = fact_dossier or {}
    raw_metrics = [m for m in (facts.get("key_metrics") or []) if m and m != "UNVERIFIED"]
    raw_dates = [d for d in (facts.get("key_dates") or []) if d and d != "UNVERIFIED"]
    metric_1 = raw_metrics[0].upper() if raw_metrics else "UNVERIFIED METRIC"
    metric_2 = raw_metrics[-1].upper() if raw_metrics else "UNVERIFIED SCALE"
    date_1 = raw_dates[0] if raw_dates else "UNVERIFIED DATE"
    raw_coords = facts.get("coordinates")
    coords = raw_coords if (raw_coords and raw_coords != "UNVERIFIED") else "UNVERIFIED"
    raw_loc = facts.get("location_name")
    loc_name = raw_loc if (raw_loc and raw_loc != "UNVERIFIED") else topic_clean[:18].upper()
    raw_quote = facts.get("verified_quote")
    quote_text = raw_quote if (raw_quote and raw_quote != "UNVERIFIED") else "UNVERIFIED ARCHIVAL RECORD"
    summary_text = facts.get("summary") or f"UNVERIFIED DRAFT DOSSIER REGARDING {topic_clean.upper()}."

    # Build entity nodes for evidence_board without fake agency names
    ent_list = [e for e in (facts.get("key_entities") or []) if e] or [topic_clean[:16]]
    evidence_nodes = [
        {"title": ent_list[0][:16], "desc": "PRIMARY SUBJECT"},
        {"title": ent_list[1][:16] if len(ent_list) > 1 else "UNVERIFIED NODE", "desc": "SECONDARY RECORD"},
        {"title": ent_list[2][:16] if len(ent_list) > 2 else "ARCHIVE ENTRY", "desc": "PENDING REVIEW"}
    ]

    date_phrase = f"documented in {date_1}" if date_1 != "UNVERIFIED DATE" else "documented in historical records"
    metric_phrase = f"recorded at {metric_2}" if metric_2 != "UNVERIFIED SCALE" else "undergoing structural evaluation"
    quote_spoken = (
        f"Archival records note the primary statement: \"{quote_text[:80]}\"."
        if quote_text != "UNVERIFIED ARCHIVAL RECORD"
        else f"Archival records regarding {topic_clean} require primary source verification."
    )

    sentences_data = [
        {
            "id": 1,
            "text": f"The documented history behind {topic_clean} reveals a critical investigative timeline.",
            "beats": [
                {
                    "id": "beat_01",
                    "type": "hero_hook",
                    "visual_prompt": f"Cinematic 35mm anamorphic film shot, dramatic volumetric lighting, {topic_clean} in high tension atmosphere, slow push-in zoom, 8k UHD",
                    "headline": "INVESTIGATIVE BRIEF",
                    "highlight": topic_clean.upper()[:24],
                    "camera_movement": hero_cam,
                    "duration": 1.4,
                    "sfx": impact_sfx
                },
                {
                    "id": "beat_02",
                    "type": "treated_image",
                    "visual_prompt": f"Cinematic 35mm photograph of {topic_clean}, dramatic chiaroscuro lighting, 35mm film grain, orbital rotation",
                    "prompt": f"cinematic archival photograph of {topic_clean}, dramatic chiaroscuro lighting, 35mm film grain",
                    "grade": default_grade,
                    "camera_movement": "orbital",
                    "duration": 1.6,
                    "sfx": whoosh_sfx
                }
            ]
        },
        {
            "id": 2,
            "text": f"When you examine the origins of {topic_clean} {date_phrase}, the primary evidence highlights a major structural shift.",
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
            "text": f"Key developments surrounding {topic_clean} shaped how investigators and analysts track the subject today.",
            "beats": [
                {
                    "id": "beat_05",
                    "type": "motion_card",
                    "template": "3_item_list",
                    "headline": "KEY FACTORS",
                    "highlight": f"{ent_list[0][:10].upper()} * ARCHIVE * {date_1}",
                    "duration": 1.5,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_06",
                    "type": "broll_video",
                    "broll_query": f"{topic_clean} documentary archive",
                    "visual_prompt": f"archival research workspace examining {topic_clean}, dramatic rim lighting",
                    "grade": "teal_split",
                    "camera_movement": "rack_focus_bokeh",
                    "duration": 1.6,
                    "sfx": "whoosh.wav"
                }
            ]
        },
        {
            "id": 4,
            "text": quote_spoken,
            "beats": [
                {
                    "id": "beat_07",
                    "type": "motion_card",
                    "template": "quote_box",
                    "headline": "ARCHIVE RECORD",
                    "highlight": quote_text[:34].upper(),
                    "duration": 1.4,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_08",
                    "type": "evidence_board",
                    "headline": f"{topic_clean.upper()[:16]} SUBJECT MAP",
                    "nodes": evidence_nodes,
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 5,
            "text": f"The operational context of {topic_clean} centers on {loc_name}.",
            "beats": [
                {
                    "id": "beat_09",
                    "type": "map_flyover",
                    "location": loc_name,
                    "coords": coords,
                    "headline": f"SECTOR // {loc_name[:14]}",
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_10",
                    "type": "treated_image",
                    "visual_prompt": f"close-up detailed macro lens shot representing {topic_clean}, high contrast, 35mm Kodak grain",
                    "prompt": f"close-up detailed macro lens shot representing {topic_clean}, high contrast",
                    "grade": "amber",
                    "camera_movement": "dolly_vertigo",
                    "duration": 1.6,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 6,
            "text": f"Current assessments show {topic_clean} {metric_phrase} across documented case studies.",
            "beats": [
                {
                    "id": "beat_11",
                    "type": "motion_card",
                    "template": "stat_counter",
                    "headline": "DOCUMENTED STATUS",
                    "highlight": metric_2[:24],
                    "duration": 1.4,
                    "sfx": "thud.wav"
                },
                {
                    "id": "beat_12",
                    "type": "treated_image",
                    "visual_prompt": f"modern investigative desk focused on {topic_clean}, dark mode, natural tungsten key light",
                    "prompt": f"modern investigative desk focused on {topic_clean}, dark mode",
                    "grade": "teal_split",
                    "camera_movement": "rack_focus_bokeh",
                    "duration": 1.5,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 7,
            "text": f"Tracking how {topic_clean} develops provides essential context for what comes next.",
            "beats": [
                {
                    "id": "beat_13",
                    "type": "motion_card",
                    "template": "quote_box",
                    "headline": "KEY OBSERVATION",
                    "highlight": "EVIDENCE UNDER REVIEW",
                    "duration": 1.5,
                    "sfx": "whoosh.wav"
                },
                {
                    "id": "beat_14",
                    "type": "treated_image",
                    "visual_prompt": f"cinematic silhouette overlooking modern city skyline, twilight volumetric fog, 35mm grain",
                    "prompt": f"cinematic silhouette overlooking modern city skyline, twilight atmosphere",
                    "grade": "hard_bw",
                    "camera_movement": "orbital",
                    "duration": 1.5,
                    "sfx": "click.wav"
                }
            ]
        },
        {
            "id": 8,
            "text": f"Every verified detail around {topic_clean} reshapes the broader picture.",
            "beats": [
                {
                    "id": "beat_15",
                    "type": "motion_card",
                    "template": "red_slam_word",
                    "headline": "FINAL SUMMARY",
                    "highlight": topic_clean.upper()[:22],
                    "duration": 1.4,
                    "sfx": "riser.wav"
                },
                {
                    "id": "beat_16",
                    "type": "treated_image",
                    "visual_prompt": f"dramatic documentary frame representing {topic_clean}, warm backlight, 85mm anamorphic lens",
                    "prompt": f"dramatic documentary frame representing {topic_clean}, warm backlight",
                    "grade": "amber",
                    "camera_movement": "dolly_vertigo",
                    "duration": 1.8,
                    "sfx": "thud.wav"
                }
            ]
        }
    ]

    # If long-form (3m+ or 5m+), expand narrative with Acts 2, 3, and 4 without fake percentages
    if duration_target > 60:
        extra_acts = [
            (9, f"Phase two examined the core framework of {topic_clean} from primary records.", "stat_counter", "STRUCTURAL REVIEW", metric_1[:22], "blueprints and archival drafts", "amber"),
            (10, f"Analysts cross-checked each sequence to verify the timeline.", "treated_image", None, None, f"analysts reviewing {topic_clean} archival records", "hard_bw"),
            (11, f"A closer inspection revealed an overlooked detail in the conventional account.", "motion_card", "KEY FINDING", "ARCHIVE COMPARISON", None, "teal_split"),
            (12, f"Subsequent evaluations documented the findings for further scrutiny.", "stat_counter", "EVALUATION STATUS", metric_2[:22], None, "amber"),
            (13, f"Observers worked to trace how {topic_clean} progressed across each stage.", "3_item_list", "CORE FACTORS", "ORIGIN · TIMELINE · IMPACT", None, "teal_split"),
            (14, f"By the time the full record surfaced, the implications were clear.", "treated_image", None, None, f"archival vault symbolizing history of {topic_clean}", "hard_bw"),
            (15, f"Then came the pivotal turning point that tested {topic_clean}.", "red_slam_word", "THE TURNING POINT", "CRITICAL INFLECTION", None, "amber"),
            (16, f"Under heightened scrutiny, earlier assumptions had to be revised.", "treated_image", None, None, f"dramatic industrial landscape representing {topic_clean}", "teal_split"),
            (17, f"The documented record of {topic_clean} remained central to the investigation.", "stat_counter", "RECORD STATUS", "UNVERIFIED DRAFT", None, "amber"),
            (18, f"This sequence demonstrated how the broader narrative evolved.", "quote_box", "FIELD REPORT", "TIMELINE UPDATED", None, "hard_bw"),
            (19, f"Institutions and researchers continued to catalog the aftermath.", "treated_image", None, None, f"global archival map documenting {topic_clean}", "teal_split"),
            (20, f"The primary takeaway surrounding {topic_clean} continues to inform current analysis.", "motion_card", "FINAL VERDICT", "CASE REVIEWED", None, "amber"),
            (21, f"Looking forward, the questions raised by {topic_clean} remain active.", "3_item_list", "CORE LESSONS", "VERIFY · DOCUMENT · ANALYZE", None, "hard_bw"),
            (22, f"Careful examination of primary sources is essential before drawing conclusions.", "stat_counter", "SOURCE STATUS", "PRIMARY VERIFICATION", None, "teal_split"),
            (23, f"New evidence around {topic_clean} continues to be indexed and reviewed.", "treated_image", None, None, f"cinematic horizon illumination representing {topic_clean}", "amber"),
            (24, f"Review and edit this draft manifest before final documentary publication.", "red_slam_word", "DRAFT REVIEW", "VERIFICATION REQUIRED", None, "amber"),
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
        "unverified_draft": True,
        "verification_status": "UNVERIFIED_DRAFT",
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
        metrics_str = ", ".join(fact_dossier.get("key_metrics", [])) or "UNVERIFIED (do not invent numbers)"
        dates_str = ", ".join(fact_dossier.get("key_dates", [])) or "UNVERIFIED (do not invent years)"
        entities_str = ", ".join(fact_dossier.get("key_entities", [])) or format_topic_title(topic)
        coords_val = fact_dossier.get("coordinates") or "UNVERIFIED"
        loc_val = fact_dossier.get("location_name") or "UNVERIFIED"
        quote_val = fact_dossier.get("verified_quote") or "UNVERIFIED"
        fact_context = (
            f"\n[FACT DOSSIER - STATUS: {fact_dossier.get('verification_status', 'UNVERIFIED')}]:\n"
            f"• Canonical Title: {fact_dossier.get('canonical_title')}\n"
            f"• Description: {fact_dossier.get('description')}\n"
            f"• Verified Metrics ($ & %): {metrics_str}\n"
            f"• Verified Dates: {dates_str}\n"
            f"• Key Entities: {entities_str}\n"
            f"• Coordinates: {coords_val} ({loc_val})\n"
            f"• Archival Record Quote: \"{quote_val}\"\n"
            f"STRICT FACTUAL INTEGRITY RULES:\n"
            f"1. NEVER fabricate fake statistics, dollar figures, coordinates, or years.\n"
            f"2. Only use 'stat_counter' with specific numbers if Verified Metrics are provided above.\n"
            f"3. Only use 'map_flyover' with specific coordinates if Coordinates above are not UNVERIFIED.\n"
            f"4. Any 'evidence_board' beat MUST list the Key Entities above in 'nodes'.\n"
        )

    # 2. Retrieve connected 5-House directing principles from Obsidian Second Brain & Harvester Dataset via BM25
    vault_context = query_director_vault(topic, genre=resolved_genre, house="ALL")

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
                healed_beats, _ = audit_and_heal_beats(all_beats, topic)
                h_idx = 0
                for s in all_sentences:
                    num_b = len(s.get("beats", []))
                    s["beats"] = healed_beats[h_idx : h_idx + num_b]
                    h_idx += num_b
                hook_txt = all_sentences[0].get("text", "")
                log_script_to_vault(job_id, topic, hook_txt, f"{resolved_genre.title()} Documentary", healed_beats)
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "style": "editor-v1",
                    "genre": resolved_genre,
                    "aspect_ratio": aspect_ratio,
                    "duration_target": duration_target,
                    "fact_dossier": fact_dossier,
                    "sentences": all_sentences,
                    "beats": healed_beats
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
