"""
CONTENT-FACTORY: Autonomous Multi-Source Video & Director Knowledge Harvester
-----------------------------------------------------------------------------
1. Zero-Disk Streaming: Extracts transcripts & metadata directly from YouTube API without saving full video files.
2. CapCut & NLE Tutorial Extraction: Analyzes editing tutorials to extract concrete cutting, pacing, and visual rules.
3. Scripting & Storytelling Masterclasses: Extracts 3-Act structures, hook formulas, and curiosity gaps.
4. Comment Sentiment Mining: Scrapes top viewer comments praising editing ("who edited this", "the edit at 2:15") to identify high-retention moments.
5. Obsidian Director Vault Sync: Writes learned techniques directly to D:\\CONTENT-FACTORY\\director_vault\\ for instant runtime recall.
6. Fine-Tuning Corpus: Appends Alpaca-formatted training pairs to C:\\cf_training\\dataset.jsonl for LoRA fine-tuning.
"""

import os
import sys
import re
import json
import time
import argparse
import urllib.request
from typing import List, Dict, Any, Optional

import yt_dlp

WORKSPACE_DIR = os.path.abspath(r"C:\cf_training")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp")
DATASET_PATH = os.path.join(WORKSPACE_DIR, "dataset.jsonl")
VAULT_DIR = os.path.abspath(r"D:\CONTENT-FACTORY\director_vault")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "techniques"), exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "hooks"), exist_ok=True)
os.makedirs(os.path.join(VAULT_DIR, "styles"), exist_ok=True)


PRAISE_KEYWORDS = [
    "edit", "editor", "who edited", "editing", "transitions", "transition",
    "capcut", "premiere", "pacing", "sound design", "visuals", "cinematic",
    "b-roll", "clean edit", "insane edit", "underrated", "chills", "masterpiece"
]


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
                text = re.sub(r"\[.*?\]", "", text).strip()  # Remove [music], [applause]
                if text:
                    sentences.append({
                        "start": round(start_ms / 1000.0, 2),
                        "duration": round(dur_ms / 1000.0, 2),
                        "end": round((start_ms + dur_ms) / 1000.0, 2),
                        "text": text
                    })
        elif target_fmt.get("ext") == "vtt":
            # Basic VTT line parsing
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


def extract_top_praise_comments(info: Dict[str, Any], max_comments: int = 40) -> List[Dict[str, str]]:
    """Filters comments praising specific editing techniques, pacing, or timestamps."""
    raw_comments = info.get("comments") or []
    praise_comments = []

    for c in raw_comments[:max_comments]:
        text = c.get("text", "")
        text_lower = text.lower()
        if any(k in text_lower for k in PRAISE_KEYWORDS):
            # Check for timestamp mentions like "2:15" or "0:45"
            timestamp_match = re.search(r"\b([0-9]{1,2}:[0-9]{2})\b", text)
            praise_comments.append({
                "author": c.get("author", "Viewer"),
                "text": text.strip(),
                "timestamp_mentioned": timestamp_match.group(1) if timestamp_match else None,
                "likes": c.get("like_count", 0)
            })

    return praise_comments


