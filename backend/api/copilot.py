from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str = 'You are an AI assistant.'

@router.post('/chat')
async def copilot_chat(req: ChatRequest):
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    # We will use the model name we create in Ollama
    payload = {
        "model": "copilot-brain",
        "prompt": req.prompt,
        "system": req.system_prompt,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return {'response': data.get('response', '')}
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Ollama. Make sure it is running! Error: {str(e)}")


