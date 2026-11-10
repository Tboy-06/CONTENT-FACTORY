import httpx
import json
import logging
from typing import Dict, Any, Optional

from backend.engine.brain import ask_brain

logger = logging.getLogger(__name__)

async def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Unified LLM caller routing through backend.engine.brain:
    Tries Ollama local brain -> Pollinations free cloud -> deterministic fallback.
    """
    return await ask_brain(prompt, system_prompt=system_prompt, format_json=False)

async def generate_script(niche: str, pipeline_mode: str = "Generate from Scratch", reference_url: str = None) -> Dict[str, Any]:
    """
    Calls a local Ollama model (llama3.1 or mistral) to generate a short-form video script.
    Returns a dictionary with 'title', 'hook', 'body', 'cta', and 'search_terms'.
    """
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    if pipeline_mode == "Remix & Spin (Copyright Bypass)":
        prompt = f"Analyze the underlying concept of this reference ({reference_url}) and write a completely new, paraphrased script around the same concept."
    elif pipeline_mode == "Clone a Video (Template Extraction)":
        prompt = f"Use the structure of {reference_url} but write a new script for the niche: {niche}."
    elif pipeline_mode == "URL-to-UGC Video (AI Actor)":
        prompt = f"Write a 60-second UGC (User Generated Content) style spokesperson script promoting the product/business at: {reference_url}. Make it feel natural and authentic, like a real person talking to camera."
    else:
        prompt = f"Write a highly engaging 60-second short-form video script about: {niche}. Ensure it has a strong 3-second hook."

    system_prompt = '''You are an expert short-form video scriptwriter. 
Output ONLY valid JSON in this format, with no markdown formatting or backticks:
{
  "title": "A catchy title",
  "hook": "The first 3 seconds spoken text",
  "body": "The main content spoken text",
  "cta": "The call to action spoken text",
  "search_terms": ["tag1", "tag2", "tag3"]
}'''

    try:
        raw_res = await ask_brain(prompt, system_prompt=system_prompt, format_json=True)
        import re
        match = re.search(r'\{.*\}', raw_res, re.DOTALL)
        if match:
            script_json = json.loads(match.group(0), strict=False)
            if "hook" in script_json:
                return script_json
        return {
            "title": niche,
            "hook": f"The hidden truth about {niche} that changes everything.",
            "body": raw_res if len(raw_res) < 300 else raw_res[:300],
            "cta": "Follow for more daily breakdowns.",
            "search_terms": [niche, "documentary", "viral"]
        }
    except Exception as e:
        logger.error(f"Error in generate_script routing through brain: {e}")
        return {
            "title": niche,
            "hook": f"Most people completely misunderstand {niche}.",
            "body": f"Here is the breakdown of {niche} and why it matters right now.",
            "cta": "Follow for more.",
            "search_terms": [niche]
        }
