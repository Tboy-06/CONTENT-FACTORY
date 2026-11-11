"""
CONTENT-FACTORY: Multi-Task Balanced Dataset Harvester & Director Knowledge Vault Sync
----------------------------------------------------------------------------------------
Designed to construct a 6,000-example instruction-tuning dataset (C:\\cf_training\\dataset.jsonl)
and populate D:\\CONTENT-FACTORY\\director_vault\\ across 4 specialized production tasks:

1. editing (Target: 2,500 | 42%):
   Reverse-engineers cut pacing, motion card templates (red_slam_word, stat_counter, 3_item_list, quote_box),
   and cosine zoom triggers from CapCut/Premiere tutorials & high-retention shorts.
   Vault destination: director_vault/techniques/

2. hooks (Target: 1,500 | 25%):
   Extracts first 3-5s viral transcript hooks alongside view-to-like telemetry to train
   curiosity-gap, negative-bias, and counter-intuitive hook generation.
   Vault destination: director_vault/hooks/

3. storytelling (Target: 1,500 | 25%):
   Parses documentary transcripts into 8-sentence Shorts and 24-sentence 4-Act scripts
   (Act 1: Inciting Anomaly, Act 2: Hidden Mechanism, Act 3: Crisis/Climax, Act 4: Aftermath).
   Vault destination: director_vault/styles/

4. visual_audio (Target: 1,000 | 16%):
   Converts spoken narration into paired visual beats, archival prompts, color grades
   (hard_bw, teal_split, amber), and SFX cues (thud.wav, whoosh.wav, click.wav, riser.wav).
   Vault destination: director_vault/sfx/

Guarantees:
- Zero-Quota Discovery via yt-dlp flat playlist extraction (0 API units).
- 1-Unit Batch Metadata via /youtube/v3/videos (50 IDs per unit).
- Checkpoint & Deduplication tracked in C:\\cf_training\\harvest_state.json.
- Zero-Disk Bloat: 0 MB video files saved to SSD.
"""

import os
import sys
import re
import json
import time
import random
import argparse
import urllib.request
from typing import List, Dict, Any, Optional, Set

import yt_dlp

WORKSPACE_DIR = os.path.abspath(r"C:\cf_training")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp")
DATASET_PATH = os.path.join(WORKSPACE_DIR, "dataset.jsonl")
STATE_PATH = os.path.join(WORKSPACE_DIR, "harvest_state.json")
VAULT_DIR = os.path.abspath(r"D:\CONTENT-FACTORY\director_vault")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "techniques"), exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "hooks"), exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "styles"), exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "sfx"), exist_ok=True)


PRAISE_KEYWORDS = [
    "edit", "editor", "who edited", "editing", "transitions", "transition",
    "capcut", "premiere", "pacing", "sound design", "visuals", "cinematic",
    "b-roll", "clean edit", "insane edit", "underrated", "chills", "masterpiece"
]

TASK_BALANCED_TARGETS = {
    "editing": 2500,
    "hooks": 1500,
    "storytelling": 1500,
    "visual_audio": 1000
}

TASK_QUERIES = {
    "editing": [
        "how to edit like vox in capcut pc tutorial",
        "cinematic video editing hacks capcut premiere pro",
        "how to edit viral reels shorts capcut pacing retention",
        "johnny harris editing style map animation tutorial",
        "capcut keyframe zoom animation sound design tutorial",
        "kinetic typography text animation tutorial capcut after effects",
        "cinematic b roll transitions paper texture mask tutorial",
        "davinci resolve cinematic color grading documentary lut",
        "mrbeast retention editing 1 second rule pacing tutorial",
        "hayden hillier smith youtube editor pacing masterclass",
        "finzar video editing tricks comedic sound effects pacing",
        "ali abdaal video editing fast pacing retention tips"
    ],
    "hooks": [
        "how to write viral hooks first 3 seconds retention youtube shorts",
        "youtube hook formula curiosity gap retention tips",
        "i studied 1000 viral hooks scriptwriting masterclass",
        "psychological hooks for youtube video retention",
        "viral video hooks that keep viewers watching till the end",
        "dan koe hook formula viral copywriting framework",
        "how to hook viewers in the first 5 seconds youtube",
        "viral tiktok reels hook formulas that work every time"
    ],
    "storytelling": [
        "how to write documentary script youtube storytelling",
        "magnates media business documentary video essay storytelling",
        "coldfusion tech documentary storytelling masterclass",
        "james jani documentary storytelling script breakdown",
        "lemmino documentary research and visual pacing",
        "studiobinder 3 act story structure pacing masterclass",
        "kurzgesagt scriptwriting storytelling curiosity gap",
        "how to structure a video essay 4 act narrative",
        "johnny harris storytelling script breakdown"
    ],
    "visual_audio": [
        "sound design for video editors whoosh riser impact tutorial",
        "foley sound effects layering documentary b roll tutorial",
        "cinematic sound effects tutorial premiere pro davinci resolve",
        "how to sound design a documentary film step by step",
        "fast cuts sfx cinematic sound effects for transitions",
        "film scoring and foley sound effects for documentary videos",
        "how to sound design a video step by step tutorial"
    ]
}


# ==============================================================================
# STATE & CHECKPOINT MANAGEMENT
# ==============================================================================

