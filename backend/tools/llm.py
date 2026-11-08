import httpx
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

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

    payload = {
        "model": "llama3.1", # Ensure the user has pulled this model in Ollama
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"Sending prompt to Ollama for niche: {niche}")
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            response_text = data.get('response', '{}')
            try:
                script_json = json.loads(response_text)
                return script_json
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Ollama: {response_text}")
                # Fallback empty structure
                return {"title": niche, "hook": "", "body": response_text, "cta": "", "search_terms": []}
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        # Return fallback on error
        return {
            "title": f"Fallback: {niche}",
            "hook": "Did you know this crazy fact?",
            "body": f"We are generating content about {niche}, but the AI is currently offline.",
            "cta": "Subscribe for more!",
            "search_terms": ["fallback"]
        }
