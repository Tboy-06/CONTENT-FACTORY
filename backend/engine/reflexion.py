"""
CONTENT-FACTORY Engine: Reflexion & Editorial Mistake Logger (reflexion.py)
----------------------------------------------------------------------------
Implements Verbal Reinforcement Learning (Reflexion) and continuous mistake logging
for autonomous documentary production (0 MB VRAM, 0 API cost).

Architecture:
1. Logs self-critic catches and human user corrections into D:\\CONTENT-FACTORY\\director_vault\\mistakes\\
   with occurrence counters and YAML frontmatter.
2. Appends instruction-tuning pairs to C:\\cf_training\\dataset.jsonl & C:\\cf_training\\reflexion_log.jsonl.
3. Provides deterministic `audit_and_heal_beats` to auto-correct pacing, typography, and retention errors.
4. Supplies top-ranked learned mistake rules for BM25 Vault-RAG injection into planner & copilot.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engine.reflexion")

VAULT_MISTAKES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "director_vault", "mistakes")
)
DATASET_FILE = r"C:\cf_training\dataset.jsonl"
REFLEXION_LOG_FILE = r"C:\cf_training\reflexion_log.jsonl"


def _slugify(text: str, max_words: int = 6) -> str:
    """Creates a clean filename slug from a rule or lesson string."""
    clean = re.sub(r"[^a-zA-Z0-9\s_-]", "", text.lower()).strip()
    words = clean.split()[:max_words]
    return "_".join(words) if words else "rule_unspecified"


def log_editorial_mistake(
    category: str,
    context_topic: str,
    bad_state: Any,
    fixed_state: Any,
    lesson_rule: str,
    occurrences: int = 1
) -> Dict[str, Any]:
    """
    Logs an editorial mistake caught by the Auto-Critic or human user edits.
    1. Updates or creates an interlinked Markdown rule in director_vault/mistakes/.
    2. Appends an instruction-tuning record to dataset.jsonl and reflexion_log.jsonl.
    """
    os.makedirs(VAULT_MISTAKES_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REFLEXION_LOG_FILE), exist_ok=True)

    slug = _slugify(lesson_rule)
    rule_filename = f"rule_{slug}.md"
    rule_filepath = os.path.join(VAULT_MISTAKES_DIR, rule_filename)

    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    total_occurrences = occurrences

    # If rule already exists, increment occurrences and retain initial creation date
    created_at = now_iso
    if os.path.exists(rule_filepath):
        try:
            with open(rule_filepath, "r", encoding="utf-8") as rf:
                content = rf.read()
            m_occ = re.search(r"occurrences:\s*(\d+)", content)
            if m_occ:
                total_occurrences = int(m_occ.group(1)) + occurrences
            m_created = re.search(r"created_at:\s*([^\n]+)", content)
            if m_created:
                created_at = m_created.group(1).strip()
        except Exception as e:
            logger.warning(f"[Reflexion] Error reading existing rule {rule_filename}: {e}")

    # Serialize bad and fixed states cleanly
    bad_str = json.dumps(bad_state, indent=2) if isinstance(bad_state, (dict, list)) else str(bad_state)
    fixed_str = json.dumps(fixed_state, indent=2) if isinstance(fixed_state, (dict, list)) else str(fixed_state)

    rule_md = f"""---
category: {category}
occurrences: {total_occurrences}
created_at: {created_at}
last_updated: {now_iso}
context_topic: {context_topic}
---
# Mistake Rule: {lesson_rule}

## Category & Frequency
- **Category:** `#{category}`
- **Occurrences Caught:** {total_occurrences}
- **Last Encountered Topic:** [[topics/{_slugify(context_topic)}|{context_topic}]]

## Bad Pattern (Mistake Caught)
```json
{bad_str}
```

## Corrected State (Optimal Heuristic)
```json
{fixed_str}
```

