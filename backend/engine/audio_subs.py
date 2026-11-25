"""
CONTENT-FACTORY Engine: Voiceover, Broadcast Mastering & Active-Word Subtitles (audio_subs)
-------------------------------------------------------------------------------------------
- 3-Tier $0 Voice Stack:
  1. Kokoro-82M (`kokoro-onnx`) local CPU offline narrator (weights in `C:\\models\\kokoro\\`)
  2. OpenRouter `:free` TTS (`fish-audio/s2.1-pro-free:free` when discovered & within quota)
  3. Upgraded Edge-TTS Multilingual Neural voices (`en-US-AndrewMultilingualNeural`,
     `en-US-BrianMultilingualNeural`, `en-US-AvaMultilingualNeural`)
- Broadcast Vocal Mastering FFmpeg Chain (80Hz highpass, 120Hz warmth, 3.2kHz presence,
  3:1 dynamic compressor, -14 LUFS loudness normalization)
- Natural micro-pauses (0.25s between beats, 0.45s dramatic silence before climax)
- Active-Word Pop-In Karaoke `.ASS` Subtitle Generator using bundled `Montserrat Black`
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
import edge_tts

logger = logging.getLogger("engine.audio_subs")

KOKORO_MODELS_DIR = r"C:\models\kokoro"
FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts"))

BROADCAST_VOCAL_MASTER_AF = (
    "highpass=f=80,"
    "equalizer=f=120:width_type=o:width=1:g=3,"
    "equalizer=f=3200:width_type=o:width=1.5:g=2.5,"
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=80,"
    "loudnorm=I=-14:TP=-1.5:LRA=9"
)

LEGACY_EDGE_VOICE_UPGRADES: Dict[str, str] = {
    "en-US-ChristopherNeural": "en-US-AndrewMultilingualNeural",
    "en-US-AriaNeural": "en-US-AvaMultilingualNeural",
    "en-US-GuyNeural": "en-US-BrianMultilingualNeural",
    "en-US-AndrewNeural": "en-US-AndrewMultilingualNeural",
}

KOKORO_VOICE_MAP: Dict[str, str] = {
    "am_michael": "en-US-AndrewMultilingualNeural",
    "am_adam": "en-US-BrianMultilingualNeural",
    "af_bella": "en-US-AvaMultilingualNeural",
    "bm_george": "en-GB-RyanNeural",
}


def upgrade_legacy_edge_voice(voice: str) -> str:
    """
    Upgrades legacy robotic Edge-TTS voices (`ChristopherNeural`, `AriaNeural`)
    to expressive Multilingual Neural voices (`AndrewMultilingualNeural`, `AvaMultilingualNeural`).
    """
    v = (voice or "en-US-AndrewMultilingualNeural").strip()
    if v in LEGACY_EDGE_VOICE_UPGRADES:
        return LEGACY_EDGE_VOICE_UPGRADES[v]
    if v in KOKORO_VOICE_MAP:
        return KOKORO_VOICE_MAP[v]
    return v


_KOKORO_INSTANCE: Any = None
_KOKORO_MODEL_LOADED_PATH: Optional[str] = None


def is_explicit_kokoro_voice(voice: Optional[str]) -> bool:
    """Returns True when the caller explicitly requested an offline Kokoro voice ID (e.g. am_michael)."""
    v = (voice or "").strip().lower()
    return v in KOKORO_VOICE_MAP or v.startswith(("am_", "af_", "bm_", "bf_"))


def resolve_kokoro_model_paths() -> Optional[Tuple[str, str]]:
    """
    Resolves local Kokoro-82M ONNX weights in C:\\models\\kokoro\\, preferring the compact
    quantized `kokoro-v1.0.int8.onnx` (~88 MB) for 16 GB RAM laptops, or `kokoro-v1.0.onnx`.
    """
    voices_path = os.path.join(KOKORO_MODELS_DIR, "voices-v1.0.bin")
    if not os.path.exists(voices_path):
        return None
    for candidate in ("kokoro-v1.0.int8.onnx", "kokoro-v1.0.onnx"):
        onnx_path = os.path.join(KOKORO_MODELS_DIR, candidate)
        if os.path.exists(onnx_path) and os.path.getsize(onnx_path) > 10 * 1024 * 1024:
            return onnx_path, voices_path
    return None


def try_kokoro_local_tts(
    text: str,
    output_path: str,
    voice: str = "am_michael"
) -> Optional[Tuple[float, List[Dict[str, Any]]]]:
    """
    Local CPU Offline Narrator (`kokoro-onnx` with singleton cached session on `C:\\models\\kokoro\\`).
    Used when offline, when Edge-TTS is unreachable, or when `am_*` voice is explicitly chosen.
    """
    global _KOKORO_INSTANCE, _KOKORO_MODEL_LOADED_PATH
    resolved = resolve_kokoro_model_paths()
    if not resolved:
        return None
    onnx_path, voices_path = resolved

    try:
        import soundfile as sf
        from kokoro_onnx import Kokoro

        if _KOKORO_INSTANCE is None or _KOKORO_MODEL_LOADED_PATH != onnx_path:
            _KOKORO_INSTANCE = Kokoro(onnx_path, voices_path)
            _KOKORO_MODEL_LOADED_PATH = onnx_path

        kokoro_voice = voice if is_explicit_kokoro_voice(voice) else "am_michael"
        samples, sample_rate = _KOKORO_INSTANCE.create(text, voice=kokoro_voice, speed=1.0, lang="en-us")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wav_tmp = output_path + ".kokoro.wav"
        sf.write(wav_tmp, samples, sample_rate)
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_tmp, "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
        if os.path.exists(wav_tmp):
            try:
                os.remove(wav_tmp)
            except OSError:
                pass
        dur = get_exact_audio_duration(output_path)
        clean_words = text.split()
        words: List[Dict[str, Any]] = []
        cur_t = 0.0
        step = dur / max(1, len(clean_words))
        for w in clean_words:
            words.append({"text": w, "start": round(cur_t, 3), "duration": round(step * 0.92, 3)})
            cur_t += step
        logger.info(f"[audio_subs] Generated Kokoro-82M local CPU voiceover ({kokoro_voice}) -> {output_path}")
        return dur, words
    except Exception as e:
        logger.debug(f"[audio_subs] Kokoro local TTS unavailable ({e}), falling back.")
        return None


def resolve_music_sfx_stage() -> Dict[str, Any]:
    """
    Stage 5 Hybrid Router (Music & SFX):
    Checks `openrouter_discovery.get_free_models_for("audio")`.
    When empty (no free OpenRouter audio models exist), immediately skips OpenRouter (0 API calls)
    and uses local BGM/SFX library (`whoosh.wav`, `thud.wav`, `click.wav`, `riser.wav`) + FFmpeg -14 LUFS ducking mix.
    """
    from backend.engine import openrouter_discovery
    free_audio_models = openrouter_discovery.get_free_models_for("audio")
    if not free_audio_models:
        return {
            "stage": "audio",
            "status": "auto_skip_to_local",
            "free_models_available": [],
            "openrouter_calls_made": 0,
            "active_engine": "local_bgm_sfx_and_ffmpeg_lufs_ducking",
        }
    return {
        "stage": "audio",
        "status": "openrouter_free_available",
        "free_models_available": free_audio_models,
        "openrouter_calls_made": 0,
        "active_engine": free_audio_models[0],
    }


def try_openrouter_free_tts(
    text: str,
    output_path: str,
    timeout: float = 20.0,
) -> bool:
    """
    Stage 4 Optional / Fallback Hybrid TTS (`speech` via `/api/v1/audio/speech`):
    Queries discovered strictly-free speech models (`fish-audio/s2.1-pro-free:free`,
    `heygen/heygen-voice-1-turbo:free`) when explicitly enabled or if Edge-TTS fails.
    Immediately returns False (0 calls) if on cooldown or no free speech model is available.
    """
    from backend.engine import openrouter_discovery

    if openrouter_discovery.is_openrouter_on_cooldown():
        return False

    api_key = openrouter_discovery.resolve_openrouter_api_key()
    if not api_key:
        return False

    speech_models = openrouter_discovery.get_free_models_for("speech")
    if not speech_models:
        return False

    model_id = speech_models[0]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    payload = {
        "model": model_id,
        "input": text.strip()[:600],
        "voice": "alloy",
        "response_format": "mp3",
    }

    req = urllib.request.Request(
        openrouter_discovery.OPENROUTER_SPEECH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "CONTENT-FACTORY Studio TTS",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            audio_bytes = resp.read()
            if len(audio_bytes) > 1000:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"[audio_subs] Generated $0 OpenRouter speech ({model_id}) -> {output_path}")
                return True
    except urllib.error.HTTPError as he:
        if he.code in (402, 429):
            openrouter_discovery.record_openrouter_status(he.code, f"Speech endpoint HTTP {he.code}")
    except Exception as e:
        logger.debug(f"[audio_subs] OpenRouter free speech skipped/fallback to Edge-TTS: {e}")
    return False


def get_contrasting_archival_voice(primary_voice: str) -> str:
    """Returns a distinct secondary voice for historical quotes, memos, and intercepted records."""
    upgraded = upgrade_legacy_edge_voice(primary_voice)
    if any(fv.lower() in upgraded.lower() for fv in ["aria", "jenny", "michelle", "ava"]):
        return "en-US-AndrewMultilingualNeural"
    elif any(mv.lower() in upgraded.lower() for mv in ["christopher", "andrew"]):
        return "en-US-BrianMultilingualNeural"
    else:
        return "en-US-AndrewMultilingualNeural"


async def apply_archival_audio_filter(input_path: str, output_path: str) -> bool:
    """
    Passes audio through vintage radio/tape bandpass filter (highpass 300Hz, lowpass 3200Hz)
    with subtle gain leveling to give authentic intercepted/declassified recording texture.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", "highpass=f=300,lowpass=f=3200,volume=1.25",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        output_path
    ]
    def _run():
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)

    try:
        res = await asyncio.to_thread(_run)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.warning(f"[audio_subs] Archival audio filter failed: {e}")
        return False