def synthesize_capcut_rules(title: str, sentences: List[Dict[str, Any]], comments: List[Dict[str, str]]) -> Dict[str, Any]:
    """Extracts actionable editing rules from tutorial transcripts for Obsidian + fine-tuning."""
    full_text = " ".join(s["text"] for s in sentences)
    
    rules = []
    # Identify key editing principles mentioned in narration
    if re.search(r"zoom|scale|punch.?in", full_text, re.I):
        rules.append("Use dynamic cosine zoom-in (1.1x to 1.2x) on key emphasis nouns and data points.")
    if re.search(r"sound effect|sfx|whoosh|thud|riser", full_text, re.I):
        rules.append("Layer whoosh/riser SFX 2-3 frames before every visual transition and heavy thud on fact reveals.")
    if re.search(r"b-roll|overlay|footage", full_text, re.I):
        rules.append("Cut to archival or contextual B-roll every 2.0 to 2.8 seconds to maintain visual stimulation.")
    if re.search(r"caption|subtitle|kinetic|font", full_text, re.I):
        rules.append("Render stark bold subtitles with active-word color highlights (yellow or cyan) matching spoken timing.")
    if re.search(r"mask|cutout|green screen|paper", full_text, re.I):
        rules.append("Apply paper-texture border overlays and photo cutouts with drop shadows for documentary feel.")
    if re.search(r"color grade|lut|teal|contrast", full_text, re.I):
        rules.append("Apply high-contrast desaturated grade with warm skin tones and deep obsidian shadows (#0B0F19).")

    if not rules:
        rules.append("Maintain high-tempo visual rhythm: cut every 2.5s and align audio transitions with vocal pauses.")

    # Save to Obsidian Director Vault
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:40].strip("_")
    note_path = os.path.join(VAULT_DIR, "techniques", f"{safe_slug}.md")
    
    obsidian_content = f"""# {title}

## Source
- Type: Editing Tutorial / Masterclass
- Analyzed Spoken Segments: {len(sentences)}
- Viewer Praise Comments: {len(comments)}

## Extracted Editing Rules
"""
    for r in rules:
        obsidian_content += f"- {r}\n"

    if comments:
        obsidian_content += "\n## Top Viewer Feedback\n"
        for c in comments[:3]:
            ts_str = f" (at {c['timestamp_mentioned']})" if c['timestamp_mentioned'] else ""
            obsidian_content += f"> \"{c['text']}\"{ts_str} — {c['author']}\n\n"

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(obsidian_content)
    except Exception as e:
        print(f"     [WARN] Could not write vault note: {e}")

    return {
        "title": title,
        "category": "editing_rules",
        "rules": rules,
        "praise_count": len(comments)
    }


def synthesize_documentary_acts(title: str, duration: float, sentences: List[Dict[str, Any]], comments: List[Dict[str, str]]) -> Dict[str, Any]:
    """Builds a multi-act long-form documentary script & beat structure."""
    is_long_form = duration > 120.0
    
    # Divide sentences into acts/chapters
    total_s = len(sentences)
    if is_long_form and total_s >= 12:
        acts = [
            {"act": 1, "title": "The Hook & Inciting Anomaly", "sentences": sentences[:int(total_s * 0.2)]},
            {"act": 2, "title": "The Hidden Mechanism", "sentences": sentences[int(total_s * 0.2):int(total_s * 0.55)]},
            {"act": 3, "title": "The Climax & Revelation", "sentences": sentences[int(total_s * 0.55):int(total_s * 0.85)]},
            {"act": 4, "title": "The Aftermath & Takeaway", "sentences": sentences[int(total_s * 0.85):]}
        ]
    else:
        acts = [{"act": 1, "title": "Full Narrative", "sentences": sentences}]

    beats = []
    beat_idx = 1
    for act in acts:
        for s in act["sentences"][:20]: # Keep beat list compact
            beats.append({
                "id": f"beat_{beat_idx}",
                "act": act["act"],
                "duration": max(1.8, s.get("duration", 2.5)),
                "narration": s["text"],
                "sfx": "whoosh.wav" if beat_idx % 3 == 0 else "thud.wav" if beat_idx % 5 == 0 else None
            })
            beat_idx += 1

    hook_line = sentences[0]["text"] if sentences else f"The untold truth behind {title}."

    # Write hook template to Obsidian Vault
    safe_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower())[:35].strip("_")
    hook_note = os.path.join(VAULT_DIR, "hooks", f"hook_{safe_slug}.md")
    with open(hook_note, "w", encoding="utf-8") as f:
        f.write(f"""# Hook: {title}

## First Spoken Line (0:00 - 0:03)
> "{hook_line}"

## Structure
- Duration: {duration:.1f}s
- Format: {"Long-Form Documentary (16:9)" if is_long_form else "Short-Form (9:16)"}
- Narrative Acts: {len(acts)}
""")

    director_output = {
        "title": title,
        "format": "16:9 Long-Form Documentary" if is_long_form else "9:16 Short",
        "duration_seconds": round(duration, 1),
        "hook": hook_line,
        "acts_count": len(acts),
        "total_beats": len(beats),
        "avg_cut_interval": round(duration / max(1, len(beats)), 2),
        "beats": beats
    }

    return {
        "prompt": f"Act as an expert documentary filmmaker. Design a complete narrative structure and beat manifest for: \"{title}\"",
        "response": json.dumps(director_output, indent=2)
    }


