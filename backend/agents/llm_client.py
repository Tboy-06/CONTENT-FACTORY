from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from backend.config import get_settings

settings = get_settings()


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, ResourceExhausted):
        return True
    if hasattr(exc, "code") and exc.code in (429, 503):
        return True
    if hasattr(exc, "status_code") and exc.status_code in (429, 503):
        return True
    if hasattr(exc, "code") and exc.code == 404:
        return False
    if hasattr(exc, "status_code") and exc.status_code == 404:
        return False
    return False


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _build_config(
        self,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_mime_type: str = "text/plain",
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ],
        )

    def count_tokens(self, text: str) -> int:
        client = self._get_client()
        res = client.models.count_tokens(model=self.model_name, contents=text)
        return getattr(res, "total_tokens", 0) or 0

    @retry(
        wait=wait_exponential(multiplier=2, min=5, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(_is_retryable_error),
    )
    async def _generate_with_retry(
        self,
        model_name: str,
        contents: Any,
        config: types.GenerateContentConfig,
    ):
        client = self._get_client()
        return await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_mime_type: str = "text/plain",
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # If no Gemini API key is set, route automatically to free Brain router without retry delays
        if not self.api_key:
            from backend.engine.brain import ask_brain
            format_json = response_mime_type == "application/json"
            text = await ask_brain(prompt, system_prompt=system_prompt, format_json=format_json)
            return {
                "text": text,
                "tokens_in": len(prompt.split()),
                "tokens_out": len(text.split()),
                "raw": None,
            }

        gen_config = self._build_config(
            system_instruction=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )

        candidate_models = [
            model or self.model_name,
            "models/gemini-3.5-flash-lite",
            "models/gemini-3.8-flash",
            "models/gemini-3.6-flash",
            "models/gemini-3.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-flash-lite-latest",
        ]
        response = None
        last_error = None
        for m_name in candidate_models:
            try:
                response = await self._generate_with_retry(m_name, prompt, gen_config)
                if response:
                    break
            except Exception as e:
                last_error = e
                continue

        if response is None:
            if last_error:
                raise last_error
            raise RuntimeError("All Gemini models failed to generate response")

        tokens_in = 0
        tokens_out = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        try:
            text = response.text or ""
        except ValueError as e:
            text = ""
            print(f"Safety filter blocked response: {e}")

        return {
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "raw": response,
        }

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )

        try:
            import re
            raw_text = result["text"].strip()
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            text_to_parse = match.group(0) if match else raw_text
            parsed = json.loads(text_to_parse)
            return {
                "success": True,
                "data": parsed,
                "tokens_in": result["tokens_in"],
                "tokens_out": result["tokens_out"],
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse JSON: {e}",
                "raw": result["text"],
                "tokens_in": result["tokens_in"],
                "tokens_out": result["tokens_out"],
            }

    async def generate_with_vision(
        self,
        prompt: str,
        image_paths: List[str],
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        client = self._get_client()
        target_model = model or settings.gemini_vision_model

        contents: List[Any] = [prompt]
        for path in image_paths:
            with open(path, "rb") as f:
                contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        gen_config = self._build_config(temperature=temperature, max_tokens=max_tokens)
        response = await self._generate_with_retry(target_model, contents, gen_config)

        tokens_in = 0
        tokens_out = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        text = getattr(response, "text", "") or ""
        return {
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        target_model = model or self.model_name
        gen_config = self._build_config(system_instruction=system_prompt, temperature=temperature)
        response = await client.aio.models.generate_content_stream(
            model=target_model,
            contents=prompt,
            config=gen_config,
        )
        async for chunk in response:
            if getattr(chunk, "text", None):
                yield chunk.text


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client(api_key: Optional[str] = None, model: Optional[str] = None) -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient(api_key=api_key, model=model)
    return _gemini_client