async def apply_broadcast_vocal_mastering(input_path: str, output_path: str) -> bool:
    """
    Pipes master narration through the Broadcast Vocal Mastering FFmpeg Chain:
    - 80Hz highpass (strips muddy low rumble)
    - 120Hz +3dB warmth boost (trailer chest resonance)
    - 3200Hz +2.5dB presence boost (cuts cleanly through background score)
    - 3:1 dynamic compressor (-18dB threshold, 5ms attack, 80ms release)
    - EBU R128 loudness normalization (-14 LUFS, -1.5 dBTP)
    """
    if not os.path.exists(input_path):
        return False
    tmp_master = output_path + ".mastered.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", BROADCAST_VOCAL_MASTER_AF,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        tmp_master,
    ]
    def _run():
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)

    try:
        res = await asyncio.to_thread(_run)
        if res.returncode == 0 and os.path.exists(tmp_master) and os.path.getsize(tmp_master) > 500:
            os.replace(tmp_master, output_path)
            logger.info(f"[audio_subs] Broadcast vocal mastering (-14 LUFS + EQ + compressor) applied -> {output_path}")
            return True
    except Exception as e:
        logger.warning(f"[audio_subs] Broadcast vocal mastering skipped ({e})")
    finally:
        if os.path.exists(tmp_master):
            try:
                os.remove(tmp_master)
            except OSError:
                pass
    return False


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
        return max(dur, 0.5)
    except Exception as e:
        logger.warning(f"Could not probe {file_path}: {e}")
        return 3.0