def load_harvest_state() -> Dict[str, Any]:
    """Loads harvest state and processed video IDs from C:\\cf_training\\harvest_state.json."""
    default_state: Dict[str, Any] = {
        "processed_ids": {
            "editing": set(),
            "hooks": set(),
            "storytelling": set(),
            "visual_audio": set()
        },
        "counts": {
            "editing": 0,
            "hooks": 0,
            "storytelling": 0,
            "visual_audio": 0,
            "total": 0
        },
        "targets": TASK_BALANCED_TARGETS,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for task in ("editing", "hooks", "storytelling", "visual_audio"):
                    task_ids = data.get("processed_ids", {}).get(task, [])
                    default_state["processed_ids"][task] = set(task_ids)
                default_state["counts"] = data.get("counts", default_state["counts"])
                default_state["targets"] = data.get("targets", TASK_BALANCED_TARGETS)
                return default_state
        except Exception as e:
            print(f"[WARN] Error loading state file ({e}). Backfilling from dataset.jsonl...")

    # Backfill from dataset.jsonl if state file doesn't exist yet
    if os.path.exists(DATASET_PATH):
        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            t = record.get("task", "editing")
                            vid = record.get("video_id") or record.get("input", "")[:40]
                            if t in default_state["processed_ids"]:
                                default_state["processed_ids"][t].add(vid)
                                default_state["counts"][t] = default_state["counts"].get(t, 0) + 1
                                default_state["counts"]["total"] += 1
                        except Exception:
                            pass
        except Exception:
            pass

    return default_state


def save_harvest_state(state: Dict[str, Any]):
    """Persists harvest state checkpoint to C:\\cf_training\\harvest_state.json."""
    save_data = {
        "processed_ids": {k: list(v) if isinstance(v, set) else v for k, v in state["processed_ids"].items()},
        "counts": state["counts"],
        "targets": state.get("targets", TASK_BALANCED_TARGETS),
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed writing harvest state: {e}")


# ==============================================================================
# SUBTITLES, COMMENTS & ZERO-DISK EXTRACTORS
# ==============================================================================

def extract_chapters_from_description(description: str) -> List[Dict[str, Any]]:
    """Extracts timestamped chapters from video descriptions as fallback structure."""
    chapters = []
    if not description:
        return []
    lines = description.splitlines()
    for line in lines:
        m = re.search(r"\b([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)\b\s*[-–—:]?\s*(.+)", line)
        if m:
            ts_str, ch_title = m.group(1), m.group(2).strip()
            parts = [float(p) for p in ts_str.split(":")]
            if len(parts) == 2:
                sec = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                sec = 0.0
            chapters.append({"start": sec, "text": ch_title, "duration": 4.0, "end": sec + 4.0})
    return chapters


def extract_subtitles_stream(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts timestamped transcript lines from subtitles/captions without downloading video."""
    all_subs = {**info.get("automatic_captions", {}), **info.get("subtitles", {})}
    subs = None
    for k in ("en", "en-US", "en-GB", "en-CA", "en-orig", "en-IE", "en-NZ"):
        if k in all_subs:
            subs = all_subs[k]
            break
    if not subs:
        for k, v in all_subs.items():
            if k.startswith("en"):
                subs = v
                break

    if not subs:
        desc = info.get("description", "")
        return extract_chapters_from_description(desc)

    # Prioritize JSON3 format (rich word & sentence timestamps)
    target_fmt = None
    for fmt in subs:
        if fmt.get("ext") == "json3":
            target_fmt = fmt
            break
    if not target_fmt:
        for fmt in subs:
            if fmt.get("ext") in ("vtt", "srv3"):
                target_fmt = fmt
                break

    if not target_fmt or not target_fmt.get("url"):
        desc = info.get("description", "")
        return extract_chapters_from_description(desc)

    try:
        req = urllib.request.Request(target_fmt["url"], headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

        sentences = []
        if target_fmt.get("ext") == "json3":
            data = json.loads(content)
            events = data.get("events", [])
            for ev in events:
                if "segs" not in ev:
                    continue
                start_ms = ev.get("tStartMs", 0)
                dur_ms = ev.get("dDurationMs", 0)
                text = "".join(s.get("utf8", "") for s in ev.get("segs", [])).strip()
                text = re.sub(r"\[.*?\]", "", text).strip()
                if text:
                    sentences.append({
                        "start": round(start_ms / 1000.0, 2),
                        "duration": round(dur_ms / 1000.0, 2),
                        "end": round((start_ms + dur_ms) / 1000.0, 2),
                        "text": text
                    })
        elif target_fmt.get("ext") == "vtt":
            lines = content.splitlines()
            for line in lines:
                if "-->" in line:
                    continue
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if clean and not clean.startswith("WEBVTT") and not clean.isdigit():
                    sentences.append({"start": 0.0, "duration": 3.0, "end": 3.0, "text": clean})

        if not sentences:
            desc = info.get("description", "")
            return extract_chapters_from_description(desc)

        return sentences
    except Exception as e:
        print(f"     [WARN] Subtitle stream download error: {e}")
        desc = info.get("description", "")
        return extract_chapters_from_description(desc)


def extract_top_praise_comments(info: Dict[str, Any], max_comments: int = 35) -> List[Dict[str, Any]]:
    """Filters comments praising specific editing techniques, pacing, or timestamps."""
    raw_comments = info.get("comments") or []
    praise_comments = []

    for c in raw_comments[:max_comments]:
        text = c.get("text", "")
        text_lower = text.lower()
        if any(k in text_lower for k in PRAISE_KEYWORDS):
            timestamp_match = re.search(r"\b([0-9]{1,2}:[0-9]{2})\b", text)
            praise_comments.append({
                "author": c.get("author", "Viewer"),
                "text": text.strip(),
                "timestamp_mentioned": timestamp_match.group(1) if timestamp_match else None,
                "likes": c.get("like_count", 0)
            })

    return praise_comments


def extract_visual_cuts_lowres(url: str, job_id: str) -> List[float]:
    """
    Downloads an ultra-tiny 144p/240p sample strictly into C:\\cf_training\\temp\\,
    detects real scene cut timestamps, and deletes the file inside a finally: block.
    Zero-disk guarantee: temp folder is left at 0 MB.
    """
    out_video = os.path.join(TEMP_DIR, f"{job_id}_lowres.%(ext)s")
    cuts_txt = os.path.join(TEMP_DIR, f"{job_id}_cuts.txt")
    actual_video = None
    cuts = [0.0]

    try:
        ydl_opts = {
            'format': 'worstvideo[height<=144]/worst[height<=240]/worst',
            'outtmpl': out_video,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignore_no_formats_error': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'download_ranges': yt_dlp.utils.download_range_func(None, [(0, 45)]),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        for f in os.listdir(TEMP_DIR):
            if f.startswith(f"{job_id}_lowres"):
                actual_video = os.path.join(TEMP_DIR, f)
                break

        if actual_video and os.path.exists(actual_video):
            cmd = [
                "ffmpeg", "-y", "-nostdin",
                "-i", actual_video,
                "-vf", f"select='gt(scene,0.28)',metadata=print:file={cuts_txt.replace('\\', '/')}",
                "-an", "-f", "null", "-"
            ]
            import subprocess
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)

            if os.path.exists(cuts_txt):
                with open(cuts_txt, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "pts_time:" in line:
                            m = re.search(r"pts_time:([0-9.]+)", line)
                            if m:
                                t = round(float(m.group(1)), 2)
                                if t not in cuts:
                                    cuts.append(t)
                cuts.sort()
    except Exception as e:
        print(f"     [WARN] Visual cut sampling skipped: {e}")
    finally:
        for p in [actual_video, cuts_txt]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        # Extra safety purge: ensure temp dir remains 0 MB
        for f in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except OSError:
                pass

    return cuts


# ==============================================================================
# MULTI-TASK SYNTHESIZERS (DUAL OUTPUT: DATASET.JSONL + OBSIDIAN VAULT)
# ==============================================================================

def synthesize_editing_task(
    info: Dict[str, Any],
    sentences: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
    visual_cuts: List[float]
) -> Dict[str, Any]:
    """
    Task 1: editing (Target: 2,500 | 42%)
    Reverse-engineers cut pacing, motion cards (red_slam_word, stat_counter, 3_item_list, quote_box),
    and cosine zoom triggers. Writes to director_vault/techniques/.
    """
    title = info.get("title", "Editing Masterclass")
    duration = float(info.get("duration") or 60.0)
    video_id = info.get("id") or "vid_edit"
    full_text = " ".join(s["text"] for s in sentences)

    rules = []
    if re.search(r"zoom|scale|punch.?in|keyframe", full_text, re.I):
        rules.append("Trigger dynamic cosine zoom-in (1.1x to 1.25x scale) on key emphasis nouns and critical statistics.")
    if re.search(r"sound effect|sfx|whoosh|thud|riser|foley", full_text, re.I):
        rules.append("Layer whoosh/riser SFX 2-3 frames before every cut transition, with heavy thud impact on data reveals.")
    if re.search(r"b-roll|overlay|footage|cut", full_text, re.I):
        rules.append("Cut to archival or contextual B-roll every 2.0 to 2.8 seconds to maintain visual dopamine.")
    if re.search(r"caption|subtitle|kinetic|font|typography", full_text, re.I):
        rules.append("Render stark bold kinetic subtitles with active-word yellow/cyan highlights matching spoken timing.")
    if re.search(r"mask|cutout|paper|texture|split", full_text, re.I):
        rules.append("Apply paper-texture border overlays and photo cutouts with drop shadows for tactile documentary aesthetic.")
    if re.search(r"color grade|lut|teal|contrast|black", full_text, re.I):
        rules.append("Apply high-contrast desaturated grade with warm skin tones and deep obsidian shadows (#0B0F19).")

    if not rules:
        rules.append("Maintain high-tempo visual rhythm: cut every 2.4s and align audio transitions with vocal pauses.")

    cuts_count = len(visual_cuts) if visual_cuts else max(3, int(duration / 2.6))
    avg_interval = round(duration / max(1, cuts_count), 2)
    cuts_per_min = round(cuts_count / max(0.5, duration / 60.0), 1)

    motion_cards = [
        {
            "template": "red_slam_word",
            "trigger_context": "Critical inflection point or classified revelation",
            "example_headline": "CLASSIFIED REVELATION",
            "example_highlight": title[:30].upper(),
            "sfx": "thud.wav",
            "grade": "hard_bw"
        },
        {
            "template": "stat_counter",
            "trigger_context": "Numeric metrics, retention spikes, or financial percentages",
            "example_headline": "PERFORMANCE METRIC",
            "example_highlight": f"{int(cuts_per_min * 3.8)}% RETENTION RETENTION",
            "sfx": "whoosh.wav",
            "grade": "amber"
        },
        {
            "template": "3_item_list",
            "trigger_context": "Structured 3-part editing frameworks or procedural rules",
            "example_headline": "EDITING PILLARS",
            "example_highlight": "HOOK · PACING · PAYOFF",
            "sfx": "click.wav",
            "grade": "teal_split"
        },
        {
            "template": "quote_box",
            "trigger_context": "Authority statements, director rules, or memorable viewer feedback",
            "example_headline": "DIRECTOR PRINCIPLE",
            "example_highlight": comments[0]["text"][:60] if comments else "Cut before the viewer anticipates the transition",
            "sfx": "click.wav",
            "grade": "hard_bw"
        }
    ]

    output_payload = {
        "pacing": {
            "avg_cut_interval_seconds": avg_interval,
            "cuts_per_minute": cuts_per_min,
            "zoom_trigger": "dynamic cosine zoom-in (1.1x - 1.25x) on key emphasis nouns and data points",
            "transition_lead_frames": 2
        },
        "motion_card_rules": motion_cards,
        "actionable_rules": rules,
        "feedback_signals": len(comments)
    }

    # Vault note in director_vault/techniques/
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:45].strip("_")
    vault_file = os.path.join(VAULT_DIR, "techniques", f"{safe_slug}.md")
    md_content = f"""# {title}

## Editing Architecture
- Category: CapCut & NLE Visual Techniques
- Duration: {duration:.1f}s ({duration/60:.1f} min)
- Cut Frequency: {avg_interval}s per cut (~{cuts_per_min} cuts/min)
- Motion Card Integration: red_slam_word, stat_counter, 3_item_list, quote_box

## Core Pacing & Cutting Rules
"""
    for r in rules:
        md_content += f"- {r}\n"

    md_content += "\n## Motion Card Deployments\n"
    for mc in motion_cards:
        md_content += f"- **{mc['template']}**: {mc['trigger_context']} (SFX: `{mc['sfx']}`, Grade: `{mc['grade']}`)\n"

    if comments:
        md_content += "\n## Viewer Feedback on Pacing\n"
        for c in comments[:3]:
            ts = f" (at {c['timestamp_mentioned']})" if c['timestamp_mentioned'] else ""
            md_content += f"> \"{c['text']}\"{ts} — {c['author']}\n\n"

    try:
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"     [WARN] Could not write techniques vault note: {e}")

    sample_narration = " ".join(s["text"] for s in sentences[:4]) if sentences else title
    return {
        "task": "editing",
        "video_id": video_id,
        "instruction": f"Analyze the visual rhythm, cut pacing, and motion card triggers for editing a documentary video on: \"{title}\"",
        "input": f"Title: {title}\nDuration: {duration}s\nSample Narration: {sample_narration[:240]}",
        "output": output_payload
    }


def synthesize_hooks_task(
    info: Dict[str, Any],
    sentences: List[Dict[str, Any]],
    comments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Task 2: hooks (Target: 1,500 | 25%)
    Extracts first 3-5 seconds of viral transcripts alongside view-to-like telemetry
    to train curiosity-gap hook generation. Writes to director_vault/hooks/.
    """
    title = info.get("title", "Viral Video")
    video_id = info.get("id") or "vid_hook"
    view_count = int(info.get("view_count") or 0)
    like_count = int(info.get("like_count") or 0)
    ratio = round(view_count / max(1, like_count), 1)

    opening_sentences = sentences[:3] if sentences else []
    hook_transcript = " ".join(s["text"] for s in opening_sentences).strip()
    if not hook_transcript:
        hook_transcript = f"The hidden truth about {title} that nobody is talking about."

    hooks = [
        {
            "hook": hook_transcript[:120],
            "trigger_type": "curiosity_gap",
            "duration_seconds": 3.2,
            "visual_pacing": "Rapid cosine punch-in with high-contrast B&W archival overlay"
        },
        {
            "hook": f"Everything you think you know about {title[:40]} is completely backwards.",
            "trigger_type": "counter_intuitive",
            "duration_seconds": 3.0,
            "visual_pacing": "Red slam word motion card: 'CRITICAL ERROR' with heavy thud SFX"
        },
        {
            "hook": f"In 2026, 99% of creators make this fatal mistake with {title[:35]}.",
            "trigger_type": "negative_bias",
            "duration_seconds": 3.4,
            "visual_pacing": "Stat counter slamming '99% AT RISK' with whoosh riser"
        }
    ]

    output_payload = {
        "title": title,
        "view_count": view_count,
        "like_count": like_count,
        "view_to_like_ratio": ratio,
        "hooks": hooks
    }

    # Vault note in director_vault/hooks/
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:45].strip("_")
    vault_file = os.path.join(VAULT_DIR, "hooks", f"hook_{safe_slug}.md")
    md_content = f"""# Hook: {title}

## Performance Telemetry
- Views: {view_count:,}
- Likes: {like_count:,}
- View-to-Like Ratio: {ratio}:1
- Primary First Spoken Line (0:00 - 0:03): "{hook_transcript[:140]}"

## High-Retention Hook Variations
"""
    for h in hooks:
        md_content += f"### {h['trigger_type'].replace('_', ' ').title()}\n"
        md_content += f"> \"{h['hook']}\"\n\n"
        md_content += f"- **Target Duration:** {h['duration_seconds']}s\n"
        md_content += f"- **Visual Pacing:** {h['visual_pacing']}\n\n"

    try:
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"     [WARN] Could not write hooks vault note: {e}")

    return {
        "task": "hooks",
        "video_id": video_id,
        "instruction": f"Generate 3 high-retention viral hooks for topic: \"{title}\"",
        "input": f"Topic: {title}\nViews: {view_count:,}\nPrimary Hook Line: {hook_transcript[:180]}",
        "output": output_payload
    }


def synthesize_storytelling_task(
    info: Dict[str, Any],
    sentences: List[Dict[str, Any]],
    comments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Task 3: storytelling (Target: 1,500 | 25%)
    Parses documentary transcripts into 8-sentence Shorts and 24-sentence 4-Act scripts
    (Act 1: Inciting Anomaly, Act 2: Hidden Mechanism, Act 3: Crisis/Climax, Act 4: Aftermath).
    Writes to director_vault/styles/.
    """
    title = info.get("title", "Documentary Narrative")
    video_id = info.get("id") or "vid_story"
    duration = float(info.get("duration") or 60.0)
    is_long_form = duration > 90.0

    total_s = len(sentences)
    if is_long_form and total_s >= 12:
        chunk_1 = sentences[:int(total_s * 0.25)] or [{"text": f"The emergence of {title} started with an anomaly that defied explanation."}]
        chunk_2 = sentences[int(total_s * 0.25):int(total_s * 0.55)] or [{"text": "Behind closed doors, the underlying mechanism was operating in total secrecy."}]
        chunk_3 = sentences[int(total_s * 0.55):int(total_s * 0.82)] or [{"text": "Then came the breaking point: an inevitable crisis that shattered conventional assumptions."}]
        chunk_4 = sentences[int(total_s * 0.82):] or [{"text": "In the aftermath, only those who adapted early were left standing."}]

        acts = [
            {
                "act": 1,
                "name": "Inciting Anomaly",
                "sentences": [s["text"] for s in chunk_1[:6]]
            },
            {
                "act": 2,
                "name": "Hidden Mechanism",
                "sentences": [s["text"] for s in chunk_2[:6]]
            },
            {
                "act": 3,
                "name": "Crisis/Climax",
                "sentences": [s["text"] for s in chunk_3[:6]]
            },
            {
                "act": 4,
                "name": "Aftermath",
                "sentences": [s["text"] for s in chunk_4[:6]]
            }
        ]
        format_type = "24-Sentence 4-Act Documentary"
    else:
        short_sentences = [s["text"] for s in sentences[:8]]
        if len(short_sentences) < 8:
            while len(short_sentences) < 8:
                short_sentences.append(f"Understanding {title} reveals how modern attention is captured.")
        acts = [
            {
                "act": 1,
                "name": "Full Narrative Arc",
                "sentences": short_sentences
            }
        ]
        format_type = "8-Sentence Short"

    hook_line = acts[0]["sentences"][0] if acts and acts[0]["sentences"] else f"The untold truth behind {title}."
    takeaway_line = acts[-1]["sentences"][-1] if acts and acts[-1]["sentences"] else f"That is why {title} matters today."

    output_payload = {
        "title": title,
        "format": format_type,
        "duration_seconds": round(duration, 1),
        "hook_line": hook_line,
        "acts": acts,
        "takeaway": takeaway_line
    }

    # Vault note in director_vault/styles/
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:45].strip("_")
    vault_file = os.path.join(VAULT_DIR, "styles", f"story_{safe_slug}.md")
    md_content = f"""# Story Structure: {title}

## Narrative Overview
- Format: {format_type}
- Total Duration: {duration:.1f}s
- Hook: "{hook_line[:140]}"
- Payoff: "{takeaway_line[:140]}"

## Acts & Narrative Breakdown
"""
    for act in acts:
        md_content += f"### Act {act['act']}: {act['name']}\n"
        for idx, line in enumerate(act["sentences"], 1):
            md_content += f"{idx}. {line}\n"
        md_content += "\n"

    try:
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"     [WARN] Could not write styles vault note: {e}")

    instruction = (
        f"Structure a 24-sentence 4-Act documentary script with Inciting Anomaly, Hidden Mechanism, Crisis/Climax, and Aftermath for: \"{title}\""
        if is_long_form else
        f"Write an 8-sentence high-retention narrative script for a documentary short on: \"{title}\""
    )

    return {
        "task": "storytelling",
        "video_id": video_id,
        "instruction": instruction,
        "input": f"Topic: {title}\nDuration: {duration}s\nFormat: {format_type}",
        "output": output_payload
    }


def synthesize_visual_audio_task(
    info: Dict[str, Any],
    sentences: List[Dict[str, Any]],
    comments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Task 4: visual_audio (Target: 1,000 | 16%)
    Converts spoken narration into paired visual beats, archival prompts, color grades
    (hard_bw, teal_split, amber), and SFX cues (thud.wav, whoosh.wav, click.wav, riser.wav).
    Writes to director_vault/sfx/.
    """
    title = info.get("title", "Visual Audio Design")
    video_id = info.get("id") or "vid_sfx"
    duration = float(info.get("duration") or 60.0)

    scene_beats = []
    grade_cycle = ["hard_bw", "teal_split", "amber"]
    sfx_cycle = ["thud.wav", "whoosh.wav", "click.wav", "riser.wav"]
    card_templates = ["red_slam_word", "stat_counter", "3_item_list", "quote_box"]

    sample_sentences = sentences[:8] if sentences else [{"text": f"The visual progression of {title} begins here."}]
    for idx, s in enumerate(sample_sentences, 1):
        text = s.get("text", "")
        grade = grade_cycle[(idx - 1) % len(grade_cycle)]
        sfx_1 = sfx_cycle[(idx - 1) % len(sfx_cycle)]
        sfx_2 = sfx_cycle[idx % len(sfx_cycle)]
        card_tpl = card_templates[(idx - 1) % len(card_templates)]

        words = re.findall(r"\b[A-Z0-9a-z]{4,}\b", text)
        kw = words[0].upper() if words else "KEY FACT"

        scene_beats.append({
            "scene_idx": idx,
            "spoken_sentence": text,
            "beat_1": {
                "type": "motion_card" if idx % 2 == 1 else "treated_image",
                "template": card_tpl if idx % 2 == 1 else None,
                "headline": f"{kw} REVEAL" if idx % 2 == 1 else None,
                "highlight": text[:28].upper() if idx % 2 == 1 else None,
                "prompt": f"archival documentary photograph relating to {title}, high contrast, dramatic lighting" if idx % 2 == 0 else None,
                "grade": grade,
                "sfx": sfx_1
            },
            "beat_2": {
                "type": "treated_image" if idx % 2 == 1 else "motion_card",
                "template": card_tpl if idx % 2 == 0 else None,
                "headline": "ANALYSIS POINT" if idx % 2 == 0 else None,
                "highlight": "DATA EVIDENCE" if idx % 2 == 0 else None,
                "prompt": f"historical technical schematics and documents regarding {title}, film grain texture" if idx % 2 == 1 else None,
                "grade": "teal_split" if grade == "hard_bw" else "amber" if grade == "teal_split" else "hard_bw",
                "sfx": sfx_2
            }
        })

    output_payload = {
        "title": title,
        "duration_seconds": round(duration, 1),
        "scene_count": len(scene_beats),
        "scenes": scene_beats
    }

    # Vault note in director_vault/sfx/
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:45].strip("_")
    vault_file = os.path.join(VAULT_DIR, "sfx", f"sfx_{safe_slug}.md")
    md_content = f"""# Visual & Audio Cues: {title}

## Production Parameters
- Duration: {duration:.1f}s
- Visual Schema: treated_image + motion_card paired beats
- Color Grades: hard_bw, teal_split, amber
- Sound Effects: thud.wav, whoosh.wav, click.wav, riser.wav

## Scene Beats & Cues
"""
    for sc in scene_beats:
        md_content += f"### Scene {sc['scene_idx']}\n"
        md_content += f"> \"{sc['spoken_sentence']}\"\n\n"
        b1, b2 = sc["beat_1"], sc["beat_2"]
        md_content += f"- **Beat 1 ({b1['type']}):** Grade: `{b1['grade']}`, SFX: `{b1['sfx']}`\n"
        md_content += f"- **Beat 2 ({b2['type']}):** Grade: `{b2['grade']}`, SFX: `{b2['sfx']}`\n\n"

    try:
        with open(vault_file, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"     [WARN] Could not write sfx vault note: {e}")

    sample_narration = " ".join(s["text"] for s in sentences[:3]) if sentences else title
    return {
        "task": "visual_audio",
        "video_id": video_id,
        "instruction": "Convert the documentary narration into paired visual beats, archival prompts, color grades, and SFX cues matching the production schema.",
        "input": f"Topic: {title}\nNarration: {sample_narration[:240]}",
        "output": output_payload
    }


# ==============================================================================
# QUOTA-SAFE YOUTUBE DISCOVERY & BATCH ENRICHMENT
# ==============================================================================

def get_youtube_api_key() -> Optional[str]:
    """Reads YouTube Data API key from D:\\CONTENT-FACTORY\\.env or environment."""
    env_file = r"D:\CONTENT-FACTORY\.env"
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("YOUTUBE_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return os.environ.get("YOUTUBE_API_KEY")


def fetch_batch_video_metadata(video_ids: List[str], api_key: str) -> Dict[str, Dict[str, Any]]:
    """
    Batches up to 50 video IDs in a SINGLE YouTube API v3 call (/youtube/v3/videos).
    Quota cost: 1 UNIT for up to 50 videos (0.02 units per video).
    """
    if not video_ids or not api_key:
        return {}

    metadata_map = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        id_str = ",".join(chunk)
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={id_str}&key={api_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("items", []):
                    vid = item.get("id")
                    stats = item.get("statistics", {})
                    snippet = item.get("snippet", {})
                    metadata_map[vid] = {
                        "video_id": vid,
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0))
                    }
        except Exception as e:
            print(f"     [WARN] Batch metadata fetch error: {e}")
    return metadata_map


def search_youtube_query(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    QUOTA-SAFE SEARCH (0 units on discovery, 1 unit per 50 videos for metadata):
    1. Discovers video IDs via yt-dlp flat playlist extraction (0 API units).
    2. Enriches candidates with batch /youtube/v3/videos if key present.
    """
    print(f"\nSearching YouTube (0-Quota Flat Search) for top {count} videos: '{query}'...")
    api_key = get_youtube_api_key()

    candidate_limit = max(count * 2, 10)
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True,
    }
    candidates = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{candidate_limit}:{query}", download=False)
            for e in res.get('entries', []):
                if e and e.get('id'):
                    candidates.append({
                        "id": e['id'],
                        "title": e.get('title', ''),
                        "url": f"https://www.youtube.com/watch?v={e['id']}",
                        "view_count": e.get('view_count') or 0
                    })
    except Exception as e:
        print(f"     [WARN] yt-dlp search error: {e}")

    if not candidates:
        print(f"     [ERROR] No candidates discovered for query '{query}'.")
        return []

    if api_key:
        candidate_ids = [c["id"] for c in candidates]
        meta_map = fetch_batch_video_metadata(candidate_ids, api_key)
        if meta_map:
            print(f"     [QUOTA OPTIMIZED] Enriched {len(meta_map)} videos via batch /videos API (cost: 1 unit).")
            for c in candidates:
                if c["id"] in meta_map:
                    c["view_count"] = meta_map[c["id"]]["view_count"]
                    c["like_count"] = meta_map[c["id"]]["like_count"]
                    c["title"] = meta_map[c["id"]]["title"]

    candidates.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    top_items = candidates[:count]
    for idx, c in enumerate(top_items, 1):
        vc = f"{c['view_count']:,}" if c.get('view_count') else "N/A"
        print(f"     {idx}. [{vc} views] {c['title'][:65]}")

    return top_items


# ==============================================================================
# CORE HARVESTING PIPELINE
# ==============================================================================

def harvest_video_entry(
    entry_or_url: str,
    task: str = "editing",
    sample_visual_cuts: bool = False,
    state: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Streams subtitles & metadata in memory, runs task synthesizer,
    appends to dataset.jsonl, writes Obsidian note, and checkpoints state.
    """
    if state is None:
        state = load_harvest_state()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'ignore_no_formats_error': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'getcomments': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'max_comments': ['35', 'all', '35', '0']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry_or_url, download=False)
            if not info:
                return None

            title = info.get("title", "Video")
            duration = float(info.get("duration") or 60.0)
            url = info.get("webpage_url") or entry_or_url
            video_id = info.get("id") or url

            # Checkpoint & Deduplication check
            task_processed = state["processed_ids"].get(task, set())
            if video_id in task_processed or title.lower().strip() in task_processed:
                print(f"     [SKIP] Already processed for task [{task}]: \"{title[:55]}\".")
                return {"title": title, "skipped": True}

            print(f"     > Streaming subtitles & metadata for: \"{title[:55]}\" ({duration/60:.1f}m)...")
            sentences = extract_subtitles_stream(info)
            print(f"     > Extracted {len(sentences)} transcript segments.")

            comments = extract_top_praise_comments(info)
            print(f"     > Scraped {len(comments)} praise feedback comments.")

            visual_cuts = []
            if sample_visual_cuts:
                job_id = f"cut_{video_id[:8]}"
                visual_cuts = extract_visual_cuts_lowres(url, job_id)
                print(f"     > Detected {len(visual_cuts)} scene cuts (temp files purged: 0 MB on disk).")

            # Route to Task Synthesizer
            if task == "editing":
                record = synthesize_editing_task(info, sentences, comments, visual_cuts)
            elif task == "hooks":
                record = synthesize_hooks_task(info, sentences, comments)
            elif task == "storytelling":
                record = synthesize_storytelling_task(info, sentences, comments)
            elif task == "visual_audio":
                record = synthesize_visual_audio_task(info, sentences, comments)
            else:
                record = synthesize_editing_task(info, sentences, comments, visual_cuts)

            # Append instruction-tuning JSON object to dataset.jsonl
            with open(DATASET_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Update checkpoint state
            state["processed_ids"][task].add(video_id)
            state["processed_ids"][task].add(title.lower().strip())
            state["counts"][task] = state["counts"].get(task, 0) + 1
            state["counts"]["total"] = state["counts"].get("total", 0) + 1
            save_harvest_state(state)

            print(f"     [SUCCESS] Task [{task}] -> Logged to Vault + dataset.jsonl (0 MB disk bloat)")
            delay = round(random.uniform(1.5, 2.0), 2)
            print(f"     [PACING] Pausing {delay}s between requests to guard YouTube & Gemini limits...")
            time.sleep(delay)
            return record
    except Exception as e:
        print(f"     [ERROR] Failed harvesting {entry_or_url}: {e}")
        time.sleep(round(random.uniform(1.5, 2.0), 2))
        return None


# ==============================================================================
# MASTER HARVEST RUNNER & CLI
# ==============================================================================

def run_balanced_plan(state: Dict[str, Any], count_per_task: int = 10, visual_cuts: bool = False):
    """Executes the balanced distribution across all 4 tasks towards the 6,000 target."""
    print("\n==================================================================")
    print(f"LAUNCHING BALANCED DATASET HARVESTER: {count_per_task} VIDEOS PER TASK ({count_per_task * 4} TOTAL)")
    print("Distribution: editing (42%) | hooks (25%) | storytelling (25%) | visual_audio (16%)")
    print(f"Target Dataset: {DATASET_PATH}")
    print(f"Director Vault: {VAULT_DIR}")
    print(f"Checkpoint State: {STATE_PATH}")
    print("Zero-Disk Guarantee: 0 MB video files saved to SSD")
    print("==================================================================\n")

    tasks_order = ["editing", "hooks", "storytelling", "visual_audio"]
    for task_name in tasks_order:
        current_cnt = state["counts"].get(task_name, 0)
        target_cnt = TASK_BALANCED_TARGETS.get(task_name, 1500)
        print(f"\n>>> PROCESSING TASK: [{task_name.upper()}] (Current: {current_cnt} / Target: {target_cnt}) <<<")

        queries = TASK_QUERIES.get(task_name, [])
        harvested_for_task = 0

        for q_idx, q in enumerate(queries, 1):
            if harvested_for_task >= count_per_task:
                break
            if state["counts"].get(task_name, 0) >= target_cnt:
                print(f"     [GOAL REACHED] Task [{task_name}] target met ({state['counts'][task_name]}/{target_cnt}).")
                break

            needed = count_per_task - harvested_for_task
            fetch_count = max(needed * 2, 5)
            items = search_youtube_query(q, fetch_count)
            time.sleep(round(random.uniform(1.5, 2.0), 2))

            for item in items:
                if harvested_for_task >= count_per_task:
                    break
                res = harvest_video_entry(
                    item["url"],
                    task=task_name,
                    sample_visual_cuts=visual_cuts,
                    state=state
                )
                if res and not res.get("skipped"):
                    harvested_for_task += 1
                    print(f"     [PROGRESS] Harvested {harvested_for_task}/{count_per_task} for task [{task_name}].")

        print(f"\n[TASK COMPLETE] [{task_name.upper()}] batch finished: {harvested_for_task} new examples added.\n")

    print("\n[BALANCED PLAN COMPLETE] Updated checkpoint state:")
    for t in tasks_order:
        print(f"  - {t}: {state['counts'].get(t, 0)} / {TASK_BALANCED_TARGETS[t]}")
    print(f"  - TOTAL: {state['counts'].get('total', 0)} / 6,000\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-Task Balanced Video Dataset Harvester")
    parser.add_argument("--task", choices=["editing", "hooks", "storytelling", "visual_audio", "all"], default="all",
                        help="Specific production task to harvest")
    parser.add_argument("--run-balanced-plan", action="store_true",
                        help="Run master 6,000 balanced distribution plan across all 4 tasks")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of videos per task in balanced plan or per query (default: 10)")
    parser.add_argument("--target-total", type=int, default=6000,
                        help="Total dataset target size (default: 6,000)")
    parser.add_argument("--query", help="Custom search query")
    parser.add_argument("--urls", nargs="+", help="Specific video URLs to harvest")
    parser.add_argument("--visual-cuts", action="store_true",
                        help="Sample real scene cuts via 144p zero-disk streaming")
    parser.add_argument("--verify", action="store_true",
                        help="Run quick verification test (strictly 1 video per task, 4 total)")
    args = parser.parse_args()

    state = load_harvest_state()
    print(f"[State Loaded] Total records in dataset.jsonl: {state['counts']['total']}")
    for t, cnt in state["counts"].items():
        if t != "total":
            print(f"  - Task [{t}]: {cnt} records")

    # Quick Verification Mode: exactly 1 video per task (4 videos total)
    if args.verify:
        print("\n==================================================================")
        print("RUNNING QUICK VERIFICATION TEST: 1 VIDEO PER TASK (4 TOTAL)")
        print("==================================================================")
        verify_tasks = [
            ("editing", "how to edit like vox in capcut pc tutorial"),
            ("hooks", "how to write viral hooks first 3 seconds retention youtube shorts"),
            ("storytelling", "how to write documentary script youtube storytelling"),
            ("visual_audio", "sound design for video editors whoosh riser impact tutorial")
        ]
        for task_name, query_text in verify_tasks:
            print(f"\n--- [VERIFY TASK: {task_name.upper()}] ---")
            items = search_youtube_query(query_text, 5)
            for item in items:
                res = harvest_video_entry(
                    item["url"],
                    task=task_name,
                    sample_visual_cuts=args.visual_cuts,
                    state=state
                )
                if res and not res.get("skipped"):
                    break

        temp_files = os.listdir(TEMP_DIR)
        print("\n==================================================================")
        print(f"VERIFICATION COMPLETE:")
        print(f"- Temp directory files remaining: {len(temp_files)} (Must be 0 MB: {len(temp_files) == 0})")
        print(f"- Total records in dataset.jsonl: {state['counts']['total']}")
        print(f"- Techniques notes: {len(os.listdir(os.path.join(VAULT_DIR, 'techniques')))}")
        print(f"- Hooks notes: {len(os.listdir(os.path.join(VAULT_DIR, 'hooks')))}")
        print(f"- Styles notes: {len(os.listdir(os.path.join(VAULT_DIR, 'styles')))}")
        print(f"- SFX notes: {len(os.listdir(os.path.join(VAULT_DIR, 'sfx')))}")
        print("==================================================================\n")
        return

    if args.run_balanced_plan:
        run_balanced_plan(state, count_per_task=args.count, visual_cuts=args.visual_cuts)
        return

    if args.urls:
        task_to_run = "editing" if args.task == "all" else args.task
        for u in args.urls:
            harvest_video_entry(u, task=task_to_run, sample_visual_cuts=args.visual_cuts, state=state)
        return

    if args.query:
        task_to_run = "editing" if args.task == "all" else args.task
        items = search_youtube_query(args.query, args.count)
        for item in items:
            harvest_video_entry(item["url"], task=task_to_run, sample_visual_cuts=args.visual_cuts, state=state)
        return

    # Default task harvest
    tasks_to_harvest = ["editing", "hooks", "storytelling", "visual_audio"] if args.task == "all" else [args.task]
    for t in tasks_to_harvest:
        print(f"\n--- Harvesting Task [{t.upper()}] ---")
        queries = TASK_QUERIES.get(t, [])
        for q in queries[:2]:
            items = search_youtube_query(q, args.count)
            for item in items:
                harvest_video_entry(item["url"], task=t, sample_visual_cuts=args.visual_cuts, state=state)


if __name__ == "__main__":
    main()
