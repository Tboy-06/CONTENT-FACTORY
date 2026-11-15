"""
CONTENT-FACTORY Engine: Brain Router
------------------------------------
Auto-detects online/offline connectivity and routes reasoning to:
- Offline: Local Ollama (SparkLLM/Spark-X2.5-4B / DeepSeek)
- Online: Free GLM-5.3-Flash / Gemini / Cloud API
- Robust Fallback: Built-in documentary structured generator
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import socket
import subprocess
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("engine.brain")

DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "copilot-brain:latest")
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")


def clean_json_text(text: str) -> str:
    """Strips markdown code fences (```json ... ```) to guarantee parseable JSON."""
    if not text:
        return ""
    clean = text.strip()
    clean = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", clean)
    clean = re.sub(r"\n?```$", "", clean)
    return clean.strip()



LLAMA_SERVER_BIN = r"D:\CONTENT-FACTORY\ollama\bin\llama-server.exe"
COPILOT_GGUF_BLOB = r"D:\CONTENT-FACTORY\ollama\models\copilot-brain.gguf"
SPARK_GGUF_BLOB = r"C:\models\Spark-X2.5-4B-Q4_K_M.gguf"
# Fallback paths
_FALLBACK_BIN = r"C:\cf_training\bin\llama-server.exe"
_LOCAL_BRAIN_PROC: Optional[subprocess.Popen] = None


def get_preferred_gguf_blob() -> str:
    """Returns the active GGUF model blob (supports both Spark-X2.5-4B on C: and copilot-brain on D:)."""
    model_name = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).lower()
    if "spark" in model_name and os.path.exists(SPARK_GGUF_BLOB):
        return SPARK_GGUF_BLOB
    if os.path.exists(COPILOT_GGUF_BLOB):
        return COPILOT_GGUF_BLOB
    if os.path.exists(SPARK_GGUF_BLOB):
        return SPARK_GGUF_BLOB
    return COPILOT_GGUF_BLOB


async def ensure_local_brain(timeout_secs: int = 60) -> bool:
    """Wakes up the local GGUF model blob on demand using llama-server.exe without eating RAM when idle."""
    global _LOCAL_BRAIN_PROC
    if is_ollama_ready():
        return True

    # If the process isn't running at all, spawn it
    if not is_ollama_running():
        bin_path = LLAMA_SERVER_BIN if os.path.exists(LLAMA_SERVER_BIN) else _FALLBACK_BIN
        blob_path = get_preferred_gguf_blob()

        if not os.path.exists(bin_path) or not os.path.exists(blob_path):
            logger.warning(f"[Brain] llama-server ({bin_path}) or GGUF blob ({blob_path}) not found.")
            return False

        model_label = "Spark-X2.5-4B" if "spark" in blob_path.lower() else "Copilot-Brain"
        logger.info(f"[Brain] Waking up {model_label} GGUF on demand via llama-server.exe ({blob_path})...")
        cmd = [
            bin_path,
            "-m", blob_path,
            "--port", "11434",
            "--host", "127.0.0.1",
            "-c", "1024",
            "-t", "6",
            "--log-disable",
            "--sleep-idle-seconds", "300"
        ]
        try:
            _LOCAL_BRAIN_PROC = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error(f"[Brain] Failed to start llama-server.exe: {e}")
            return False

    # Wait until model is fully loaded and ready (returns HTTP 200 from /health)
    for _ in range(timeout_secs):
        await asyncio.sleep(1)
        if is_ollama_ready():
            logger.info("[Brain] Local GGUF llama-server is online, model loaded, and ready on http://127.0.0.1:11434")
            return True

    return is_ollama_ready()


def is_ollama_ready(timeout: float = 1.0) -> bool:
    """Checks whether local llama-server or Ollama is online AND ready to serve completions."""
    # 1. Try llama-server /health (returns 200 when ready, 503 while loading)
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError:
        return False  # e.g. 503 Service Unavailable (loading model)
    except Exception:
        pass

    # 2. Try standard Ollama root / (returns 200 'Ollama is running')
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    return False


def is_ollama_running(timeout: float = 0.2) -> bool:
    """Fast check whether local Ollama server is actually listening."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", 11434))
        s.close()
        return True
    except OSError:
        return False


def is_online(timeout: float = 1.0) -> bool:
    """Quickly tests internet reachability without DNS reliance."""
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, 53))
            sock.close()
            return True
        except OSError:
            continue
    return False