## Permanent Director Directive
> **Rule:** {lesson_rule}
"""

    try:
        with open(rule_filepath, "w", encoding="utf-8") as f:
            f.write(rule_md.strip() + "\n")
        logger.info(f"[Reflexion] Saved mistake rule to {rule_filepath} (occurrences={total_occurrences})")
    except Exception as e:
        logger.error(f"[Reflexion] Failed writing markdown rule: {e}")

    # Append to training datasets for offline and future LoRA fine-tuning
    tuning_record = {
        "timestamp": now_iso,
        "category": category,
        "occurrences": total_occurrences,
        "instruction": f"Avoid this editorial mistake: {lesson_rule}",
        "input": json.dumps({"topic": context_topic, "bad_state": bad_state}),
        "output": json.dumps({"lesson": lesson_rule, "healed_state": fixed_state}),
        "prompt": f"Act as an expert documentary short director. Fix this editorial mistake for topic '{context_topic}': {lesson_rule}",
        "response": json.dumps({"corrected": fixed_state, "rule": lesson_rule, "category": category})
    }

    # Append to reflexion_log.jsonl
    try:
        with open(REFLEXION_LOG_FILE, "a", encoding="utf-8") as rlf:
            rlf.write(json.dumps(tuning_record) + "\n")
    except Exception as e:
        logger.warning(f"[Reflexion] Could not append to reflexion_log.jsonl: {e}")

    # Append to main dataset.jsonl
    try:
        if os.path.exists(os.path.dirname(DATASET_FILE)):
            with open(DATASET_FILE, "a", encoding="utf-8") as dsf:
                dsf.write(json.dumps(tuning_record) + "\n")
    except Exception as e:
        logger.warning(f"[Reflexion] Could not append to dataset.jsonl: {e}")

    return {
        "rule_file": rule_filename,
        "category": category,
        "occurrences": total_occurrences,
        "lesson": lesson_rule,
        "context_topic": context_topic
    }


def get_learned_mistakes(query_topic: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scans director_vault/mistakes/ and retrieves top learned mistake rules.
    Sorts by occurrence frequency and relevance to `query_topic`.
    """
    if not os.path.exists(VAULT_MISTAKES_DIR):
        return []

    rules: List[Dict[str, Any]] = []
    q_words = set(re.findall(r"\b\w{3,}\b", query_topic.lower())) if query_topic else set()

    for fn in os.listdir(VAULT_MISTAKES_DIR):
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(VAULT_MISTAKES_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            category = "editorial"
            m_cat = re.search(r"category:\s*([^\n]+)", content)
            if m_cat:
                category = m_cat.group(1).strip()

            occurrences = 1
            m_occ = re.search(r"occurrences:\s*(\d+)", content)
            if m_occ:
                occurrences = int(m_occ.group(1))

            m_rule = re.search(r"# Mistake Rule:\s*([^\n]+)", content)
            lesson = m_rule.group(1).strip() if m_rule else fn.replace("rule_", "").replace(".md", "").replace("_", " ")

            m_topic = re.search(r"context_topic:\s*([^\n]+)", content)
            topic = m_topic.group(1).strip() if m_topic else ""

            # Score relevance based on occurrences + query overlap
            relevance_score = float(occurrences) * 2.0
            if q_words:
                content_words = set(re.findall(r"\b\w{3,}\b", content.lower()))
                overlap = len(q_words.intersection(content_words))
                relevance_score += overlap * 5.0

            rules.append({
                "file": fn,
                "category": category,
                "occurrences": occurrences,
                "lesson": lesson,
                "context_topic": topic,
                "score": relevance_score
            })
        except Exception as e:
            logger.debug(f"[Reflexion] Error parsing mistake file {fn}: {e}")

    rules.sort(key=lambda r: r["score"], reverse=True)
    return rules[:limit]


def audit_and_heal_beats(
    beats: List[Dict[str, Any]],
    topic: str = "Documentary"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Automated Self-Critic & Healing Hook:
    Audits beat sequence for objective editorial mistakes and auto-corrects them in-place:
    1. Consecutive identical beat types / templates (Pacing Monotony) -> Auto-diversify.
    2. Headline / Highlight text overflow (Typography Clipping) -> Auto-trim punchy text.
    3. Sluggish durations (> 4.0s) without camera movement -> Auto-inject 3D camera shader.
    Logs each caught failure pattern to director_vault/mistakes/ and dataset.jsonl.
    """
    if not beats:
        return beats, []

    healed_beats: List[Dict[str, Any]] = [dict(b) for b in beats]
    logged_mistakes: List[Dict[str, Any]] = []

    # Alternative templates for motion cards when duplicate is caught
    card_template_rotation = ["stat_counter", "quote_box", "3_item_list", "workflow_stepper", "red_slam_word", "star_badge"]

    for i in range(len(healed_beats)):
        beat = healed_beats[i]

        # -------------------------------------------------------------
        # Rule 1: Pacing Monotony (Consecutive Identical Types/Templates)
        # -------------------------------------------------------------
        if i > 0:
            prev_beat = healed_beats[i - 1]
            prev_type = prev_beat.get("type", "")
            curr_type = beat.get("type", "")
            prev_tmpl = prev_beat.get("template", "")
            curr_tmpl = beat.get("template", "")

            # Check consecutive motion cards with identical template
            if curr_type == "motion_card" and prev_type == "motion_card" and curr_tmpl == prev_tmpl:
                bad_state = {"beat_index": i, "prev_template": prev_tmpl, "curr_template": curr_tmpl}
                # Pick different template
                new_tmpl = next((t for t in card_template_rotation if t != curr_tmpl), "stat_counter")
                beat["template"] = new_tmpl
                fixed_state = {"beat_index": i, "prev_template": prev_tmpl, "new_template": new_tmpl}
                
                lesson = f"Avoid consecutive identical motion card templates ('{curr_tmpl}'); rotate to '{new_tmpl}' to maintain visual velocity."
                logged = log_editorial_mistake("pacing_monotony", topic, bad_state, fixed_state, lesson)
                logged_mistakes.append(logged)

            # Check 3 consecutive identical types (e.g. 3 treated_images in a row)
            elif i >= 2 and curr_type == prev_type and prev_type == healed_beats[i - 2].get("type", ""):
                bad_state = {"beat_index": i, "repeated_type": curr_type, "count": 3}
                # Diversify by converting the 3rd beat to an evidence board or declassified scan
                new_type = "declassified_scan" if curr_type == "treated_image" else "treated_image"
                beat["type"] = new_type
                if new_type == "declassified_scan" and not beat.get("text"):
                    beat["text"] = beat.get("headline", topic.upper())
                fixed_state = {"beat_index": i, "diversified_to": new_type}

                lesson = f"Never allow 3 consecutive beats of type '{curr_type}'; alternate with '{new_type}' to prevent viewer drop-off."
                logged = log_editorial_mistake("pacing_monotony", topic, bad_state, fixed_state, lesson)
                logged_mistakes.append(logged)

        # -------------------------------------------------------------
        # Rule 2: Typography Overflow (9:16 Canvas Clipping)
        # -------------------------------------------------------------
        headline = beat.get("headline", "")
        if headline and len(headline) > 28:
            bad_state = {"beat_id": beat.get("id"), "headline": headline, "length": len(headline)}
            # Auto-trim to 26 chars at word boundary
            words = headline.split()
            trimmed = ""
            for w in words:
                if len(f"{trimmed} {w}".strip()) <= 26:
                    trimmed = f"{trimmed} {w}".strip()
                else:
                    break
            if not trimmed:
                trimmed = headline[:25].strip()
            beat["headline"] = trimmed.upper()
            fixed_state = {"beat_id": beat.get("id"), "healed_headline": beat["headline"], "length": len(beat["headline"])}

            lesson = "Headline text on 9:16 cards must not exceed 28 characters to avoid layout edge clipping."
            logged = log_editorial_mistake("typography_overflow", topic, bad_state, fixed_state, lesson)
            logged_mistakes.append(logged)

        highlight = beat.get("highlight", "")
        if highlight and len(highlight) > 35:
            bad_state = {"beat_id": beat.get("id"), "highlight": highlight, "length": len(highlight)}
            words = highlight.split()
            trimmed = ""
            for w in words:
                if len(f"{trimmed} {w}".strip()) <= 32:
                    trimmed = f"{trimmed} {w}".strip()
                else:
                    break
            if not trimmed:
                trimmed = highlight[:30].strip()
            beat["highlight"] = trimmed
            fixed_state = {"beat_id": beat.get("id"), "healed_highlight": beat["highlight"], "length": len(beat["highlight"])}

            lesson = "Card highlight badges must not exceed 35 characters to fit high-contrast pill geometry."
            logged = log_editorial_mistake("typography_overflow", topic, bad_state, fixed_state, lesson)
            logged_mistakes.append(logged)

        # -------------------------------------------------------------
        # Rule 3: Sluggish Retention (Durations > 4.0s without 3D camera move)
        # -------------------------------------------------------------
        dur = float(beat.get("duration", 1.5))
        b_type = beat.get("type", "")
        camera_move = beat.get("camera_movement")

        if dur > 4.0 and b_type in ("treated_image", "hero_hook", "ai_video") and not camera_move:
            bad_state = {"beat_id": beat.get("id"), "duration": dur, "camera_movement": None}
            # Inject dynamic 3D camera motion
            beat["camera_movement"] = "orbital"
            fixed_state = {"beat_id": beat.get("id"), "duration": dur, "camera_movement": "orbital"}

            lesson = "Visual shots exceeding 4.0s must include active 3D camera movements (orbital/dolly) to sustain attention."
            logged = log_editorial_mistake("sluggish_retention", topic, bad_state, fixed_state, lesson)
            logged_mistakes.append(logged)

    return healed_beats, logged_mistakes


def log_system_fallback(
    service_name: str,
    context_topic: str,
    failed_params: Dict[str, Any],
    fallback_used: str,
    error_message: str
) -> Dict[str, Any]:
    """
    Logs an automated fallback event (e.g. ZeroGPU timeout -> Pollinations Flux)
    so future scripts optimize prompts and avoid repeatedly triggering timeouts.
    """
    lesson = f"Service '{service_name}' failed with '{error_message[:60]}'. Use fallback '{fallback_used}' or simplify parameters."
    return log_editorial_mistake(
        category="system_fallback",
        context_topic=context_topic,
        bad_state={"service": service_name, "params": failed_params, "error": error_message[:120]},
        fixed_state={"fallback": fallback_used},
        lesson_rule=lesson
    )