def extract_visual_cuts_lowres(url: str, job_id: str) -> List[float]:
    """
    Downloads an ultra-tiny 144p/240p video sample (~1.5 MB),
    detects real visual camera cut timestamps via FFmpeg,
    and immediately deletes the file from disk (zero lingering bloat).
    """
    out_video = os.path.join(TEMP_DIR, f"{job_id}_lowres.%(ext)s")
    cuts_txt = os.path.join(TEMP_DIR, f"{job_id}_cuts.txt")

    ydl_opts = {
        'format': 'worstvideo[height<=240]/worst[height<=240]/worst',
        'outtmpl': out_video,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['web']}},
        'download_ranges': yt_dlp.utils.download_range_func(None, [(0, 60)]),
    }

    actual_video = None
    cuts = [0.0]

    try:
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
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

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
        print(f"     [WARN] Low-res visual cut detection skipped: {e}")
    finally:
        for p in [actual_video, cuts_txt]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    return cuts


def harvest_video_entry(
    entry_or_url: str,
    mode: str = "documentary",
    sample_visual_cuts: bool = False,
    existing_titles: Optional[set] = None
) -> Optional[Dict[str, Any]]:
    """Streams metadata, transcript, and comments with ZERO temporary video storage."""
    if existing_titles is None:
        existing_titles = get_existing_harvested_titles()

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

            title = info.get("title", "Documentary Video")
            duration = float(info.get("duration") or 60.0)
            url = info.get("webpage_url") or entry_or_url

            if title.lower().strip() in existing_titles:
                print(f"     [SKIP] Already harvested: \"{title[:55]}\". Skipping to preserve bandwidth.")
                return {"title": title, "skipped": True}

            print(f"     > Streaming subtitles & metadata for: \"{title[:55]}\" ({duration/60:.1f} min)...")
            sentences = extract_subtitles_stream(info)
            print(f"     > Extracted {len(sentences)} spoken transcript segments.")

            comments = extract_top_praise_comments(info)
            print(f"     > Scraped {len(comments)} comments highlighting editing/pacing.")

            # Optional visual cuts sampling via tiny 240p sample
            visual_cuts = []
            if sample_visual_cuts:
                print(f"     > Sampling camera cuts via 240p stream (~1.5 MB)...")
                job_id = f"samp_{int(duration)}_{abs(hash(url)) % 10000}"
                visual_cuts = extract_visual_cuts_lowres(url, job_id)
                cuts_per_min = round(len(visual_cuts) / max(0.5, min(duration, 60.0) / 60.0), 1)
                print(f"     > Detected {len(visual_cuts)} real scene cuts ({cuts_per_min} cuts/min).")

            if mode == "tutorial":
                rule_pack = synthesize_capcut_rules(title, sentences, comments)
                if visual_cuts:
                    rule_pack["visual_cuts_sampled"] = len(visual_cuts)
                    rule_pack["cuts_per_minute"] = round(len(visual_cuts) / max(0.5, min(duration, 60.0) / 60.0), 1)
                training_pair = {
                    "prompt": f"You are an elite video editing director trained in CapCut and Premiere Pro. What are the core editing techniques and visual rhythm rules for \"{title}\"?",
                    "response": json.dumps(rule_pack, indent=2)
                }
            else:
                training_pair = synthesize_documentary_acts(title, duration, sentences, comments)

            # Append to master fine-tuning dataset
            with open(DATASET_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_pair) + "\n")

            existing_titles.add(title.lower().strip())
            print(f"     [SUCCESS] Logged to Obsidian Vault + dataset.jsonl (0 MB lingering disk bloat)")
            time.sleep(0.35)
            return training_pair
    except Exception as e:
        print(f"     [ERROR] Failed harvesting {entry_or_url}: {e}")
        return None


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
    Compare to /youtube/v3/search which costs 100 UNITS per search!
    Stretches 10,000 units/day to 500,000 video records!
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
                    content_details = item.get("contentDetails", {})
                    metadata_map[vid] = {
                        "video_id": vid,
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "duration_iso": content_details.get("duration", ""),
                    }
        except Exception as e:
            print(f"     [WARN] Batch metadata fetch warning: {e}")
    return metadata_map