async def generate_sentence_audio(
    text: str,
    output_path: str,
    voice: str = "en-US-AndrewMultilingualNeural",
    pause_before: float = 0.0,
    pause_after: float = 0.25,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    3-Tier $0 Sentence Audio Synthesizer:
    1. Online Default: Upgraded Multilingual Edge-TTS (`en-US-AndrewMultilingualNeural`, `AvaMultilingualNeural`,
       `BrianMultilingualNeural`) with exact millisecond `WordBoundary` events for active-word captions.
    2. Offline / Explicit Local Narrator: Cached `Kokoro-82M` int8 (`C:\\models\\kokoro\\`) when offline,
       when `am_*` voice is explicitly chosen, or if Edge-TTS fails.
    3. OpenRouter `:free` TTS + deterministic FFmpeg fallback.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    words: List[Dict[str, Any]] = []
    force_offline = os.environ.get("FORCE_OFFLINE", "false").lower() == "true"

    # Only run Kokoro first if the user explicitly picked an offline Kokoro voice OR force_offline is enabled
    if force_offline or is_explicit_kokoro_voice(voice):
        kokoro_res = await asyncio.to_thread(try_kokoro_local_tts, text, output_path, voice)
        if kokoro_res is not None:
            _, words = kokoro_res
            for w in words:
                w["start"] = round(w["start"] + pause_before, 3)

    if not words and not (os.path.exists(output_path) and os.path.getsize(output_path) > 500):
        # Tier 1 Online: Upgraded Edge-TTS Multilingual Neural Voice (exact WordBoundary sync)
        effective_voice = upgrade_legacy_edge_voice(voice)

        async def _stream_edge_tts():
            last_exc = None
            for attempt in range(3):
                words.clear()
                try:
                    communicate = edge_tts.Communicate(text, effective_voice)
                    audio_bytes_written = 0
                    with open(output_path, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                                audio_bytes_written += len(chunk["data"])
                            elif chunk["type"] == "WordBoundary":
                                words.append({
                                    "text": chunk["text"],
                                    "start": (chunk["offset"] / 10_000_000) + pause_before,
                                    "duration": chunk["duration"] / 10_000_000
                                })
                    if audio_bytes_written > 500:
                        return
                except Exception as exc:
                    last_exc = exc
                    await asyncio.sleep(0.6 * (attempt + 1))
            if last_exc:
                raise last_exc
            raise RuntimeError("No audio bytes received from Edge-TTS")

        try:
            await asyncio.wait_for(_stream_edge_tts(), timeout=30.0)
        except Exception as e:
            logger.warning(f"[audio_subs] Edge-TTS error ({e}), trying offline Kokoro-82M -> OpenRouter :free TTS.")
            kokoro_fb = await asyncio.to_thread(try_kokoro_local_tts, text, output_path, "am_michael")
            if kokoro_fb is not None:
                _, words = kokoro_fb
                for w in words:
                    w["start"] = round(w["start"] + pause_before, 3)
            else:
                or_ok = await asyncio.to_thread(try_openrouter_free_tts, text, output_path)
                clean_words = text.split()
                if or_ok and os.path.exists(output_path):
                    est_duration = get_exact_audio_duration(output_path)
                else:
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
                cur_t = pause_before
                step = est_duration / max(1, len(clean_words))
                for w in clean_words:
                    words.append({"text": w, "start": cur_t, "duration": step * 0.9})
                    cur_t += step

    # Apply pre-sentence comedic/dramatic dead-air delay and post-sentence micro-pause pad
    af_filters = []
    if pause_before > 0:
        delay_ms = int(pause_before * 1000)
        af_filters.append(f"adelay={delay_ms}|{delay_ms}")
    if pause_after > 0:
        af_filters.append(f"apad=pad_dur={round(pause_after, 3)}")

    if af_filters and os.path.exists(output_path):
        padded_tmp = output_path + ".padded.mp3"
        cmd_pad = [
            "ffmpeg", "-y", "-i", output_path,
            "-af", ",".join(af_filters),
            "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
            padded_tmp
        ]
        await asyncio.to_thread(subprocess.run, cmd_pad, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(padded_tmp) and os.path.getsize(padded_tmp) > 0:
            os.replace(padded_tmp, output_path)

    dur = get_exact_audio_duration(output_path)
    # Fallback word boundaries if TTS stream returned audio without WordBoundary events
    if not words:
        clean_words = text.split()
        spoken_dur = max(0.5, dur - pause_before - pause_after)
        step = spoken_dur / max(1, len(clean_words))
        cur_t = pause_before
        for w in clean_words:
            words.append({"text": w, "start": round(cur_t, 3), "duration": round(step * 0.9, 3)})
            cur_t += step

    return dur, words


def format_ass_time(seconds: float) -> str:
    """Formats float seconds to ASS timestamp H:MM:SS.cs"""
    seconds = max(0.0, float(seconds))
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
    play_res_y: int = 1920,
    margin_v: int = 380,
    font_size: int = 70
) -> str:
    """
    Builds a trailer-grade active-word pop-in karaoke .ASS subtitle file.
    - Uses bundled `Montserrat Black` typography (zero Arial).
    - Groups words into 3-word phrases and emits per-word Dialogue events where the
      currently spoken word pops in with a 100ms scale bounce
      (`\\fscx88\\fscy88\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)`)
      and switches to high-contrast gold/cyan (`&H0000D4FF&`) while neighboring words stay crisp white.
    """
    highlight_size = font_size + 4
    header = f"""[Script Info]
Title: ContentFactory Studio Active-Word Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat Black,{font_size},&H00FFFFFF,&H0000D4FF,&H00080A10,&H96000000,-1,0,0,0,100,100,1,0,1,6,4,2,70,70,{margin_v},1
Style: Highlight,Montserrat Black,{highlight_size},&H0000D4FF,&H00FFFFFF,&H00080A10,&H96000000,-1,0,0,0,105,105,1,0,1,7,4,2,70,70,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: List[str] = []
    chunk_size = 3
    pop_tag = r"\fscx88\fscy88\t(0,90,\fscx106\fscy106)\t(90,150,\fscx100\fscy100)"

    for i in range(0, len(all_words), chunk_size):
        chunk = all_words[i:i + chunk_size]
        if not chunk:
            continue

        chunk_end_t = chunk[-1]["start"] + max(0.18, chunk[-1]["duration"]) + 0.12
        if i + chunk_size < len(all_words):
            next_chunk_start = all_words[i + chunk_size]["start"]
            chunk_end_t = min(chunk_end_t, next_chunk_start)

        for active_idx, w in enumerate(chunk):
            w_start = float(w["start"])
            if active_idx + 1 < len(chunk):
                w_end = max(w_start + 0.12, float(chunk[active_idx + 1]["start"]))
            else:
                w_end = max(w_start + 0.18, chunk_end_t)

            start_str = format_ass_time(w_start)
            end_str = format_ass_time(w_end)

            rendered_tokens: List[str] = []
            for token_idx, token_obj in enumerate(chunk):
                raw_word = str(token_obj["text"]).upper().replace("{", "").replace("}", "")
                if token_idx == active_idx:
                    rendered_tokens.append(
                        f"{{{pop_tag}\\c&H0000D4FF&}}{raw_word}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}"
                    )
                else:
                    rendered_tokens.append(f"{{\\c&H00FFFFFF&}}{raw_word}")

            line_text = " ".join(rendered_tokens)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    content = header + "\n".join(events) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"[audio_subs] Generated active-word pop-in .ASS captions: {output_ass_path}")
    return output_ass_path


async def process_manifest_audio(
    manifest: Dict[str, Any],
    job_dir: str,
    voice: str = "en-US-AndrewMultilingualNeural"
) -> Dict[str, Any]:
    """
    Synthesizes each sentence with upgraded 3-tier voices and natural micro-pauses
    (0.25s between beats, 0.45s dramatic silence before the climax sentence),
    concatenates into `voice_master.mp3`, and runs the Broadcast Vocal Mastering FFmpeg Chain.
    """
    audio_dir = os.path.join(job_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    primary_voice = upgrade_legacy_edge_voice(voice)
    sentences = manifest.get("sentences", [])
    total_sentences = len(sentences)
    climax_sentence_idx = max(1, total_sentences - 2) if total_sentences >= 4 else -1

    sentence_files = []
    global_time = 0.0
    all_words = []

    for idx, s in enumerate(sentences):
        s_id = s["id"]
        s_text = s["text"]
        s_path = os.path.join(audio_dir, f"sentence_{s_id:02d}.mp3")

        # Natural micro-pause: 0.45s dramatic silence right before the climax sentence, 0.25s between normal sentences
        pause_before = float(s.get("pause_before", 0.0) or 0.0)
        if idx == climax_sentence_idx:
            pause_before = max(pause_before, 0.45)
            s["is_climax_entry"] = True
        pause_after = 0.25 if idx < total_sentences - 1 else 0.15

        beats = s.get("beats", [])
        is_archival_beat = any(
            b.get("type") in ("declassified_scan", "quote_box") or
            b.get("template") == "quote_box" or
            b.get("voice_filter") == "archival"
            for b in beats
        )

        if is_archival_beat:
            active_voice = get_contrasting_archival_voice(primary_voice)
            raw_path = os.path.join(audio_dir, f"sentence_{s_id:02d}_raw.mp3")
            dur, words = await generate_sentence_audio(
                s_text, raw_path, voice=active_voice, pause_before=pause_before, pause_after=pause_after
            )
            filter_ok = await apply_archival_audio_filter(raw_path, s_path)
            if not filter_ok:
                s_path = raw_path
            else:
                dur = get_exact_audio_duration(s_path)
                try:
                    os.remove(raw_path)
                except Exception:
                    pass
            s["voice"] = active_voice
            s["voice_filter"] = "archival_bandpass"
        else:
            dur, words = await generate_sentence_audio(
                s_text, s_path, voice=primary_voice, pause_before=pause_before, pause_after=pause_after
            )
            s["voice"] = primary_voice

        s["audio_path"] = s_path
        s["duration"] = dur
        s["start_time"] = round(global_time, 3)
        sentence_files.append(s_path)

        for w in words:
            all_words.append({
                "text": w["text"],
                "start": round(w["start"] + global_time, 3),
                "duration": round(w["duration"], 3)
            })

        # Proportionally distribute sentence duration across its visual beats while respecting 3-act weights
        if len(beats) == 2:
            b0_w = float(beats[0].get("duration", 1.4))
            b1_w = float(beats[1].get("duration", 1.6))
            w_sum = max(0.2, b0_w + b1_w)
            beats[0]["duration"] = round(max(0.65, dur * (b0_w / w_sum)), 2)
            beats[1]["duration"] = round(max(0.65, dur - beats[0]["duration"]), 2)
        elif beats:
            each = round(max(0.65, dur / len(beats)), 2)
            for b in beats:
                b["duration"] = each

        global_time += dur

    # Concatenate sentence audio into voice_master.mp3 and apply Broadcast Vocal Mastering
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
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        master_voice_path
    ]
    await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Pipe voice_master.mp3 through the Broadcast Vocal Mastering FFmpeg Chain
    await apply_broadcast_vocal_mastering(master_voice_path, master_voice_path)

    # Generate active-word .ASS subtitles (scaled for aspect ratio)
    aspect_ratio = manifest.get("aspect_ratio", "9:16")
    ass_path = os.path.join(job_dir, "captions.ass")
    if aspect_ratio == "16:9":
        build_ass_subtitles(all_words, ass_path, play_res_x=1920, play_res_y=1080, margin_v=85, font_size=50)
    else:
        build_ass_subtitles(all_words, ass_path, play_res_x=1080, play_res_y=1920, margin_v=380, font_size=70)

    manifest["total_duration"] = round(global_time, 2)
    manifest["actual_duration"] = round(global_time, 2)
    manifest["voice_master_path"] = master_voice_path
    manifest["captions_ass_path"] = ass_path

    return manifest


# Alias for compatibility across CLI and Instant Pipeline
synthesize_documentary_audio_and_subs = process_manifest_audio
