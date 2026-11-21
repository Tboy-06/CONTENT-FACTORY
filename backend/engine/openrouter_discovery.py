"""
CONTENT-FACTORY Engine: Zero-Cost Dynamic OpenRouter Capability Discovery & Hybrid Fallback Router
--------------------------------------------------------------------------------------------------
Scans OpenRouter's live multimodal catalog (`GET https://openrouter.ai/api/v1/models?output_modalities=all`),
enforces a strict double-lock $0.00 guard (`is_strictly_free`), classifies discovered `:free` models across
all 6 video production stages (`text`, `vision`, `image`, `speech`, `audio`, `video`), and manages an automatic
402/429 circuit breaker so stages without free models or under rate-limit skip in 0ms to local engines.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("engine.openrouter_discovery")

_STATE_LOCK = threading.Lock()

OPENROUTER_CATALOG_URL = "https://openrouter.ai/api/v1/models?output_modalities=all"
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"
OPENROUTER_SPEECH_URL = "https://openrouter.ai/api/v1/audio/speech"

CATALOG_TTL_SECONDS = 6 * 3600  # 6 hours in-memory cache (0 MB disk bloat on D:\)
COOLDOWN_402_SECONDS = 15 * 60  # 15 minutes cooldown on HTTP 402 (daily free cap / payment required)
COOLDOWN_429_SECONDS = 60       # 60 seconds cooldown on HTTP 429 (per-minute rate limit)

# Background Harvester Guard: keep dataset_collector off the 50/day OpenRouter :free quota by default
ALLOW_HARVESTER_OPENROUTER_FREE = False

# Priority rankings per User A2 routing rules
TEXT_PRIORITY_ORDER = [
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "inclusionai/ling-3.2-flash:free",
    "baidu/ernie-5.5-flash-preview:free",
    "particle-ai/particle-1:free",
    "recursive/flint-v1.0:free",
    "liquid/lfm-3-1.7b:free",
]

VISION_PRIORITY_ORDER = [
    "nvidia/nemotron-3.5-super-vl:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.2-flash:free",
    "particle-ai/particle-1:free",
]

LOCAL_FALLBACK_ENGINES = {
    "text": "Local Spark-X2.5-4B (llama-server.exe) + Director Vault BM25 / SQLite memory",
    "vision": "Local FFmpeg keyframe/scene metrics + Faster-Whisper transcript -> Spark-X2.5-4B",
    "image": "Pollinations Flux (1080p $0 plates) + Pexels / yt-dlp B-roll in visual_cortex.py",
    "speech": "Local Edge-TTS (unlimited $0 neural voiceover + word timestamps) in audio_subs.py",
    "audio": "Local BGM/SFX library (whoosh.wav, thud.wav, click.wav) + FFmpeg -14 LUFS ducking mix",
    "video": "Local visual_cortex.py / free_visuals.py + 2-pass FFmpeg cosine zoompan / Depth Cortex + motion HUD cards",
}

# In-memory state (0 disk writes)
_CATALOG_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "raw_count": 0,
    "strictly_free_count": 0,
    "stages": {
        "text": [],
        "vision": [],
        "image": [],
        "speech": [],
        "audio": [],
        "video": [],
    },
    "models_by_id": {},
}

_CIRCUIT_BREAKER: Dict[str, Any] = {
    "cooldown_until": 0.0,
    "last_status_code": None,
    "last_reason": "",
    "triggered_at": None,
}

_QUOTA_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": None,
}


def _is_valid_key_string(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return False
    t = val.strip()
    if not t or "YOUR_KEY_HERE" in t or t == "sk-or-v1-...":
        return False
    return True


def resolve_openrouter_api_key() -> Optional[str]:
    """
    Dynamically resolves OPENROUTER_API_KEY without requiring a server restart.
    Checks:
      1. os.environ["OPENROUTER_API_KEY"]
      2. backend.config.get_settings().openrouter_api_key
      3. D:\\CONTENT-FACTORY\\.env and ~/.env
      4. C:\\Users\\User\\.gemini\\config\\plugins\\ruflow\\openrouter.config.json
    """
    env_val = os.environ.get("OPENROUTER_API_KEY")
    if _is_valid_key_string(env_val):
        return env_val.strip()

    try:
        from backend.config import get_settings
        cfg = get_settings()
        cfg_key = getattr(cfg, "openrouter_api_key", "")
        if _is_valid_key_string(cfg_key):
            return cfg_key.strip()
    except Exception:
        pass

    home = Path.home()
    project_root = Path(__file__).resolve().parent.parent.parent

    # Check .env files
    for env_path in (project_root / ".env", home / ".env"):
        try:
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line_s = line.strip()
                    if line_s.startswith("OPENROUTER_API_KEY="):
                        raw_v = line_s.split("=", 1)[1].strip().strip("'\"")
                        if _is_valid_key_string(raw_v):
                            return raw_v
        except Exception:
            pass

    # Check Antigravity Ruflo plugin openrouter.config.json
    plugin_cfg = home / ".gemini" / "config" / "plugins" / "ruflow" / "openrouter.config.json"
    try:
        if plugin_cfg.exists():
            data = json.loads(plugin_cfg.read_text(encoding="utf-8"))
            raw_v = (data.get("OPENROUTER_API_KEY") or data.get("apiKey") or "").strip()
            if _is_valid_key_string(raw_v):
                return raw_v
    except Exception:
        pass

    return None


def is_strictly_free(model_obj: Dict[str, Any]) -> bool:
    """
    STRICT ZERO-COST DOUBLE LOCK:
    1. Model ID MUST equal "openrouter/free" OR end with ":free" (rejects temporary $0 previews
       like `google/lyria-3-pro-preview` and dynamic paid routers like `openrouter/auto`).
    2. `pricing` dictionary MUST exist and have explicit `"prompt"` and `"completion"` values.
    3. Every numeric field in `pricing` (`prompt`, `completion`, `request`, `image`, `audio`,
       `internal_reasoning`, etc.) MUST parse to exactly `0.0` (rejects sentinel `"-1"` and any `> 0`).
    """
    if not isinstance(model_obj, dict):
        return False

    model_id = str(model_obj.get("id") or "").strip()
    if not model_id:
        return False

    if not (model_id == "openrouter/free" or model_id.endswith(":free")):
        return False

    pricing = model_obj.get("pricing")
    if not isinstance(pricing, dict) or not pricing:
        return False

    # prompt and completion must be explicitly present and equal to 0
    if pricing.get("prompt") is None or pricing.get("completion") is None:
        return False

    price_keys = set(pricing.keys()) | {
        "prompt", "completion", "request", "image", "audio", "internal_reasoning"
    }

    for k in price_keys:
        val = pricing.get(k)
        if val is None or val == "":
            if k in ("prompt", "completion"):
                return False
            continue
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return False
        if math.isnan(fval) or math.isinf(fval) or fval != 0.0:
            return False

    return True


def _sort_with_priority(model_ids: List[str], priority_order: List[str], keep_router_last: bool = True) -> List[str]:
    unique_ids = []
    seen = set()
    for mid in model_ids:
        if mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)

    has_free_router = "openrouter/free" in seen
    candidates = [m for m in unique_ids if m != "openrouter/free"]

    priority_rank = {mid: idx for idx, mid in enumerate(priority_order)}
    candidates.sort(key=lambda m: (priority_rank.get(m, 999), m))

    if has_free_router and keep_router_last:
        candidates.append("openrouter/free")
    elif has_free_router:
        candidates.insert(0, "openrouter/free")

    return candidates


def classify_catalog_into_stages(raw_models: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Filters `raw_models` through `is_strictly_free` and categorizes strictly-free models
    into the 6 Content Factory pipeline stages based on `architecture.input_modalities`
    and `architecture.output_modalities`.
    """
    stages: Dict[str, List[str]] = {
        "text": [],
        "vision": [],
        "image": [],
        "speech": [],
        "audio": [],
        "video": [],
    }

    for m in raw_models:
        if not is_strictly_free(m):
            continue

        mid = str(m["id"]).strip()
        arch = m.get("architecture") or {}
        in_mods = [str(x).lower() for x in (arch.get("input_modalities") or ["text"])]
        out_mods = [str(x).lower() for x in (arch.get("output_modalities") or ["text"])]

        # 1. Text stage (/api/v1/chat/completions)
        if "text" in out_mods:
            stages["text"].append(mid)

        # 2. Vision stage (image or video input -> text output)
        if ("image" in in_mods or "video" in in_mods) and "text" in out_mods:
            stages["vision"].append(mid)

        # 3. Image generation stage (/api/v1/images)
        if "image" in out_mods:
            stages["image"].append(mid)

        # 4. Speech / TTS stage (/api/v1/audio/speech)
        if "speech" in out_mods:
            stages["speech"].append(mid)

        # 5. Music & SFX stage (audio output)
        if "audio" in out_mods:
            stages["audio"].append(mid)

        # 6. Video generation stage (/api/v1/videos)
        if "video" in out_mods:
            stages["video"].append(mid)

    stages["text"] = _sort_with_priority(stages["text"], TEXT_PRIORITY_ORDER, keep_router_last=True)
    stages["vision"] = _sort_with_priority(stages["vision"], VISION_PRIORITY_ORDER, keep_router_last=True)
    stages["image"] = _sort_with_priority(stages["image"], [], keep_router_last=False)
    stages["speech"] = _sort_with_priority(stages["speech"], [
        "fish-audio/s2.1-pro-free:free",
        "heygen/heygen-voice-1-turbo:free",
    ], keep_router_last=False)
    stages["audio"] = _sort_with_priority(stages["audio"], [], keep_router_last=False)
    stages["video"] = _sort_with_priority(stages["video"], [], keep_router_last=False)

    return stages


