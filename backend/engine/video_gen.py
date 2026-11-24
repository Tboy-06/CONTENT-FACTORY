"""
CONTENT-FACTORY Engine: Zero-Cost Generative Video Engine (video_gen.py)
------------------------------------------------------------------------
Brings Google Flow / Gemini / Hugging Face style Image-to-Video & Text-to-Video
(Prompt + optional Starting Reference Image -> Real Moving AI Video with Native Audio)
into CONTENT-FACTORY at $0 cost with strict zero-billing protection:

- Tier 1 ($0 Default — Hugging Face ZeroGPU via `gradio_client`):
  * Primary Space: `Lightricks/LTX-2.5` (Text-to-Video & Image-to-Video with synchronized native audio)
  * Fallback Space: `zerogpu-aoti/wan2-2-fp8da-aoti-faster` (Wan 2.2 14B Image-to-Video)
  * Fast Backup Space: `Lightricks/LTX-Video`
  * Passes user's free `HF_TOKEN` (5 min/day free ZeroGPU quota), inspects endpoints via `view_api()`,
    saves `.mp4` clips strictly to `C:\\cf_training\\temp\\ai_clips\\` (0 MB bloat on D:), and trips a
    cooldown circuit-breaker immediately if daily ZeroGPU quota is exhausted.
- Tier 2 (Strict Opt-In Paid — `gemini-omni-1.2-flash`):
  * Hard-blocked by default (`enable_paid_gemini_video=False`) so $0 billing is guaranteed.
- Tier 3 (Graceful Google Flow Handoff & B-Roll Fallback):
  * Returns `status="quota_exhausted"` with a `flow_handoff` package (`prompt`, `image_path`, `flow_url`)
    so the user can 1-click copy into Google Flow (50 free daily credits) or fall back to real B-roll.
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import os
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.config import get_settings

logger = logging.getLogger("engine.video_gen")

# Strictly store generated AI video clips on C: drive (0 MB bloat on D:)
AI_CLIPS_DIR = r"C:\cf_training\temp\ai_clips"
os.makedirs(AI_CLIPS_DIR, exist_ok=True)

PRIMARY_LTX_SPACE = "Lightricks/LTX-2.5"
FALLBACK_WAN_SPACE = "zerogpu-aoti/wan2-2-fp8da-aoti-faster"
TERTIARY_LTX_SPACE = "Lightricks/LTX-Video"
GOOGLE_FLOW_URL = "https://labs.google/fx/tools/flow"

# Circuit Breaker State for Hugging Face ZeroGPU 5-min/day quota
_ZEROGPU_COOLDOWN_UNTIL: float = 0.0
_ZEROGPU_LAST_REASON: Optional[str] = None


def is_zerogpu_on_cooldown() -> bool:
    """Returns True if Hugging Face ZeroGPU daily quota circuit breaker is currently active."""
    return time.time() < _ZEROGPU_COOLDOWN_UNTIL


def trip_zerogpu_circuit_breaker(reason: str, cooldown_seconds: float = 900.0) -> None:
    """Trips the ZeroGPU circuit breaker so subsequent beats don't waste retries on exhausted quota."""
    global _ZEROGPU_COOLDOWN_UNTIL, _ZEROGPU_LAST_REASON
    _ZEROGPU_COOLDOWN_UNTIL = time.time() + cooldown_seconds
    _ZEROGPU_LAST_REASON = reason
    logger.warning(f"[video_gen] ZeroGPU circuit breaker tripped for {int(cooldown_seconds)}s: {reason}")


def reset_zerogpu_circuit_breaker() -> None:
    """Resets the ZeroGPU circuit breaker."""
    global _ZEROGPU_COOLDOWN_UNTIL, _ZEROGPU_LAST_REASON
    _ZEROGPU_COOLDOWN_UNTIL = 0.0
    _ZEROGPU_LAST_REASON = None


def _get_gradio_client_cls():
    """Lazy loader for gradio_client.Client (patchable in unit tests)."""
    from gradio_client import Client
    return Client