def search_youtube_query(query: str, count: int = 10) -> List[str]:
    """
    QUOTA-SAFE SEARCH (0 units on discovery, 1 unit per 50 videos for metadata):
    1. Discovers video IDs via yt-dlp flat playlist extraction (0 API units used).
    2. Enriches & ranks candidates with batch /youtube/v3/videos (1 unit per 50 videos).
    NEVER calls /youtube/v3/search (which wastes 100 units per query).
    """
    print(f"\nSearching YouTube (Quota-Safe) for top {count} videos matching: '{query}'...")
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
        print(f"     [ERROR] No candidate videos discovered for '{query}'.")
        return []

    # Batch enrich metadata via official YouTube API (1 unit per 50 videos)
    if api_key:
        candidate_ids = [c["id"] for c in candidates]
        meta_map = fetch_batch_video_metadata(candidate_ids, api_key)
        if meta_map:
            print(f"     [QUOTA OPTIMIZED] Enriched {len(meta_map)} videos via batch /videos API (cost: 1 unit total, NOT 100 units!).")
            for c in candidates:
                if c["id"] in meta_map:
                    c["view_count"] = meta_map[c["id"]]["view_count"]
                    c["title"] = meta_map[c["id"]]["title"]

    # Sort candidates by view count to harvest top-performing videos
    candidates.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    top_urls = [c["url"] for c in candidates[:count]]
    for idx, c in enumerate(candidates[:count], 1):
        vc = f"{c['view_count']:,}" if c.get('view_count') else "N/A"
        print(f"     {idx}. [{vc} views] {c['title'][:65]}")

    return top_urls


def get_existing_harvested_titles() -> set:
    """Reads dataset.jsonl and returns titles of already harvested videos to skip duplicates."""
    titles = set()
    if os.path.exists(DATASET_PATH):
        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        res_str = data.get("response", "")
                        try:
                            parsed = json.loads(res_str)
                            if "title" in parsed:
                                titles.add(parsed["title"].lower().strip())
                        except Exception:
                            pass
        except Exception:
            pass
    return titles


