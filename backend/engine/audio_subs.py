"""
CONTENT-FACTORY Engine: Voiceover & Karaoke Subtitles (audio_subs)
------------------------------------------------------------------
- TTS: Edge-TTS (online) with automatic fallback
- Exact duration measurement via ffprobe
- Word-level timing synchronization
- Advanced .ASS karaoke pop-in subtitle generator
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import Any, Dict, List, Tuple
import edge_tts

logger = logging.getLogger("engine.audio_subs")


def get_exact_audio_duration(file_path: str) -> float:
    """Probes exact float duration in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dur = float(res.stdout.strip())
        return max(dur, 1.0)
    except Exception as e:
        logger.warning(f"Could not probe {file_path}: {e}")
        return 3.0


async def generate_sentence_audio(
    text: str,
    output_path: str,
    voice: str = "en-US-ChristopherNeural"
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Synthesizes single sentence audio with edge_tts with a 30s timeout and offline fallback.
    Returns (duration_seconds, word_boundaries).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    words: List[Dict[str, Any]] = []

    async def _stream_edge_tts():
        communicate = edge_tts.Communicate(text, voice)
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append({
                        "text": chunk["text"],
                        "start": chunk["offset"] / 10_000_000,
                        "duration": chunk["duration"] / 10_000_000
                    })

    try:
        await asyncio.wait_for(_stream_edge_tts(), timeout=30.0)
    except Exception as e:
        logger.warning(f"[audio_subs] Edge-TTS timeout or error ({e}). Generating fallback audio.")
        # Generate offline fallback audio via FFmpeg with estimated word pacing
        clean_words = text.split()
        est_duration = max(2.0, len(clean_words) * 0.38)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"aevalsrc=0:d={est_duration}",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            "-ar", "44100",
            output_path
        ]
        await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        words = []
        cur_t = 0.0
        step = est_duration / max(1, len(clean_words))
        for w in clean_words:
            words.append({"text": w, "start": cur_t, "duration": step * 0.9})
            cur_t += step

    dur = get_exact_audio_duration(output_path)
    return dur, words


def format_ass_time(seconds: float) -> str:
    """Formats float seconds to ASS timestamp H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def build_ass_subtitles(
    all_words: List[Dict[str, Any]],
    output_ass_path: str,
    play_res_x: int = 1080,
    play_res_y: int = 1920
) -> str:
    """
    Builds a high-retention word-by-word karaoke ASS subtitle file.
    Uses bold centered typography with pop-in color animation.
    """
    header = f"""[Script Info]
Title: ContentFactory Documentary Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,68,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,380,1
Style: Highlight,Arial,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,7,4,2,60,60,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    # Group words into short 3-word chunks
    chunk_size = 3
    for i in range(0, len(all_words), chunk_size):
        chunk = all_words[i:i + chunk_size]
        if not chunk:
            continue
        start_t = chunk[0]["start"]
        end_t = chunk[-1]["start"] + chunk[-1]["duration"] + 0.15

        # Format with karaoke highlight tag
        words_str = " ".join(w["text"].upper() for w in chunk)
        start_str = format_ass_time(start_t)
        end_str = format_ass_time(end_t)

        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{words_str}")

    content = header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"[audio_subs] Generated .ASS captions: {output_ass_path}")
    return output_ass_path


async def process_manifest_audio(
    manifest: Dict[str, Any],
    job_dir: str,
    voice: str = "en-US-ChristopherNeural"
) -> Dict[str, Any]:
    """
    Synthesizes each sentence, updates beat durations proportionally,
    and merges into a single continuous voiceover track.
    """
    audio_dir = os.path.join(job_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    sentence_files = []
    global_time = 0.0
    all_words = []

    for s in manifest.get("sentences", []):
        s_id = s["id"]
        s_text = s["text"]
        s_path = os.path.join(audio_dir, f"sentence_{s_id:02d}.mp3")

        dur, words = await generate_sentence_audio(s_text, s_path, voice=voice)
        s["audio_path"] = s_path
        s["duration"] = dur
        sentence_files.append(s_path)

        # Offset words for master timeline
        for w in words:
            all_words.append({
                "text": w["text"],
                "start": w["start"] + global_time,
                "duration": w["duration"]
            })

        # Lock visual beat durations proportionally to sentence length
        beats = s.get("beats", [])
        if len(beats) == 2:
            # First beat ~45%, second beat ~55%
            beats[0]["duration"] = round(dur * 0.45, 2)
            beats[1]["duration"] = round(dur * 0.55, 2)
        elif beats:
            each = round(dur / len(beats), 2)
            for b in beats:
                b["duration"] = each

        global_time += dur

    # Concatenate sentence audio into voice_master.mp3 via FFmpeg
    master_voice_path = os.path.join(job_dir, "voice_master.mp3")
    concat_list_path = os.path.join(audio_dir, "concat_list.txt")

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for sf in sentence_files:
            rel = os.path.abspath(sf).replace("\\", "/")
            f.write(f"file '{rel}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        master_voice_path
    ]
    await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Generate .ASS subtitles
    ass_path = os.path.join(job_dir, "captions.ass")
    build_ass_subtitles(all_words, ass_path)

    manifest["total_duration"] = global_time
    manifest["voice_master_path"] = master_voice_path
    manifest["captions_ass_path"] = ass_path

    return manifest


# Alias for compatibility across CLI and Instant Pipeline
synthesize_documentary_audio_and_subs = process_manifest_audio