def _wrap_file_for_gradio(file_path: str) -> Any:
    """Wraps a local image path using gradio_client.handle_file if available."""
    try:
        from gradio_client import handle_file
        return handle_file(file_path)
    except Exception:
        return file_path


def build_google_flow_handoff(
    prompt: str,
    image_path: Optional[str] = None,
    duration: float = 5.0
) -> Dict[str, Any]:
    """
    Constructs a 1-click Google Flow / Gemini Web handoff payload when daily
    Hugging Face ZeroGPU quota is exhausted or for manual hero-shot creation.
    """
    return {
        "prompt": prompt.strip(),
        "image_path": image_path,
        "duration": round(float(duration), 1),
        "flow_url": GOOGLE_FLOW_URL,
        "instructions": (
            "1. Open Google Flow (50 free credits/day). "
            "2. Paste the copied cinematic prompt and attach the reference image. "
            "3. Download the generated .mp4 clip and drop it into this beat's Upload Clip slot."
        ),
    }


def _extract_video_path_from_result(result: Any) -> Optional[str]:
    """Extracts a local filesystem .mp4 path from diverse Gradio Space return signatures."""
    if not result:
        return None
    if isinstance(result, str) and os.path.exists(result):
        return result
    if isinstance(result, dict):
        for key in ("video", "path", "value", "output", "file"):
            val = result.get(key)
            if isinstance(val, str) and os.path.exists(val):
                return val
            if isinstance(val, dict):
                nested = _extract_video_path_from_result(val)
                if nested:
                    return nested
    if isinstance(result, (list, tuple)):
        for item in result:
            found = _extract_video_path_from_result(item)
            if found:
                return found
    return None


def _instantiate_gradio_client(client_cls: Any, space_id: str, token: Optional[str]) -> Any:
    """Instantiates gradio_client.Client across v1.x and v2.x signatures (`token` vs `hf_token`)."""
    if not token:
        return client_cls(space_id)
    try:
        sig = inspect.signature(client_cls.__init__)
        if "token" in sig.parameters:
            return client_cls(space_id, token=token)
        if "hf_token" in sig.parameters:
            return client_cls(space_id, hf_token=token)
    except Exception:
        pass
    try:
        return client_cls(space_id, token=token)
    except TypeError:
        return client_cls(space_id, hf_token=token)


def _predict_on_space(
    client: Any,
    space_id: str,
    prompt: str,
    image_path: Optional[str],
    duration: float
) -> Optional[str]:
    """
    Inspects the Gradio Space's endpoints via `view_api()` and calls `predict()`
    using resilient parameter mapping on a single connection.
    """
    has_image = bool(image_path and os.path.exists(image_path))
    api_info = None
    try:
        api_info = client.view_api(return_format="dict")
    except Exception:
        api_info = None

    chosen_api_name = None
    param_names: List[str] = []

    if isinstance(api_info, dict):
        named = api_info.get("named_endpoints") or {}
        # Prefer endpoints matching generate / video / i2v / t2v
        preferred_order = sorted(
            named.keys(),
            key=lambda k: (
                0 if any(w in k.lower() for w in ("generate", "video", "i2v", "t2v", "infer", "predict")) else 1
            ),
        )
        if preferred_order:
            chosen_api_name = preferred_order[0]
            ep_meta = named.get(chosen_api_name) or {}
            param_names = [
                str(p.get("parameter_name") or p.get("label") or "").lower()
                for p in (ep_meta.get("parameters") or [])
            ]

    kwargs: Dict[str, Any] = {}
    if param_names:
        for p in param_names:
            if p in ("prompt", "text", "text_prompt", "positive_prompt"):
                kwargs[p] = prompt
                break
        if has_image and image_path:
            for p in param_names:
                if p in ("image", "input_image", "init_image", "first_frame", "cond_image", "reference_image"):
                    kwargs[p] = _wrap_file_for_gradio(image_path)
                    break
        for p in param_names:
            if p in ("duration", "video_length", "seconds", "length"):
                kwargs[p] = duration
                break

    if not kwargs:
        kwargs["prompt"] = prompt
        if has_image and image_path and "wan" in space_id.lower():
            kwargs["image"] = _wrap_file_for_gradio(image_path)

    # Attempt prediction with discovered api_name, then fallback to default predict
    attempts = []
    if chosen_api_name:
        attempts.append((chosen_api_name, kwargs))
    for default_ep in ("/generate", "/generate_video", "/predict", "/infer"):
        if default_ep != chosen_api_name:
            attempts.append((default_ep, {"prompt": prompt}))

    last_err = None
    for ep_name, ep_kwargs in attempts:
        try:
            res = client.predict(api_name=ep_name, **ep_kwargs)
            vid = _extract_video_path_from_result(res)
            if vid:
                return vid
        except Exception as e:
            last_err = e
            err_lower = str(e).lower()
            if any(q in err_lower for q in ("quota", "zerogpu", "exceeded", "daily limit", "429")):
                raise

    if last_err:
        raise last_err
    return None


