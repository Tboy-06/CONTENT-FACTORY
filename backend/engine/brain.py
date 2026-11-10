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
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("engine.brain")

DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "SparkLLM/Spark-X2.5-4B")
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")


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
    """Queries local Ollama instance with think=False to prevent 80s reasoning delays."""
    if not is_ollama_running():
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


async def ask_brain(
    prompt: str,
    system_prompt: Optional[str] = None,
    format_json: bool = True,
    num_predict: int = 2048
) -> str:
    """
    Unified brain router (Hardware-Optimized Priority):
    1. Online Mode (is_online() == True):
       - Primary: Gemini API (gemini-2.5-flash) -> 2-second cloud speed, 0 MB local RAM, 0% CPU.
       - Secondary: Zero-cost cloud endpoint (call_cloud_free).
    2. Offline Mode (or if Cloud Fails / Rate-Limited):
       - Automatically fails over to local Ollama (Spark-X2.5-4B with think: False).
    3. Emergency Fallback:
       - Raises RuntimeError to engage deterministic generator in planner.py.
    """
    online = is_online()
    logger.info(f"[Brain] Routing query (Online={online})")

    # 1. When Online: Try Cloud FIRST (Gemini 2.5 Flash -> 0 MB local RAM, 0% CPU, 2s response)
    if online:
        # A. Gemini API with candidate model cascade
        try:
            from backend.config import get_settings
            cfg = get_settings()
            gemini_key = cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                if format_json and "JSON" not in full_prompt.upper():
                    full_prompt += "\nOutput strictly a valid JSON object or array."

                candidate_models = [
                    cfg.gemini_model or "gemini-2.5-flash",
                    "gemini-2.5-flash",
                    "gemini-flash-latest",
                    "gemini-3.8-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-flash-lite-latest",
                    "gemini-2.5-pro",
                    "gemini-pro-latest",
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
                            timeout=12.0
                        )
                        if res and res.text:
                            logger.info(f"[Brain] Cloud inference succeeded via {model_name} (0 MB local RAM used)")
                            return res.text.strip()
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

        # B. Free cloud endpoint fallback (0 key, 0 RAM)
        try:
            cloud_res = await call_cloud_free(prompt, system_prompt=system_prompt, format_json=format_json)
            if cloud_res:
                logger.info("[Brain] Free cloud endpoint inference succeeded (0 MB local RAM used)")
                return cloud_res
        except Exception as e:
            logger.warning(f"[Brain] Free cloud fallback error: {e}")

    # 2. Offline Mode or Cloud Failover: Use local Ollama (Spark-X2.5-4B)
    if is_ollama_running():
        logger.info("[Brain] Engaging local Ollama (Spark-X2.5-4B) offline engine...")
        res = await call_ollama(
            prompt,
            system_prompt=system_prompt,
            format_json=format_json,
            num_predict=num_predict
        )
        if res:
            logger.info("[Brain] Local Ollama inference completed successfully")
            return res

    raise RuntimeError("No LLM engine responded. Fallback generator should engage.")
