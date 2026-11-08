from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.vault import create_job, create_stage, get_job, update_job_status
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()


class ManagerAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="create_job",
                description="Create a new content job from a goal",
                parameters={
                    "type": "object",
                    "properties": {
                        "niche": {"type": "string", "description": "Content niche (e.g., finance, tech, health)"},
                        "frequency": {"type": "integer", "description": "Videos per week"},
                        "platforms": {"type": "array", "items": {"type": "string"}, "description": "Target platforms"},
                        "style_reference": {"type": "string", "description": "Optional reference video URL for style"},
                    },
                    "required": ["niche", "frequency", "platforms"],
                },
                handler=self._create_job,
            ),
            Tool(
                name="assign_stage",
                description="Assign next stage to a job",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "stage_name": {"type": "string"},
                    },
                    "required": ["job_id", "stage_name"],
                },
                handler=self._assign_stage,
            ),
            Tool(
                name="escalate",
                description="Escalate job to human via Telegram",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": ["job_id", "reason"],
                },
                handler=self._escalate,
            ),
            Tool(
                name="notify_telegram",
                description="Send notification to Telegram",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "job_id": {"type": "integer", "description": "Optional job ID"},
                    },
                    "required": ["message"],
                },
                handler=self._notify_telegram,
            ),
        ]
        super().__init__(agent_id="manager", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        goal = context.get("goal")
        if not goal:
            return AgentResult(success=False, error="No goal provided in context")

        niche = goal.get("niche")
        frequency = goal.get("frequency", 3)
        platforms = goal.get("platforms", ["tiktok", "youtube"])
        style_reference = goal.get("style_reference")

        # Create the job
        config = {
            "frequency": frequency,
            "platforms": platforms,
            "style_reference": style_reference,
            "approval_mode": settings.default_approval_mode,
        }

        new_job = await create_job(niche=niche, config=config, priority=goal.get("priority", 0))

        # Create initial IDEA stage
        await create_stage(new_job.id, "IDEA", agent_id="manager", input_data={"goal": goal})

        # Notify
        await self._notify_telegram(
            message=f"🎯 New goal accepted: {frequency} {niche} videos/week on {', '.join(platforms)}",
            job_id=new_job.id,
        )

        return AgentResult(
            success=True,
            output={"job_id": new_job.id, "status": "created"},
            tokens_in=0,
            tokens_out=0,
        )

    async def _create_job(self, niche: str, frequency: int, platforms: List[str], style_reference: Optional[str] = None) -> Dict[str, Any]:
        # This is called by the tool system
        config = {
            "frequency": frequency,
            "platforms": platforms,
            "style_reference": style_reference,
        }
        job = await create_job(niche=niche, config=config)
        return {"job_id": job.id}

    async def _assign_stage(self, job_id: int, stage_name: str) -> Dict[str, Any]:
        job = await get_job(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        await create_stage(job_id, stage_name)
        return {"success": True}

    async def _escalate(self, job_id: int, reason: str) -> Dict[str, Any]:
        await self._notify_telegram(
            message=f"⚠️ Escalation for job {job_id}: {reason}",
            job_id=job_id,
        )
        return {"success": True}

    async def _notify_telegram(self, message: str, job_id: Optional[int] = None) -> Dict[str, Any]:
        # Actual Telegram sending is handled by the bot module
        # This just logs the notification request
        from backend.vault import log_event
        await log_event("INFO", "manager", f"Telegram notification queued: {message}", {"job_id": job_id})
        return {"success": True}