def generate_ai_video_clip(
    prompt: str,
    image_path: Optional[str] = None,
    duration: float = 5.0,
    mode: str = "free_hf",
    engine: str = "auto",
    hf_token: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a real moving AI video clip from `{prompt + optional reference image}`:
    - Tier 1 (`mode="free_hf"`): Hugging Face ZeroGPU (`Lightricks/LTX-2.5` -> `Wan 2.2 14B I2V`) at $0.
    - Tier 2 (`mode="paid_gemini_omni"`): Strictly blocked unless `settings.enable_paid_gemini_video=True`.
    - Tier 3: Returns `status="quota_exhausted"` + `flow_handoff` when ZeroGPU quota is full.
    """
    os.makedirs(AI_CLIPS_DIR, exist_ok=True)
    clean_prompt = (prompt or "Cinematic 35mm documentary shot, volumetric lighting").strip()[:280]
    cfg = get_settings()
    handoff = build_google_flow_handoff(clean_prompt, image_path=image_path, duration=duration)

    # ------------------------------------------------------------------
    # TIER 2: Strict $0 Billing Lock on Paid Gemini Omni 1.2 Flash
    # ------------------------------------------------------------------
    if mode == "paid_gemini_omni" or engine == "gemini_omni":
        if not getattr(cfg, "enable_paid_gemini_video", False):
            logger.info("[video_gen] Blocked paid_gemini_omni request (enable_paid_gemini_video=False).")
            return {
                "status": "blocked_zero_cost_guard",
                "cost_usd": 0.0,
                "video_path": None,
                "engine_used": None,
                "has_native_audio": False,
                "message": (
                    "Paid Gemini Omni 1.2 Flash video API is locked OFF by the $0 Zero-Cost Rule "
                    "(enable_paid_gemini_video=False). Use free Hugging Face ZeroGPU or Google Flow handoff."
                ),
                "flow_handoff": handoff,
            }

    # ------------------------------------------------------------------
    # TIER 1: Free Hugging Face ZeroGPU (`Lightricks/LTX-2.5` & `Wan 2.2 I2V`)
    # ------------------------------------------------------------------
    if is_zerogpu_on_cooldown():
        rem = max(0, int(_ZEROGPU_COOLDOWN_UNTIL - time.time()))
        return {
            "status": "quota_exhausted",
            "cost_usd": 0.0,
            "video_path": None,
            "engine_used": None,
            "has_native_audio": False,
            "reason": f"ZeroGPU cooldown active ({rem}s remaining): {_ZEROGPU_LAST_REASON}",
            "flow_handoff": handoff,
        }

    resolved_token = (
        hf_token
        or os.environ.get("HF_TOKEN", "").strip()
        or getattr(cfg, "hf_token", "").strip()
        or None
    )

    try:
        client_cls = _get_gradio_client_cls()
    except Exception as imp_err:
        return {
            "status": "quota_exhausted",
            "cost_usd": 0.0,
            "video_path": None,
            "engine_used": None,
            "has_native_audio": False,
            "reason": f"gradio_client unavailable: {imp_err}",
            "flow_handoff": handoff,
        }

    # Candidate ZeroGPU Spaces in priority order
    candidates: List[Tuple[str, bool]] = []
    if engine == "hf_wan22":
        candidates = [
            (FALLBACK_WAN_SPACE, False),
            (PRIMARY_LTX_SPACE, True),
        ]
    elif engine == "hf_ltx25":
        candidates = [
            (PRIMARY_LTX_SPACE, True),
            (FALLBACK_WAN_SPACE, False),
        ]
    else:
        candidates = [
            (PRIMARY_LTX_SPACE, True),
            (FALLBACK_WAN_SPACE, False),
            (TERTIARY_LTX_SPACE, False),
        ]

    last_error = "No ZeroGPU Space responded"
    for space_id, has_native_audio in candidates:
        try:
            logger.info(
                f"[video_gen] Calling Hugging Face ZeroGPU Space '{space_id}' "
                f"(auth={'HF_TOKEN' if resolved_token else 'anonymous'}, image={bool(image_path)})..."
            )
            client = _instantiate_gradio_client(client_cls, space_id, resolved_token)
            raw_clip_path = _predict_on_space(
                client=client,
                space_id=space_id,
                prompt=clean_prompt,
                image_path=image_path,
                duration=duration,
            )
            if raw_clip_path and os.path.exists(raw_clip_path):
                clip_hash = hashlib.sha256(
                    f"{space_id}:{clean_prompt}:{image_path}:{duration}".encode("utf-8")
                ).hexdigest()[:12]
                c_dest = os.path.join(AI_CLIPS_DIR, f"ai_clip_{clip_hash}.mp4")
                shutil.copy2(raw_clip_path, c_dest)
                if output_path and os.path.abspath(output_path) != os.path.abspath(c_dest):
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    shutil.copy2(c_dest, output_path)
                logger.info(f"[video_gen] Generated ZeroGPU AI clip via {space_id} -> {c_dest}")
                return {
                    "status": "success",
                    "cost_usd": 0.0,
                    "video_path": c_dest,
                    "output_path": output_path or c_dest,
                    "engine_used": space_id,
                    "has_native_audio": has_native_audio,
                    "flow_handoff": handoff,
                }
        except Exception as e:
            last_error = str(e)
            err_lower = last_error.lower()
            if any(q in err_lower for q in ("quota", "zerogpu", "exceeded", "daily limit", "429")):
                trip_zerogpu_circuit_breaker(last_error)
                return {
                    "status": "quota_exhausted",
                    "cost_usd": 0.0,
                    "video_path": None,
                    "engine_used": space_id,
                    "has_native_audio": False,
                    "reason": last_error,
                    "flow_handoff": handoff,
                }
            logger.info(f"[video_gen] Space {space_id} unavailable ({last_error[:100]}), trying fallback...")

    return {
        "status": "quota_exhausted",
        "cost_usd": 0.0,
        "video_path": None,
        "engine_used": None,
        "has_native_audio": False,
        "reason": last_error,
        "flow_handoff": handoff,
    }


def get_video_gen_status() -> Dict[str, Any]:
    """Returns current ZeroGPU video generator status for Studio UI telemetry."""
    cfg = get_settings()
    token_present = bool(os.environ.get("HF_TOKEN", "").strip() or getattr(cfg, "hf_token", "").strip())
    on_cd = is_zerogpu_on_cooldown()
    return {
        "hf_token_configured": token_present,
        "daily_quota_tier": "5 min/day ZeroGPU (Free Account)" if token_present else "Anonymous (Add HF_TOKEN in Settings for 5 min/day)",
        "primary_space": PRIMARY_LTX_SPACE,
        "fallback_space": FALLBACK_WAN_SPACE,
        "paid_gemini_video_enabled": bool(getattr(cfg, "enable_paid_gemini_video", False)),
        "circuit_breaker": {
            "on_cooldown": on_cd,
            "remaining_seconds": max(0.0, round(_ZEROGPU_COOLDOWN_UNTIL - time.time(), 1)) if on_cd else 0.0,
            "last_reason": _ZEROGPU_LAST_REASON,
        },
        "storage_dir": AI_CLIPS_DIR,
    }