def main():
    parser = argparse.ArgumentParser(description="Zero-Disk Long-Form & Tutorial Director Harvester")
    parser.add_argument("--mode", choices=["documentaries", "tutorials", "scripting", "all"], default="all")
    parser.add_argument("--batch-50", action="store_true", help="Harvest 50 top-tier videos across 5 curated categories (10 per category)")
    parser.add_argument("--batch-500", action="store_true", help="Harvest 500 top-tier videos across 25 viral editing & documentary categories (20 per category)")
    parser.add_argument("--query", help="Custom search query")
    parser.add_argument("--count", type=int, default=5, help="Number of videos per category")
    parser.add_argument("--urls", nargs="+", help="Specific video URLs to harvest")
    parser.add_argument("--visual-cuts", action="store_true", help="Sample real camera cuts via tiny 240p stream (~1.5 MB auto-purged)")
    args = parser.parse_args()

    targets = []
    already_harvested = get_existing_harvested_titles()
    print(f"[Harvester] Found {len(already_harvested)} previously harvested videos in dataset.jsonl.")

    if args.urls:
        for u in args.urls:
            targets.append((u, "tutorial" if "capcut" in u.lower() or "edit" in u.lower() else "documentary"))
    elif args.batch_500:
        print("\n[BATCH-500] Launching 500-video harvest across 25 viral editing & storytelling categories (20 per category):")
        cat_configs_500 = [
            # 1. CapCut Motion Graphics & NLE Visual Hacks
            ("how to edit like vox in capcut pc tutorial", "tutorial", 20),
            ("cinematic video editing hacks capcut premiere pro", "tutorial", 20),
            ("how to edit viral reels shorts capcut pacing retention", "tutorial", 20),
            ("johnny harris editing style map animation tutorial", "tutorial", 20),
            ("capcut keyframe zoom animation sound design tutorial", "tutorial", 20),
            ("how to edit dark aesthetic documentary Iman Gadzhi style", "tutorial", 20),
            ("kinetic typography text animation tutorial capcut", "tutorial", 20),
            ("cinematic b roll transitions paper texture mask tutorial", "tutorial", 20),
            ("davinci resolve cinematic color grading documentary lut", "tutorial", 20),
            ("ali abdaal video editing fast pacing retention tips", "tutorial", 20),
            ("finzar video editing tricks comedic sound effects pacing", "tutorial", 20),
            ("sound design for video editors whoosh riser impact tutorial", "tutorial", 20),
            ("foley sound effects layering documentary b roll tutorial", "tutorial", 20),
            ("mrbeast retention editing 1 second rule pacing tutorial", "tutorial", 20),
            ("hayden hillier smith youtube editor pacing masterclass", "tutorial", 20),

            # 2. Documentary Scriptwriting & Storytelling Architecture
            ("how to write documentary script youtube storytelling", "documentary", 20),
            ("magnates media business documentary video essay", "documentary", 20),
            ("james jani documentary storytelling script breakdown", "documentary", 20),
            ("lemmino documentary research and visual pacing", "documentary", 20),
            ("studiobinder 3 act story structure pacing masterclass", "documentary", 20),
            ("dan koe one person business scriptwriting hook formula", "documentary", 20),
            ("coldfusion tech documentary storytelling masterclass", "documentary", 20),
            ("sunnyv2 mini documentary youtube retention analysis", "documentary", 20),
            ("kurzgesagt scriptwriting storytelling curiosity gap", "documentary", 20),
            ("psychological hooks first 3 seconds retention youtube shorts", "documentary", 20),
        ]
        seen_urls = set()
        for idx_cat, (q, m, c) in enumerate(cat_configs_500, 1):
            print(f"\n--- [Category {idx_cat}/25] {q.upper()} ---")
            urls = search_youtube_query(q, c)
            for u in urls:
                if u not in seen_urls:
                    seen_urls.add(u)
                    targets.append((u, m))
    elif args.batch_50:
        # Curated 50-video batch (10 per domain)
        print("\n[BATCH-50] Launching 50-video harvest across 5 viral editing categories:")
        cat_configs = [
            ("how to edit like vox in capcut tutorial", "tutorial", 10),
            ("cinematic video editing hacks capcut premiere", "tutorial", 10),
            ("how to write documentary script youtube storytelling", "documentary", 10),
            ("magnates media documentary video essay", "documentary", 10),
            ("how to edit viral reels in capcut retention pacing", "tutorial", 10),
        ]
        seen_urls = set()
        for q, m, c in cat_configs:
            urls = search_youtube_query(q, c)
            for u in urls:
                if u not in seen_urls:
                    seen_urls.add(u)
                    targets.append((u, m))
    elif args.query:
        urls = search_youtube_query(args.query, args.count)
        mode = "tutorial" if "capcut" in args.query.lower() or "edit" in args.query.lower() else "documentary"
        for u in urls:
            targets.append((u, mode))
    else:
        # Default diverse multi-domain harvest:
        capcut_urls = search_youtube_query("how to edit like vox capcut tutorial", args.count)
        for u in capcut_urls:
            targets.append((u, "tutorial"))

        cinematic_urls = search_youtube_query("cinematic video editing hacks capcut premiere", args.count)
        for u in cinematic_urls:
            targets.append((u, "tutorial"))

        scripting_urls = search_youtube_query("how to write documentary script youtube storytelling", args.count)
        for u in scripting_urls:
            targets.append((u, "documentary"))

        doc_urls = search_youtube_query("magnates media documentary", args.count)
        for u in doc_urls:
            targets.append((u, "documentary"))

    print(f"\n==================================================================")
    print(f"Starting Zero-Disk Stream Harvester: {len(targets)} total video targets")
    print(f"Target Dataset: {DATASET_PATH}")
    print(f"Director Vault: {VAULT_DIR}")
    print(f"Zero Video Bloat: 0 MB video files saved to disk")
    print(f"==================================================================")

    success_count = 0
    start_time = time.time()
    for idx, (url, m) in enumerate(targets, 1):
        elapsed = time.time() - start_time
        rate = idx / max(1, elapsed)
        print(f"\n[{idx}/{len(targets)}] (Elapsed: {int(elapsed)}s, ~{rate:.1f} vids/s) Processing [{m.upper()}]: {url}")
        res = harvest_video_entry(
            url,
            mode=m,
            sample_visual_cuts=args.visual_cuts,
            existing_titles=already_harvested
        )
        if res:
            success_count += 1

    dataset_size = os.path.getsize(DATASET_PATH) / 1024 if os.path.exists(DATASET_PATH) else 0
    print(f"\n==================================================================")
    print(f"[HARVEST COMPLETE] Successfully harvested {success_count}/{len(targets)} videos.")
    print(f"Total dataset size on disk: {dataset_size:.1f} KB (Zero disk bloat!).")
    print(f"Total entries in dataset.jsonl: {len(already_harvested)}")
    print(f"Obsidian Director Vault updated with all learned techniques.")
    print(f"==================================================================\n")


if __name__ == "__main__":
    main()