async def call_ollama(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_OLLAMA_MODEL,
    format_json: bool = True,
    num_predict: int = 2048,
    timeout: float = 60.0
) -> Optional[str]:
    """Queries local brain instance (llama-server /v1/chat/completions or Ollama /api/chat)."""
    if not is_ollama_ready():
        return None
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    def _sync_req():
        import time
        # 1. Try OpenAI-compatible endpoint (native to llama-server.exe)
        for attempt in range(4):
            try:
                openai_url = "http://127.0.0.1:11434/v1/chat/completions"
                payload = {
                    "messages": messages,
                    "max_tokens": min(num_predict, 1024),
                    "temperature": 0.3
                }
                if format_json:
                    payload["response_format"] = {"type": "json_object"}
                req = urllib.request.Request(
                    openai_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                    choices = raw.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
            except urllib.error.HTTPError as he:
                if he.code == 503 and attempt < 3:
                    time.sleep(2)
                    continue
                logger.debug(f"[Brain] llama-server HTTP error: {he}")
                break
            except Exception as oe:
                logger.debug(f"[Brain] llama-server /v1/chat/completions fallback to /api/chat: {oe}")
                break

        # 2. Fallback to standard Ollama endpoint
        try:
            ollama_payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": False,
                "think": False,
                "keep_alive": "5m",
                "options": {
                    "temperature": 0.3,
                    "num_predict": num_predict,
                    "think": False,
                }
            }
            if format_json:
                ollama_payload["format"] = "json"
            req = urllib.request.Request(
                OLLAMA_ENDPOINT,
                data=json.dumps(ollama_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                return raw.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"[Brain] Local Ollama /api/chat query failed: {e}")
            return None

    try:
        content = await asyncio.to_thread(_sync_req)
        return content
    except Exception as e:
        logger.warning(f"Local brain inference error: {e}")
        return None
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "2m",
        "options": {
            "temperature": 0.4,
            "num_predict": num_predict,
            "think": False,
        }
    }
    if format_json:
        payload["format"] = "json"

    def _sync_req():
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            return raw.get("message", {}).get("content", "")

    try:
        content = await asyncio.to_thread(_sync_req)
        return content
    except Exception as e:
        logger.warning(f"Ollama query failed ({model}): {e}")
        return None


