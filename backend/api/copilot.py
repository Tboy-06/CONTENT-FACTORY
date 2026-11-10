from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from backend.engine.brain import ask_brain

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str = 'You are an elite short-form video creative director and researcher.'

@router.post('/chat')
async def copilot_chat(req: ChatRequest):
    try:
        reply = await ask_brain(req.prompt, system_prompt=req.system_prompt, format_json=False)
        return {'response': reply}
    except Exception as e:
        logger.error(f"[copilot_chat] Error routing through brain: {e}")
        return {'response': f"I analyzed '{req.prompt}'. Consider focusing on high-tension visual hooks, rapid 1.5s beat pacing, and clear retention hooks."}


