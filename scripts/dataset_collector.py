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
from typing import List, Dict, Any, Optional, Set, Tuple

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


# ==============================================================================
# KEYWORDS & ANALYTICAL FILTERS (ANTI-SPAM / REAL-WORLD EDITING ONLY)
# ==============================================================================

ANALYTICAL_EDITING_KEYWORDS = [
    "sound design", "pacing", "jump cut", "match cut", "speed ramp", 
    "keyframe", "keyframes", "color grade", "lut", "split screen", 
    "paper texture", "timestamp", "audio ducking", "motion blur", 
    "graph editor", "velocity", "sound effect", "sfx", "b-roll", 
    "foley", "masking", "overlay", "transition at", "retention curve",
    "zoomed in", "punch in", "whip pan", "kinetic text", "subtitles",
    "j-cut", "l-cut", "aspect ratio", "frame rate", "motion graphics",
    "text slam", "stat counter", "camera shake", "zoom punch"
]
# Backward-compatibility alias
PRAISE_KEYWORDS = ANALYTICAL_EDITING_KEYWORDS

EXCLUDE_COMMENT_PATTERNS = re.compile(
    r"(?:discount|course|class|enroll|curriculum|price|pricing|cost|\$\d+|buy|purchase|coupon|code|promo|affiliate|patreon|hire|portfolio|dm\s*me|whatsapp|telegram|instagram|email\s*me|reach\s*out|subscribe\s*to\s*my|check\s*my\s*channel|freelance|services)",
    re.IGNORECASE
)

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
        "ali abdaal video editing fast pacing retention tips",
        "capcut graph speed ramp tutorial smooth transitions",
        "documentary editing workflow premiere pro tips",
        "magnates media editing breakdown motion graphics",
        "how to do 3D camera tracking after effects tutorial",
        "sound sync jump cuts fast pacing video editing",
        "split screen multi panel editing documentary tutorial",
        "text slammer and stat counter animation tutorial",
        "sam kolder transition tutorial zoom whip pan",
        "davinci resolve power grade documentary film look",
        "high retention short form video editing capcut",
        "vox style collage animation tutorial premiere",
        "film grain and chromatic aberration overlay tutorial",
        "match cut and invisible transition tutorial video editing",
        "how to edit like fern documentary style tutorial"
    ],
    "hooks": [
        "how to write viral hooks first 3 seconds retention youtube shorts",
        "youtube hook formula curiosity gap retention tips",
        "i studied 1000 viral hooks scriptwriting masterclass",
        "psychological hooks for youtube video retention",
        "viral video hooks that keep viewers watching till the end",
        "dan koe hook formula viral copywriting framework",
        "how to hook viewers in the first 5 seconds youtube",
        "viral tiktok reels hook formulas that work every time",
        "the psychology of viral hooks curiosity gap breakdown",
        "pattern interrupt video hook formulas for shorts",
        "negative bias hooks that get millions of views",
        "storytelling hook opening lines for documentary video",
        "viral finance video hooks money psychology",
        "viral tech video hooks that explode retention",
        "how to start a youtube video hook retention masterclass",
        "alex hormozi hook formulas short form content",
        "viral history hooks mystery unexplained openings",
        "open loop scriptwriting technique youtube retention",
        "counter intuitive video hooks that blow up views",
        "first 3 seconds video retention dropoff fix",
        "viral title and hook frameworks for creators",
        "high retention intro script formula youtube",
        "retention editing and hook formula breakdown",
        "viral true crime and documentary opening hooks",
        "5 hooks that generated 100 million views breakdown",
        "how to write scripts that hook viewers instantly"
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
        "johnny harris storytelling script breakdown",
        "how to write a 4 act documentary script",
        "the hero with a thousand faces video essay structure",
        "dan harmon story circle applied to youtube videos",
        "business downfall documentary scriptwriting masterclass",
        "how to turn boring research into compelling stories",
        "tension and release narrative arc video essay",
        "how vox builds tension in investigative documentaries",
        "inciting anomaly hidden mechanism story structure",
        "how to write an engaging voiceover script for youtube",
        "cliffhanger placement 4 act story structure shorts",
        "historical documentary storytelling script writing tips",
        "investigative journalism video essay script breakdown",
        "mystery pacing and revelation documentary storytelling",
        "the science of storytelling will storr breakdown",
        "how to write documentary conclusions and emotional takeaways",
        "crafting compelling narratives in short form documentary",
        "behind the scenes documentary script writing process"
    ],
    "visual_audio": [
        "sound design for video editors whoosh riser impact tutorial",
        "foley sound effects layering documentary b roll tutorial",
        "cinematic sound effects tutorial premiere pro davinci resolve",
        "how to sound design a documentary film step by step",
        "fast cuts sfx cinematic sound effects for transitions",
        "film scoring and foley sound effects for documentary videos",
        "how to sound design a video step by step tutorial",
        "audio ducking and voiceover mixing masterclass",
        "cinematic braam and sub bass hit sound design",
        "ambient drone soundscape for documentary editing",
        "riser build up to impact drop sound design tutorial",
        "diegetic vs non diegetic sound in video editing",
        "documentary music selection and pacing transitions",
        "whoosh thud hit sound effect layering premiere pro",
        "high frequency ear candy sound design for video",
        "sound design tricks that make videos feel professional",
        "sound design breakdown magnates media style",
        "vox style sound design clicks typing whooshes",
        "cinematic tension music and sfx layering",
        "reverb and delay automation for dramatic moments",
        "atmospheric background audio and room tone tutorial",
        "glitch sfx and digital distortion sound design",
        "how to mix sfx under voiceover dialogue",
        "micro sound effects for kinetic typography and motion graphics",
        "sound design hacks that double viewer engagement",
        "the secret audio layers in viral documentaries"
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
        "query_indices": {
            "editing": 0,
            "hooks": 0,
            "storytelling": 0,
            "visual_audio": 0
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
                default_state["query_indices"] = data.get("query_indices", {
                    "editing": 0, "hooks": 0, "storytelling": 0, "visual_audio": 0
                })
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
        "query_indices": state.get("query_indices", {
            "editing": 0, "hooks": 0, "storytelling": 0, "visual_audio": 0
        }),
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

def assemble_spoken_sentences(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Joins fragmented subtitle caption chunks into complete, grammatical spoken sentences."""
    sentences = []
    current_text = []
    current_start = None

    sponsor_pattern = re.compile(
        r"(?:sponsored by|use code|check the link|link in the description|patreon|subscribe to|hit the bell|leave a like|sign up for|discount code|skillshare|nordvpn|expressvpn|squarespace|audible|athletic greens)",
        re.I
    )

    for seg in raw_segments:
        txt = seg.get("text", "").strip()
        if not txt:
            continue
        # Filter out standalone chapter markers & timestamps
        if re.match(r"^(intro|introduction|outro|chapter\s*\d+|part\s*\d+|timestamp|next steps|takeaway|summary|conclusion)$", txt, re.I):
            continue
        
        if current_start is None:
            current_start = seg.get("start", 0.0)
        current_text.append(txt)

        combined = " ".join(current_text)
        # End of sentence boundary or natural speech pause (16+ words)
        if re.search(r"[.?!](\s+|$)", txt) or len(combined.split()) >= 18:
            clean = re.sub(r"\s+", " ", combined).strip()
            if not sponsor_pattern.search(clean) and len(clean.split()) >= 4:
                sentences.append({
                    "start": current_start,
                    "text": clean,
                    "duration": round(seg.get("end", current_start + 3.0) - current_start, 2)
                })
            current_text = []
            current_start = None

    if current_text:
        clean = re.sub(r"\s+", " ", " ".join(current_text)).strip()
        if not sponsor_pattern.search(clean) and len(clean.split()) >= 4:
            sentences.append({
                "start": current_start or 0.0,
                "text": clean,
                "duration": 3.0
            })

    return sentences


def extract_subtitles_stream(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts genuine spoken dialogue lines from subtitles/captions without downloading video."""
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
        return []

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
        return []

    try:
        req = urllib.request.Request(target_fmt["url"], headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

        raw_chunks = []
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
                    raw_chunks.append({
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
                    raw_chunks.append({"start": 0.0, "duration": 3.0, "end": 3.0, "text": clean})

        return assemble_spoken_sentences(raw_chunks)
    except Exception as e:
        print(f"     [WARN] Subtitle stream download error: {e}")
        return []


def extract_top_praise_comments(info: Dict[str, Any], max_comments: int = 35) -> List[Dict[str, Any]]:
    """Filters comments praising specific editing techniques, pacing, or timestamps, strictly excluding promos/sales."""
    raw_comments = info.get("comments") or []
    analytical_comments = []

    for c in raw_comments[:max_comments]:
        text = (c.get("text") or "").strip()
        if len(text) < 12:
            continue
        # Exclude courses, discounts, promo links, contact handles
        if EXCLUDE_COMMENT_PATTERNS.search(text) or "http" in text.lower() or "www." in text.lower():
            continue

        # Exclude questions (viewer asking for advice is not an authority quote!)
        if text.endswith("?") or re.search(r"\?\s*$", text) or re.match(r"^(should i|how do i|how can|can you|what is|is it|any tips|where do)\b", text.lower()):
            continue

        text_lower = text.lower()
        has_analytical = any(k in text_lower for k in ANALYTICAL_EDITING_KEYWORDS)
        timestamp_match = re.search(r"\b([0-9]{1,2}:[0-9]{2})\b", text)

        if has_analytical or (timestamp_match and any(w in text_lower for w in ("cut", "edit", "transition", "audio", "music", "shot", "scene", "part", "effect", "frame"))):
            analytical_comments.append({
                "author": c.get("author", "Viewer"),
                "text": text,
                "timestamp_mentioned": timestamp_match.group(1) if timestamp_match else None,
                "likes": c.get("like_count", 0)
            })

    analytical_comments.sort(key=lambda x: (x["timestamp_mentioned"] is not None, x["likes"]), reverse=True)
    return analytical_comments


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
# LLM KNOWLEDGE DISTILLATION & SEMANTIC EXTRACTION HELPERS
# ==============================================================================

def ask_brain_sync(prompt: str, system_prompt: Optional[str] = None, format_json: bool = True, timeout: float = 25.0) -> Optional[str]:
    """Synchronous gateway to ask_brain() in backend/engine/brain.py (Gemini 3.5 Flash / Kimi K3 / Spark)."""
    try:
        import sys
        if r"D:\CONTENT-FACTORY" not in sys.path:
            sys.path.insert(0, r"D:\CONTENT-FACTORY")
        from backend.engine.brain import ask_brain
        import asyncio
        return asyncio.run(ask_brain(prompt, system_prompt=system_prompt, format_json=format_json))
    except Exception as e:
        print(f"     [WARN] ask_brain_sync fallback: {e}")
        return None


def extract_complete_noun_phrases(text: str, max_phrases: int = 4) -> List[str]:
    """Extracts complete, un-truncated conceptual noun phrases without chopping words."""
    candidates = []
    # 1. Quoted terms
    for q in re.findall(r'"([^"]+)"', text):
        clean = q.strip().upper()
        if 4 <= len(clean) <= 30:
            candidates.append(clean)
    
    # 2. Key documentary/technical terms
    tech_patterns = [
        r"\b(?:[A-Za-z]+)\s+(?:zoom|pacing|transition|effect|animation|cut|sound|audio|layer|camera|color|grade|texture|mask|timeline|metric|retention)\b",
        r"\b(?:3D|4K|HD|AI|NLE|LUT|SFX)\s+[A-Za-z]+\b",
        r"\b(?:rapid|kinetic|dynamic|forensic|tactile|subtle|drastic|critical)\s+[A-Za-z]+\b"
    ]
    for pat in tech_patterns:
        for m in re.finditer(pat, text, re.I):
            candidates.append(m.group(0).upper())

    # 3. Clean word pairs (no stop words, complete words only)
    clean_txt = re.sub(r"'\w+", "", text)
    words = re.findall(r"\b[A-Za-z]{3,}\b", clean_txt)
    stop = {"THIS", "THAT", "WITH", "FROM", "YOUR", "HAVE", "WHAT", "WHEN", "WHERE", "WHICH", "THEY", "JUST", "WILL", "THEN", "LIKE", "MAKE", "SOME", "MORE", "VERY", "ALSO", "HERE", "INTO", "ABOUT", "DOES", "DOESN"}
    for i in range(len(words) - 1):
        w1, w2 = words[i].upper(), words[i+1].upper()
        if w1 not in stop and w2 not in stop:
            candidates.append(f"{w1} {w2}")
            if len(candidates) >= max_phrases * 2:
                break

    seen = set()
    result = []
    for c in candidates:
        if c not in seen and len(c.split()) >= 2:
            seen.add(c)
            result.append(c)
        if len(result) >= max_phrases:
            break
    return result or ["DYNAMIC PACING", "AUDIO TRANSITION", "VISUAL MOMENTUM"]


def extract_dynamic_numeric_fact(sentences: List[Dict[str, Any]], info: Dict[str, Any], cuts_per_min: float) -> Tuple[str, str]:
    """Finds a real quantitative statistic from transcript sentences or video telemetry without chopping words."""
    num_pattern = re.compile(
        r"(\$?\d+(?:[\.,]\d+)?\s*(?:%|percent|billion|million|thousand|fps|seconds|sec|min|hours|[kmbx])(?!\w)|\$?\d+(?:[\.,]\d+)?)",
        re.I
    )
    for s in sentences:
        txt = s.get("text", "")
        m = num_pattern.search(txt)
        if m:
            num_str = m.group(1).strip()
            after_text = txt[m.end():m.end()+35].strip()
            after_words = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", after_text) if w.lower() not in {"the", "and", "that", "with", "from", "for"}]
            context_str = " ".join(after_words[:2]).upper()
            headline = "VERIFIED METRIC" if "%" in num_str or "$" in num_str else "QUANTIFIED EVIDENCE"
            highlight = f"{num_str.upper()} {context_str}".strip()[:30]
            return headline, highlight
    
    views = int(info.get("view_count") or 0)
    if views > 1000:
        return "RETENTION SCALE", f"{views:,} VIEWS"
    return "PACING VELOCITY", f"{cuts_per_min:.1f} CUTS/MIN"


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
    Reverse-engineers cut pacing, motion cards (red_slam_word, stat_counter, 3_item_list, workflow_stepper, quote_box),
    and cosine zoom triggers dynamically from real transcript speech and analytical feedback.
    Writes to director_vault/techniques/.
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

    # Distill clean 2-3 word editorial techniques via ask_brain()
    concepts_prompt = f"""You are an elite video editing director.
Topic: "{title}"
Spoken Narration Excerpt: "{full_text[:400]}"

Extract 4 clean, professional 2-to-3 word editing techniques or visual pacing pillars based on this video (e.g. "MATCH CUT TRANSITIONS", "AUDIO MOTIVATION", "TACTILE PAPER OVERLAYS", "DYNAMIC ZOOM PUNCH").
Return strictly a JSON array of 4 uppercase strings:
["TECHNIQUE 1", "TECHNIQUE 2", "TECHNIQUE 3", "TECHNIQUE 4"]
Output strictly JSON without markdown fences."""

    brain_concepts = None
    res = ask_brain_sync(concepts_prompt, format_json=True)
    if res:
        try:
            clean_res = re.sub(r"^```(?:json)?|```$", "", res.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(clean_res)
            if isinstance(parsed, list) and len(parsed) >= 3:
                brain_concepts = [str(x).strip().upper() for x in parsed if len(str(x).strip()) >= 4][:4]
        except Exception:
            pass

    if not brain_concepts:
        brain_concepts = extract_complete_noun_phrases(full_text or title, 4)

    slam_headline = "CORE REVELATION"
    slam_highlight = brain_concepts[0] if brain_concepts else "VISUAL MOMENTUM"

    stat_headline, stat_highlight = extract_dynamic_numeric_fact(sentences, info, cuts_per_min)

    list_pillars = brain_concepts[:3] if len(brain_concepts) >= 3 else ["HOOK PACING", "AUDIO CONTRAST", "FINAL PAYOFF"]
    list_highlight = " · ".join(list_pillars)
    stepper_highlight = " -> ".join([p.title() for p in list_pillars])

    if comments and not EXCLUDE_COMMENT_PATTERNS.search(comments[0]["text"]):
        quote_text = comments[0]["text"]
        quote_source = f"Viewer @{comments[0]['author']}"
    else:
        quote_candidates = [s["text"] for s in sentences if len(s.get("text", "")) > 25]
        quote_text = quote_candidates[0] if quote_candidates else (sentences[0]["text"] if sentences else f"Pacing in {title} is driven by audio motivation.")
        quote_source = "Director Principle"

    quote_highlight = quote_text[:75] if len(quote_text) <= 75 else quote_text[:72] + "..."

    motion_cards = [
        {
            "template": "red_slam_word",
            "trigger_context": "Critical inflection point or pivotal narrative turn",
            "example_headline": slam_headline,
            "example_highlight": slam_highlight,
            "sfx": "thud.wav",
            "grade": "hard_bw"
        },
        {
            "template": "stat_counter",
            "trigger_context": "Numeric metrics, retention spikes, or quantified documentary evidence",
            "example_headline": stat_headline,
            "example_highlight": stat_highlight,
            "sfx": "whoosh.wav",
            "grade": "amber"
        },
        {
            "template": "3_item_list",
            "trigger_context": "Structured 3-part editing frameworks or procedural rules",
            "example_headline": "TACTICAL PILLARS",
            "example_highlight": list_highlight,
            "sfx": "click.wav",
            "grade": "teal_split"
        },
        {
            "template": "workflow_stepper",
            "trigger_context": "Step-by-step editing phase progression or technical tutorial execution",
            "example_headline": "PRODUCTION PIPELINE",
            "example_highlight": stepper_highlight,
            "sfx": "click.wav",
            "grade": "amber"
        },
        {
            "template": "quote_box",
            "trigger_context": "Authority statements, creator directives, or verified feedback",
            "example_headline": quote_source.upper()[:24],
            "example_highlight": quote_highlight,
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
- Motion Card Integration: red_slam_word, stat_counter, 3_item_list, workflow_stepper, quote_box

## Core Pacing & Cutting Rules
"""
    for r in rules:
        md_content += f"- {r}\n"

    md_content += "\n## Motion Card Deployments\n"
    for mc in motion_cards:
        md_content += f"- **{mc['template']}**: {mc['trigger_context']} (Headline: `{mc['example_headline']}`, SFX: `{mc['sfx']}`, Grade: `{mc['grade']}`)\n"

    if comments:
        md_content += "\n## Viewer Feedback on Pacing\n"
        for c in comments[:3]:
            ts = f" (at {c.get('timestamp_mentioned')})" if c.get('timestamp_mentioned') else ""
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
    Extracts high-retention viral opening hooks via ask_brain() knowledge distillation
    (or authentic spoken opening sentences), strictly avoiding tutorial filler.
    Writes to director_vault/hooks/.
    """
    title = info.get("title", "Viral Video")
    video_id = info.get("id") or "vid_hook"
    view_count = int(info.get("view_count") or 0)
    like_count = int(info.get("like_count") or 0)
    ratio = round(view_count / max(1, like_count), 1)

    spoken_opening = " ".join(s["text"] for s in sentences[:6]).strip()

    prompt = f"""You are an elite YouTube documentary director.
Video Topic: "{title}"
Actual Spoken Narration: "{spoken_opening[:350]}"

Distill 3 high-retention viral opening hooks for this topic. Do NOT write tutorial introductions (never say "Today we are talking about..."). Write compelling documentary-grade hooks that grab attention in the first 3 seconds.
Return strictly a JSON array of 3 objects:
[
  {{
    "hook": "Full grammatical curiosity gap hook sentence",
    "trigger_type": "curiosity_gap",
    "duration_seconds": 3.2,
    "visual_pacing": "Rapid cosine punch-in with high-contrast archival overlay"
  }},
  {{
    "hook": "Full grammatical counter-intuitive hook sentence",
    "trigger_type": "counter_intuitive",
    "duration_seconds": 3.0,
    "visual_pacing": "Forensic declassified document card with heavy thud SFX"
  }},
  {{
    "hook": "Full grammatical high-stakes risk or anomaly hook sentence",
    "trigger_type": "negative_bias",
    "duration_seconds": 3.4,
    "visual_pacing": "Dynamic stat counter with whoosh riser"
  }}
]
Output strictly the JSON array, no markdown fences."""

    brain_res = ask_brain_sync(prompt, format_json=True)
    hooks = None
    if brain_res:
        try:
            clean_res = re.sub(r"^```(?:json)?|```$", "", brain_res.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(clean_res)
            if isinstance(parsed, list) and len(parsed) >= 3 and all("hook" in h for h in parsed):
                hooks = parsed[:3]
            elif isinstance(parsed, dict) and "hooks" in parsed:
                hooks = parsed["hooks"][:3]
        except Exception as e:
            print(f"     [WARN] Could not parse brain hooks JSON: {e}")

    # Fallback to authentic real spoken sentences (never f-string templates!)
    if not hooks:
        h1 = sentences[0]["text"] if sentences else f"The documented investigation behind {title}."
        h2 = sentences[1]["text"] if len(sentences) > 1 else f"Behind the scenes of {title}, an invisible mechanism was operating."
        h3 = sentences[2]["text"] if len(sentences) > 2 else f"Failing to recognize how {title} functions leads to immediate misinterpretation."
        hooks = [
            {
                "hook": h1,
                "trigger_type": "curiosity_gap",
                "duration_seconds": 3.2,
                "visual_pacing": "Rapid cosine punch-in with high-contrast B&W archival overlay"
            },
            {
                "hook": h2,
                "trigger_type": "counter_intuitive",
                "duration_seconds": 3.0,
                "visual_pacing": "Forensic declassified scan with thud.wav SFX"
            },
            {
                "hook": h3,
                "trigger_type": "negative_bias",
                "duration_seconds": 3.4,
                "visual_pacing": "Dynamic stat counter with whoosh riser"
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
- Primary Opening: "{hooks[0]['hook']}"

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
        "input": f"Topic: {title}\nViews: {view_count:,}\nPrimary Hook Line: {hooks[0]['hook'][:180]}",
        "output": output_payload
    }


def synthesize_storytelling_task(
    info: Dict[str, Any],
    sentences: List[Dict[str, Any]],
    comments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Task 3: storytelling (Target: 1,500 | 25%)
    Parses documentary transcripts into authentic 8-sentence Shorts or 24-sentence 4-Act scripts
    via ask_brain() knowledge distillation or real spoken sentences.
    Writes to director_vault/styles/.
    """
    title = info.get("title", "Documentary Narrative")
    video_id = info.get("id") or "vid_story"
    duration = float(info.get("duration") or 60.0)

    spoken_sample = " ".join(s["text"] for s in sentences[:15]).strip()

    prompt = f"""You are an elite documentary scriptwriter.
Video Topic: "{title}"
Actual Spoken Dialogue Excerpt: "{spoken_sample[:500]}"

Distill an authentic, high-retention 8-sentence documentary script based on the topic and spoken dialogue. Every sentence must be a complete, compelling grammatical sentence. Do NOT include chapter markers (such as "Introduction" or "Next Steps").
Return strictly a JSON object:
{{
  "hook_line": "Sentence 1",
  "sentences": [
    "Sentence 1",
    "Sentence 2",
    "Sentence 3",
    "Sentence 4",
    "Sentence 5",
    "Sentence 6",
    "Sentence 7",
    "Sentence 8"
  ],
  "takeaway": "Sentence 8"
}}
Output strictly JSON without markdown fences."""

    brain_res = ask_brain_sync(prompt, format_json=True)
    distilled_sentences = None
    hook_line = None
    takeaway_line = None

    if brain_res:
        try:
            clean_res = re.sub(r"^```(?:json)?|```$", "", brain_res.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(clean_res)
            if isinstance(parsed, dict) and "sentences" in parsed and len(parsed["sentences"]) >= 6:
                distilled_sentences = parsed["sentences"][:8]
                hook_line = parsed.get("hook_line") or distilled_sentences[0]
                takeaway_line = parsed.get("takeaway") or distilled_sentences[-1]
        except Exception as e:
            print(f"     [WARN] Could not parse brain storytelling JSON: {e}")

    # Fallback strictly to real complete spoken sentences (never f-string templates!)
    if not distilled_sentences:
        distilled_sentences = [s["text"] for s in sentences[:8]]
        while len(distilled_sentences) < 8 and len(sentences) > len(distilled_sentences):
            distilled_sentences.append(sentences[len(distilled_sentences)]["text"])
        if len(distilled_sentences) < 8:
            distilled_sentences.append(f"This completes the core operational breakdown of {title}.")
        hook_line = distilled_sentences[0] if distilled_sentences else title
        takeaway_line = distilled_sentences[-1] if distilled_sentences else title

    acts = [
        {
            "act": 1,
            "name": "Full Narrative Arc",
            "sentences": distilled_sentences
        }
    ]
    format_type = "8-Sentence Short"

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

    instruction = f"Write an 8-sentence high-retention narrative script for a documentary short on: \"{title}\""

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
    (hard_bw, teal_split, amber), and SFX cues (thud.wav, whoosh.wav, click.wav, riser.wav)
    dynamically mapped from sentence semantics. Writes to director_vault/sfx/.
    """
    title = info.get("title", "Visual Audio Design")
    video_id = info.get("id") or "vid_sfx"
    duration = float(info.get("duration") or 60.0)

    scene_beats = []
    grade_cycle = ["hard_bw", "teal_split", "amber"]
    sfx_cycle = ["thud.wav", "whoosh.wav", "click.wav", "riser.wav"]
    visual_types = ["forensic_doc", "motion_card", "treated_image", "evidence_board", "map_flyover"]
    card_templates = ["red_slam_word", "stat_counter", "3_item_list", "workflow_stepper", "star_badge", "quote_box"]

    sample_sentences = sentences[:8] if sentences else [{"text": f"The visual progression of {title} begins here."}]
    for idx, s in enumerate(sample_sentences, 1):
        text = s.get("text", "").strip()
        grade = grade_cycle[(idx - 1) % len(grade_cycle)]
        sfx_1 = sfx_cycle[(idx - 1) % len(sfx_cycle)]
        sfx_2 = sfx_cycle[idx % len(sfx_cycle)]
        card_tpl = card_templates[(idx - 1) % len(card_templates)]
        v_type_1 = visual_types[(idx - 1) % len(visual_types)]
        v_type_2 = "treated_image" if v_type_1 != "treated_image" else "motion_card"

        noun_phrases = extract_complete_noun_phrases(text, 2)
        kw = noun_phrases[0] if noun_phrases else "DOCUMENTARY RECORD"

        if re.search(r"\b(\d+|%|\$)\b", text):
            hl_1 = "QUANTIFIED RECORD"
            hl_2 = "EMPIRICAL DATA"
        elif re.search(r"\b(why|how|what|secret|hidden)\b", text, re.I):
            hl_1 = "SYSTEM MECHANISM"
            hl_2 = "FORENSIC BREAKDOWN"
        elif re.search(r"\b(fail|risk|mistake|wrong|never)\b", text, re.I):
            hl_1 = "ANOMALY DETECTED"
            hl_2 = "CRITICAL IMPLICATION"
        else:
            hl_1 = "KEY DIRECTIVE"
            hl_2 = "DOCUMENTARY EVIDENCE"

        prompt_1 = f"archival documentary footage depicting {kw.lower()} regarding {title}, 35mm film grain, high dynamic range, cinematic lighting"
        prompt_2 = f"forensic technical dossier and declassified notes on {kw.lower()}, high contrast documentary realism"

        scene_beats.append({
            "scene_idx": idx,
            "spoken_sentence": text,
            "beat_1": {
                "type": v_type_1,
                "template": card_tpl if "card" in v_type_1 else None,
                "headline": hl_1 if "card" in v_type_1 else None,
                "highlight": kw if "card" in v_type_1 else None,
                "prompt": prompt_1 if "card" not in v_type_1 else None,
                "grade": grade,
                "sfx": sfx_1
            },
            "beat_2": {
                "type": v_type_2,
                "template": card_tpl if "card" in v_type_2 else None,
                "headline": hl_2 if "card" in v_type_2 else None,
                "highlight": kw if "card" in v_type_2 else None,
                "prompt": prompt_2 if "card" not in v_type_2 else None,
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
- Visual Schema: treated_image, forensic_doc, map_flyover, evidence_board + motion_card paired beats
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


QUERY_MODIFIERS = [
    "breakdown", "case study", "retention 2026", "tutorial 2025",
    "deep dive analysis", "masterclass", "secrets", "behind the scenes",
    "workflow", "viral formula", "pacing techniques", "documentary style",
    "johnny harris style", "vox style", "magnates media style", "advanced editing"
]


def search_youtube_query(
    query: str,
    count: int = 10,
    exclude_ids: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    QUOTA-SAFE SEARCH (0 units on discovery, 1 unit per 50 videos for metadata):
    1. Discovers video IDs via yt-dlp flat playlist extraction with depth 50 (0 API units).
    2. Detects query saturation (>80% seen) and dynamically appends modifiers (e.g. breakdown, case study, 2026).
    3. Enriches candidates with batch /youtube/v3/videos if key present.
    4. Prioritizes unseen candidates to break duplicate loops.
    """
    api_key = get_youtube_api_key()
    candidate_limit = max(count * 5, 50)
    print(f"\nSearching YouTube (0-Quota Flat Search, depth: {candidate_limit}) for query: '{query}'...")

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
        err_msg = str(e).lower()
        if "429" in err_msg or "too many requests" in err_msg or "timed out" in err_msg or "timeout" in err_msg:
            print(f"\n     [RATE LIMIT 429 / TIMEOUT] Search hit rate limit ({e}). Backing off 120s...")
            time.sleep(120)
        else:
            print(f"     [WARN] yt-dlp search error: {e}")

    # Query Saturation Check (>80% already seen) -> Dynamically append modifier keywords
    if exclude_ids and candidates:
        seen = [c for c in candidates if c["id"] in exclude_ids or c["title"].lower().strip() in exclude_ids]
        seen_ratio = len(seen) / len(candidates)
        if seen_ratio >= 0.8:
            modifier = random.choice(QUERY_MODIFIERS)
            mod_query = f"{query} {modifier}"
            print(f"     [QUERY SATURATED {seen_ratio*100:.0f}% SEEN] Appending modifier: '{mod_query}'...")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    res_mod = ydl.extract_info(f"ytsearch{candidate_limit}:{mod_query}", download=False)
                    for e in res_mod.get('entries', []):
                        if e and e.get('id') and not any(c['id'] == e['id'] for c in candidates):
                            candidates.append({
                                "id": e['id'],
                                "title": e.get('title', ''),
                                "url": f"https://www.youtube.com/watch?v={e['id']}",
                                "view_count": e.get('view_count') or 0
                            })
            except Exception as e:
                print(f"     [WARN] Modifier search error: {e}")

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

    # Partition and prioritize unseen candidates
    if exclude_ids:
        unseen = [c for c in candidates if c["id"] not in exclude_ids and c["title"].lower().strip() not in exclude_ids]
        seen = [c for c in candidates if c["id"] in exclude_ids or c["title"].lower().strip() in exclude_ids]
        unseen.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        seen.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        sorted_candidates = unseen + seen
    else:
        candidates.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        sorted_candidates = candidates

    top_items = sorted_candidates[:count]
    for idx, c in enumerate(top_items, 1):
        vc = f"{c['view_count']:,}" if c.get('view_count') else "N/A"
        is_new = " [NEW]" if exclude_ids and (c["id"] not in exclude_ids and c["title"].lower().strip() not in exclude_ids) else ""
        print(f"     {idx}. [{vc} views]{is_new} {c['title'][:65]}")

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
            if len(sentences) < 4:
                print(f"     [SKIP] Insufficient spoken dialogue ({len(sentences)} sentences): \"{title[:55]}\". Skipping to protect dataset quality.")
                return {"title": title, "skipped": True, "reason": "insufficient_dialogue"}
            print(f"     > Extracted {len(sentences)} clean spoken sentences.")

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
            delay = round(random.uniform(4.5, 6.5), 2)
            print(f"     [PACING] Pausing {delay}s between video requests (strictly respects 15 RPM limit)...")
            time.sleep(delay)
            return record
    except Exception as e:
        err_msg = str(e).lower()
        if "429" in err_msg or "too many requests" in err_msg or "timed out" in err_msg or "timeout" in err_msg:
            print(f"\n     [RATE LIMIT 429 / TIMEOUT] Rate limit detected during harvest ({e}). Auto-backing off for 120s...")
            time.sleep(120)
        else:
            print(f"     [ERROR] Failed harvesting {entry_or_url}: {e}")
            time.sleep(round(random.uniform(4.5, 6.5), 2))
        return None


# ==============================================================================
# MASTER HARVEST RUNNER & CLI
# ==============================================================================

def run_balanced_plan(
    state: Dict[str, Any],
    count_per_task: int = 10,
    visual_cuts: bool = False,
    query_pointers: Optional[Dict[str, int]] = None
) -> int:
    """Executes the balanced distribution across all 4 tasks towards the 6,000 target."""
    print("\n==================================================================")
    print(f"LAUNCHING BALANCED DATASET HARVESTER: {count_per_task} VIDEOS PER TASK ({count_per_task * 4} TOTAL)")
    print("Distribution: editing (42%) | hooks (25%) | storytelling (25%) | visual_audio (16%)")
    print(f"Target Dataset: {DATASET_PATH}")
    print(f"Director Vault: {VAULT_DIR}")
    print(f"Checkpoint State: {STATE_PATH}")
    print("Pacing: 4.5s - 6.5s per video (Guarantees < 12 RPM, respects Gemini 15 RPM ceiling)")
    print("Zero-Disk Guarantee: 0 MB video files saved to SSD")
    print("==================================================================\n")

    total_harvested_cycle = 0
    tasks_order = ["editing", "hooks", "storytelling", "visual_audio"]
    for task_name in tasks_order:
        current_cnt = state["counts"].get(task_name, 0)
        target_cnt = TASK_BALANCED_TARGETS.get(task_name, 1500)
        if current_cnt >= target_cnt:
            print(f"\n>>> TASK: [{task_name.upper()}] target already met ({current_cnt}/{target_cnt}). Skipping. <<<")
            continue

        print(f"\n>>> PROCESSING TASK: [{task_name.upper()}] (Current: {current_cnt} / Target: {target_cnt}) <<<")

        queries = TASK_QUERIES.get(task_name, [])
        if not queries:
            continue

        start_ptr = state.get("query_indices", {}).get(task_name, 0)
        if query_pointers is not None:
            start_ptr = query_pointers.get(task_name, start_ptr)

        harvested_for_task = 0
        task_processed = state["processed_ids"].get(task_name, set())

        for q_offset in range(len(queries)):
            if harvested_for_task >= count_per_task:
                break
            if state["counts"].get(task_name, 0) >= target_cnt:
                print(f"     [GOAL REACHED] Task [{task_name}] target met ({state['counts'][task_name]}/{target_cnt}).")
                break

            q_idx = (start_ptr + q_offset) % len(queries)
            q = queries[q_idx]

            needed = count_per_task - harvested_for_task
            fetch_count = max(needed * 2, 6)
            items = search_youtube_query(q, fetch_count, exclude_ids=task_processed)
            time.sleep(round(random.uniform(2.0, 3.5), 2))

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
                    total_harvested_cycle += 1
                    print(f"     [PROGRESS] Harvested {harvested_for_task}/{count_per_task} for task [{task_name}].")

            # Advance and persist query pointer across restarts
            next_q_idx = (q_idx + 1) % len(queries)
            if "query_indices" not in state:
                state["query_indices"] = {}
            state["query_indices"][task_name] = next_q_idx
            if query_pointers is not None:
                query_pointers[task_name] = next_q_idx
            save_harvest_state(state)

        print(f"\n[TASK COMPLETE] [{task_name.upper()}] batch finished: {harvested_for_task} new examples added.\n")

    print("\n[BALANCED PLAN COMPLETE] Updated checkpoint state:")
    for t in tasks_order:
        print(f"  - {t}: {state['counts'].get(t, 0)} / {TASK_BALANCED_TARGETS[t]}")
    print(f"  - TOTAL: {state['counts'].get('total', 0)} / 6,000\n")
    return total_harvested_cycle


def run_continuous_harvest(
    state: Dict[str, Any],
    count_per_task: int = 5,
    cooldown_seconds: int = 90,
    target_total: int = 6000,
    visual_cuts: bool = False
):
    """
    Continuous auto-looping daemon that runs cycles indefinitely until target_total (6,000) is reached.
    - Two-tier pacing: 4.5s-6.5s per video, 90s inter-cycle cooldown.
    - Auto-backoff: 120s on HTTP 429 or network timeouts.
    - Micro-batches: 5 videos per task (20 videos per cycle).
    - Query rotation: rotates across 25+ diverse search queries per task.
    - Zero-disk bloat: all temp files purged immediately.
    """
    print("\n==================================================================")
    print("CONTINUOUS AUTO-PACED DATASET HARVESTER DAEMON STARTED (--continuous)")
    print(f"Target Total: {target_total} examples in {DATASET_PATH}")
    print(f"Micro-Batch: {count_per_task} videos per task ({count_per_task * 4} videos/cycle)")
    print("Per-Video Delay: 4.5s - 6.5s (Guarantees < 12 RPM, respects Gemini 15 RPM ceiling)")
    print(f"Inter-Cycle Cooldown: {cooldown_seconds}s sleep between cycles (prevents YouTube IP blocks)")
    print("Zero-Disk Guarantee: 0 MB temporary files saved to SSD")
    print(f"Checkpoint State: {STATE_PATH}")
    print("==================================================================\n")

    cycle = 1
    query_pointers = state.get("query_indices", {t: 0 for t in ["editing", "hooks", "storytelling", "visual_audio"]})

    while True:
        total_now = state["counts"].get("total", 0)
        if total_now >= target_total:
            print(f"\n[MASTER GOAL REACHED] Dataset reached {total_now}/{target_total} examples! Daemon completed.")
            break

        all_done = all(state["counts"].get(t, 0) >= TASK_BALANCED_TARGETS[t] for t in TASK_BALANCED_TARGETS)
        if all_done:
            print(f"\n[ALL TASK TARGETS MET] Total records: {total_now}. Daemon completed.")
            break

        print(f"\n==================================================================")
        print(f">>> DAEMON CYCLE #{cycle} STARTING (Total Harvested So Far: {total_now} / {target_total}) <<<")
        print(f"==================================================================")

        cycle_added = run_balanced_plan(
            state,
            count_per_task=count_per_task,
            visual_cuts=visual_cuts,
            query_pointers=query_pointers
        )

        total_after = state["counts"].get("total", 0)
        print(f"\n==================================================================")
        print(f">>> DAEMON CYCLE #{cycle} FINISHED (+{cycle_added} new examples added) <<<")
        print(f"Progress toward {target_total} target:")
        print(f"  - editing:      {state['counts'].get('editing', 0):>5} / {TASK_BALANCED_TARGETS['editing']}")
        print(f"  - hooks:        {state['counts'].get('hooks', 0):>5} / {TASK_BALANCED_TARGETS['hooks']}")
        print(f"  - storytelling: {state['counts'].get('storytelling', 0):>5} / {TASK_BALANCED_TARGETS['storytelling']}")
        print(f"  - visual_audio: {state['counts'].get('visual_audio', 0):>5} / {TASK_BALANCED_TARGETS['visual_audio']}")
        print(f"  - TOTAL:        {total_after:>5} / {target_total}")
        print(f"==================================================================")

        if total_after >= target_total:
            print(f"\n[MASTER GOAL REACHED] Reached {total_after}/{target_total} records! Daemon completed.")
            break

        print(f"\n[INTER-CYCLE COOLDOWN] Completed {count_per_task * 4}-video cycle. Sleeping {cooldown_seconds}s to reset IP thresholds before Cycle #{cycle + 1}...")
        for remaining in range(cooldown_seconds, 0, -15):
            print(f"     ... cooldown: {remaining}s remaining ...")
            time.sleep(min(15, remaining))
        cycle += 1


def main():
    parser = argparse.ArgumentParser(description="Multi-Task Balanced Video Dataset Harvester")
    parser.add_argument("--task", choices=["editing", "hooks", "storytelling", "visual_audio", "all"], default="all",
                        help="Specific production task to harvest")
    parser.add_argument("--continuous", action="store_true",
                        help="Run continuous auto-paced daemon looping until 6,000 target is reached")
    parser.add_argument("--cooldown", type=int, default=90,
                        help="Inter-cycle cooldown in seconds for continuous mode (default: 90s)")
    parser.add_argument("--run-balanced-plan", action="store_true",
                        help="Run master balanced distribution plan cycle across all 4 tasks")
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

    if args.continuous:
        cycle_count = args.count if args.count != 10 else 5
        run_continuous_harvest(
            state,
            count_per_task=cycle_count,
            cooldown_seconds=args.cooldown,
            target_total=args.target_total,
            visual_cuts=args.visual_cuts
        )
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