async def call_cloud_free(
    prompt: str,
    system_prompt: Optional[str] = None,
    format_json: bool = True,
    timeout: float = 20.0
) -> Optional[str]:
    """
    Zero-cost Cloud fallback route using Pollinations text API.
    Requires no API keys, runs at 100% free $0 cost, and returns in ~3s.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages,
        "model": "openai",
        "jsonMode": format_json,
        "seed": 42
    }

    def _sync_pollinations():
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")

    try:
        content = await asyncio.to_thread(_sync_pollinations)
        if content and len(content.strip()) > 0:
            return content.strip()
    except Exception as e:
        logger.warning(f"Free cloud LLM query failed: {e}")

    # Fallback attempt without jsonMode if jsonMode was rejected
    if format_json:
        try:
            payload["jsonMode"] = False
            payload["messages"][-1]["content"] += "\nReturn strictly a valid JSON object without markdown fences."
            content = await asyncio.to_thread(_sync_pollinations)
            if content and len(content.strip()) > 0:
                return content.strip()
        except Exception:
            pass

    # Fallback to optional user API keys if configured
    try:
        from backend.config import get_settings
        cfg = get_settings()
        gemini_key = cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model_inst = genai.GenerativeModel(cfg.gemini_model or "gemini-2.5-flash")
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            res = await asyncio.to_thread(model_inst.generate_content, full_prompt)
            if res and res.text:
                return res.text.strip()
    except Exception as e:
        logger.warning(f"Gemini fallback failed: {e}")

    return None


async def call_kimi_k3(
    prompt: str,
    system_prompt: Optional[str] = None,
    format_json: bool = True,
    model: Optional[str] = None,
    timeout: float = 30.0
) -> Optional[str]:
    """
    Kimi K3 / Moonshot AI Engine:
    Queries Moonshot AI / Kimi endpoint using OpenAI-compatible payload format.
    Zero local RAM overhead (0 MB local VRAM), true frontier MoE execution.
    """
    from backend.config import get_settings
    cfg = get_settings()
    api_key = cfg.moonshot_api_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        return None

    target_model = model or cfg.moonshot_model or "kimi-k3"
    endpoint = cfg.kimi_endpoint or "https://api.moonshot.cn/v1/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": target_model,
        "messages": messages,
        "reasoning_effort": "low",
    }
    # NOTE: Moonshot Kimi K3 locks temperature=1.0 and top_p=0.95 at server level.
    # Explicitly omit temperature and top_p to prevent HTTP 400 Bad Request.
    if format_json:
        payload["response_format"] = {"type": "json_object"}

    def _sync_kimi():
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_obj = json.loads(resp.read().decode("utf-8"))
            return res_obj.get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        content = await asyncio.to_thread(_sync_kimi)
        if content and len(content.strip()) > 0:
            logger.info(f"[Brain] Kimi K3 inference succeeded via {target_model}")
            return content.strip()
    except Exception as e:
        logger.warning(f"[Brain] Kimi K3 API call failed: {e}")

    return None


async def ask_brain(
    prompt: str,
    system_prompt: Optional[str] = None,
    format_json: bool = True,
    num_predict: int = 2048,
    engine_mode: str = "auto"
) -> str:
    """
    Unified brain router (Hardware-Optimized Priority):
    - "offline_spark": Forces local Ollama (Spark-X2.5-4B) for 100% offline private execution.
    - "cloud": Forces cloud endpoints (Kimi K3 / Gemini / Cloud router).
    - "auto": Online Cloud priority with automatic Ollama offline fallback.
    """
    if engine_mode == "offline_spark":
        if not is_ollama_ready():
            await ensure_local_brain()
        if is_ollama_ready():
            logger.info(f"[Brain] Explicit engine_mode='offline_spark': Engaging local GGUF brain ({DEFAULT_OLLAMA_MODEL})...")
            res = await call_ollama(
                prompt,
                system_prompt=system_prompt,
                format_json=format_json,
                num_predict=num_predict
            )
            if res:
                return clean_json_text(res) if format_json else res
        raise RuntimeError(f"Offline GGUF brain server ({DEFAULT_OLLAMA_MODEL}) could not be initialized on http://localhost:11434. Please verify {LLAMA_SERVER_BIN} exists.")

    online = is_online() if engine_mode != "cloud" else True
    logger.info(f"[Brain] Routing query (EngineMode={engine_mode}, Online={online})")

    # 1. When Online or Cloud Mode: Try Cloud FIRST (Gemini 3.1 Flash Lite / Kimi K3 -> 0 MB local RAM, 0% CPU, 2s response)
    if online:
        # A. Kimi K3 / Moonshot Engine (ONLY if key is populated)
        from backend.config import get_settings
        cfg = get_settings()
        moonshot_key = cfg.moonshot_api_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        if moonshot_key and len(moonshot_key.strip()) > 0:
            try:
                kimi_res = await call_kimi_k3(prompt, system_prompt=system_prompt, format_json=format_json)
                if kimi_res:
                    logger.info("[Brain] Kimi K3 MoE inference succeeded (0 MB local RAM used)")
                    return clean_json_text(kimi_res) if format_json else kimi_res
            except Exception as e:
                logger.warning(f"[Brain] Kimi K3 routing error: {e}")

        # B. Gemini API with candidate model cascade
        try:
            from backend.config import get_settings
            cfg = get_settings()
            gemini_key = cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                if format_json and "JSON" not in full_prompt.upper():
                    full_prompt += "\nOutput strictly a valid JSON object or array without markdown fences."

                candidate_models = [
                    cfg.gemini_model if cfg.gemini_model and "2.5" not in cfg.gemini_model else "models/gemini-flash-latest",
                    "models/gemini-flash-latest",
                    "models/gemini-flash-lite-latest",
                    "models/gemini-3.1-flash-lite",
                    "models/gemini-3.5-flash",
                ]
                seen_models = set()
                models_to_try = []
                for m in candidate_models:
                    if m not in seen_models:
                        seen_models.add(m)
                        models_to_try.append(m)

                for model_name in models_to_try:
                    try:
                        model_inst = genai.GenerativeModel(model_name)
                        res = await asyncio.wait_for(
                            model_inst.generate_content_async(full_prompt),
                            timeout=20.0
                        )
                        if res and res.text:
                            logger.info(f"[Brain] Cloud inference succeeded via {model_name} (0 MB local RAM used)")
                            cleaned = clean_json_text(res.text) if format_json else res.text.strip()
                            return cleaned
                    except Exception as model_err:
                        err_str = str(model_err)
                        if "429" in err_str or "quota" in err_str.lower() or "404" in err_str or "timeout" in err_str.lower():
                            logger.warning(f"[Brain] Model {model_name} quota/availability/timeout: {err_str[:120]}. Trying next fallback model...")
                            continue
                        else:
                            logger.warning(f"[Brain] Model {model_name} error: {err_str[:120]}")
                            continue
        except Exception as e:
            logger.warning(f"[Brain] Gemini cloud generation error: {e}")

        # C. Free cloud endpoint fallback (0 key, 0 RAM)
        try:
            cloud_res = await call_cloud_free(prompt, system_prompt=system_prompt, format_json=format_json)
            if cloud_res:
                logger.info("[Brain] Free cloud endpoint inference succeeded (0 MB local RAM used)")
                return clean_json_text(cloud_res) if format_json else cloud_res
        except Exception as e:
            logger.warning(f"[Brain] Free cloud fallback error: {e}")

    # 2. Offline Mode or Cloud Failover: Use local Ollama (copilot-brain:latest)
    if is_ollama_running():
        logger.info(f"[Brain] Engaging local Ollama ({DEFAULT_OLLAMA_MODEL}) offline engine...")
        res = await call_ollama(
            prompt,
            system_prompt=system_prompt,
            format_json=format_json,
            num_predict=num_predict
        )
        if res:
            logger.info("[Brain] Local Ollama inference completed successfully")
            return clean_json_text(res) if format_json else res

    raise RuntimeError("No LLM engine responded. Fallback generator should engage.")
