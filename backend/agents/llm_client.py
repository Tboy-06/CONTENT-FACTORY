from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception

from backend.config import get_settings

settings = get_settings()


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, ResourceExhausted):
        return True
    if hasattr(exc, "code") and exc.code in (429, 503):
        return True
    if hasattr(exc, "status_code") and exc.status_code in (429, 503):
        return True
    # 404 for deprecated models — not retryable, fail fast
    if hasattr(exc, "code") and exc.code == 404:
        return False
    if hasattr(exc, "status_code") and exc.status_code == 404:
        return False
    return False


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self._configured = False

    def _ensure_configured(self):
        if not self._configured and self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True

    def _get_model(self, model: Optional[str] = None, system_instruction: Optional[str] = None):
        self._ensure_configured()
        return genai.GenerativeModel(
            model or self.model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            system_instruction=system_instruction,
        )

    def count_tokens(self, text: str) -> int:
        self._ensure_configured()
        model = self._get_model()
        return model.count_tokens(text).total_tokens

    @retry(
        wait=wait_exponential(multiplier=2, min=5, max=120),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_retryable_error),
    )
    async def _generate_with_retry(
        self,
        prompt: str,
        model_obj,
        gen_config: GenerationConfig,
    ):
        return await model_obj.generate_content_async(prompt, generation_config=gen_config)

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
            format_json = (response_mime_type == "application/json")
            text = await ask_brain(prompt, system_prompt=system_prompt, format_json=format_json)
            return {
                "text": text,
                "tokens_in": len(prompt.split()),
                "tokens_out": len(text.split()),
                "raw": None,
            }

        self._ensure_configured()

        full_prompt = prompt
        model_obj = self._get_model(model, system_instruction=system_prompt)

        gen_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )

        candidate_models = [
            model or self.model_name,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash"
        ]
        response = None
        last_error = None
        for m_name in candidate_models:
            try:
                m_obj = self._get_model(m_name, system_instruction=system_prompt)
                response = await self._generate_with_retry(full_prompt, m_obj, gen_config)
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
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = response.usage_metadata.candidates_token_count or 0

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
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
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

    @retry(
        wait=wait_exponential(multiplier=2, min=5, max=120),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_retryable_error),
    )
    async def _generate_vision_with_retry(
        self,
        parts: List,
        model_obj,
        gen_config: GenerationConfig,
    ):
        return await model_obj.generate_content_async(parts, generation_config=gen_config)

    async def generate_with_vision(
        self,
        prompt: str,
        image_paths: List[str],
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        self._ensure_configured()

        model_obj = self._get_model(model or settings.gemini_vision_model)

        files = []
        for path in image_paths:
            file_obj = genai.upload_file(path)
            files.append(file_obj)

        parts = [prompt] + files

        gen_config = GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
        response = await self._generate_vision_with_retry(parts, model_obj, gen_config)

        tokens_in = 0
        tokens_out = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = response.usage_metadata.candidates_token_count or 0

        try:
            text = response.text or ""
        except ValueError as e:
            text = ""
            print(f"Safety filter blocked response: {e}")

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
        self._ensure_configured()

        full_prompt = prompt
        model_obj = self._get_model(model, system_instruction=system_prompt)
        response = await model_obj.generate_content_async(
            full_prompt,
            generation_config=GenerationConfig(temperature=temperature),
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client(api_key: Optional[str] = None, model: Optional[str] = None) -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient(api_key=api_key, model=model)
    return _gemini_client