def refresh_catalog_if_needed(force: bool = False, timeout: float = 12.0) -> Dict[str, Any]:
    """
    Fetches `GET https://openrouter.ai/api/v1/models?output_modalities=all` and caches
    the 6-stage capability map in memory for 6 hours.
    """
    now = time.time()
    if not force and _CATALOG_CACHE["timestamp"] > 0 and (now - _CATALOG_CACHE["timestamp"] < CATALOG_TTL_SECONDS):
        return _CATALOG_CACHE

    req = urllib.request.Request(
        OPENROUTER_CATALOG_URL,
        headers={
            "Accept": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "CONTENT-FACTORY Studio",
            "User-Agent": "ContentFactoryStudio/3.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            raw_models = payload.get("data") if isinstance(payload, dict) else []
            if not isinstance(raw_models, list):
                raw_models = []

            stages = classify_catalog_into_stages(raw_models)
            strictly_free_models = {
                str(m["id"]).strip(): m for m in raw_models if is_strictly_free(m)
            }

            _CATALOG_CACHE["timestamp"] = now
            _CATALOG_CACHE["raw_count"] = len(raw_models)
            _CATALOG_CACHE["strictly_free_count"] = len(strictly_free_models)
            _CATALOG_CACHE["stages"] = stages
            _CATALOG_CACHE["models_by_id"] = strictly_free_models

            logger.info(
                f"[OpenRouterDiscovery] Scanned {len(raw_models)} models -> "
                f"{len(strictly_free_models)} strictly-free ($0.00) models across stages: "
                f"text={len(stages['text'])}, vision={len(stages['vision'])}, "
                f"image={len(stages['image'])}, speech={len(stages['speech'])}, "
                f"audio={len(stages['audio'])}, video={len(stages['video'])}"
            )
    except Exception as e:
        logger.warning(f"[OpenRouterDiscovery] Could not refresh live catalog ({e}); using cached/fallback registry.")
        if _CATALOG_CACHE["timestamp"] == 0:
            # Safe strictly-free static bootstrap if offline at startup
            _CATALOG_CACHE["stages"] = {
                "text": [
                    "nvidia/nemotron-3.5-lightning:free",
                    "google/gemma-4-31b-it:free",
                    "openrouter/free",
                ],
                "vision": [
                    "nvidia/nemotron-3.5-super-vl:free",
                    "google/gemma-4-26b-a4b-it:free",
                    "openrouter/free",
                ],
                "image": [],
                "speech": [],
                "audio": [],
                "video": [],
            }

    return _CATALOG_CACHE


def get_free_models_for(capability: str, force_refresh: bool = False) -> List[str]:
    """
    Returns strictly-free ($0.00) OpenRouter model IDs for a given capability
    (`text`, `vision`, `image`, `speech`, `audio`, `video`).
    Returns `[]` immediately if OpenRouter is on circuit-breaker cooldown or no free model exists.
    """
    if is_openrouter_on_cooldown():
        return []
    cache = refresh_catalog_if_needed(force=force_refresh)
    stages = cache.get("stages") or {}
    return list(stages.get(capability.lower().strip(), []))


# ==============================================================================
# CIRCUIT BREAKER (HTTP 402 -> 15m Cooldown, HTTP 429 -> 60s Cooldown)
# ==============================================================================

def record_openrouter_status(status_code: int, reason: str = "") -> None:
    """
    Trips the circuit breaker when OpenRouter returns HTTP 402 (daily free quota reached / payment required)
    or HTTP 429 (per-minute rate limit).
    """
    now = time.time()
    with _STATE_LOCK:
        if status_code == 402:
            _CIRCUIT_BREAKER["cooldown_until"] = now + COOLDOWN_402_SECONDS
            _CIRCUIT_BREAKER["last_status_code"] = 402
            _CIRCUIT_BREAKER["last_reason"] = reason or "HTTP 402: Daily free cap exhausted or payment required (15m auto-skip)"
            _CIRCUIT_BREAKER["triggered_at"] = now
            logger.warning(f"[OpenRouterDiscovery] Circuit breaker tripped (402): auto-skipping to local engines for 15m.")
        elif status_code == 429:
            _CIRCUIT_BREAKER["cooldown_until"] = max(_CIRCUIT_BREAKER["cooldown_until"], now + COOLDOWN_429_SECONDS)
            _CIRCUIT_BREAKER["last_status_code"] = 429
            _CIRCUIT_BREAKER["last_reason"] = reason or "HTTP 429: Upstream free rate limit hit (60s auto-skip)"
            _CIRCUIT_BREAKER["triggered_at"] = now
            logger.warning(f"[OpenRouterDiscovery] Circuit breaker tripped (429): auto-skipping to local engines for 60s.")


def is_openrouter_on_cooldown() -> bool:
    """Returns True if the circuit breaker is currently active."""
    with _STATE_LOCK:
        return time.time() < float(_CIRCUIT_BREAKER.get("cooldown_until") or 0.0)


def reset_circuit_breaker() -> None:
    """Resets the circuit breaker state."""
    with _STATE_LOCK:
        _CIRCUIT_BREAKER["cooldown_until"] = 0.0
        _CIRCUIT_BREAKER["last_status_code"] = None
        _CIRCUIT_BREAKER["last_reason"] = ""
        _CIRCUIT_BREAKER["triggered_at"] = None


def get_circuit_breaker_status() -> Dict[str, Any]:
    now = time.time()
    until = float(_CIRCUIT_BREAKER.get("cooldown_until") or 0.0)
    active = now < until
    return {
        "on_cooldown": active,
        "remaining_seconds": round(max(0.0, until - now), 1) if active else 0.0,
        "last_status_code": _CIRCUIT_BREAKER.get("last_status_code"),
        "last_reason": _CIRCUIT_BREAKER.get("last_reason") or None,
    }


def check_free_quota(force: bool = False, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Queries `GET https://openrouter.ai/api/v1/key` to inspect key status and free-tier rate limits.
    Cached for 60 seconds in memory.
    """
    api_key = resolve_openrouter_api_key()
    if not api_key:
        return {"configured": False, "reason": "OPENROUTER_API_KEY not found"}

    now = time.time()
    if not force and _QUOTA_CACHE["data"] and (now - _QUOTA_CACHE["timestamp"] < 60.0):
        return _QUOTA_CACHE["data"]

    req = urllib.request.Request(
        OPENROUTER_KEY_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "ContentFactoryStudio/3.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            data = raw.get("data") if isinstance(raw, dict) else {}
            result = {
                "configured": True,
                "label": data.get("label"),
                "usage": data.get("usage", 0),
                "limit": data.get("limit"),
                "is_free_tier": data.get("is_free_tier", True),
                "rate_limit": data.get("rate_limit"),
            }
            _QUOTA_CACHE["timestamp"] = now
            _QUOTA_CACHE["data"] = result
            return result
    except urllib.error.HTTPError as he:
        if he.code in (402, 429):
            record_openrouter_status(he.code, f"Quota check returned HTTP {he.code}")
        return {"configured": True, "error": f"HTTP {he.code}"}
    except Exception as e:
        return {"configured": True, "error": str(e)}


def get_capabilities_report(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Builds the live 6-stage capability report for `GET /api/copilot/openrouter-capabilities`.
    Shows which stages have active `$0 :free` OpenRouter models vs. which stages auto-skip to local engines.
    """
    cache = refresh_catalog_if_needed(force=force_refresh)
    stages = cache.get("stages") or {}
    cb = get_circuit_breaker_status()
    api_key_present = bool(resolve_openrouter_api_key())

    stage_table: Dict[str, Any] = {}
    for stage_name in ("text", "vision", "image", "speech", "audio", "video"):
        models = list(stages.get(stage_name, []))
        can_use_openrouter = api_key_present and (not cb["on_cooldown"]) and len(models) > 0
        stage_table[stage_name] = {
            "status": "openrouter_free_active" if can_use_openrouter else "auto_skip_to_local",
            "free_models_count": len(models),
            "free_models": models,
            "primary_free_model": models[0] if models else None,
            "local_fallback_engine": LOCAL_FALLBACK_ENGINES.get(stage_name),
        }

    return {
        "strict_zero_cost_lock": True,
        "api_key_configured": api_key_present,
        "harvester_openrouter_enabled": ALLOW_HARVESTER_OPENROUTER_FREE,
        "catalog_total_scanned": cache.get("raw_count", 0),
        "catalog_strictly_free_count": cache.get("strictly_free_count", 0),
        "last_catalog_refresh_epoch": cache.get("timestamp", 0.0),
        "circuit_breaker": cb,
        "stages": stage_table,
    }
