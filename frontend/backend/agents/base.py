from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
from backend.agents.llm_client import GeminiClient
from backend.vault.repository import Repository
from backend.vault.models import StageStatus

@dataclass
class AgentResult:
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    tokens: int = 0
    cost: float = 0.0
    duration: float = 0.0

@dataclass
class JobData:
    id: int
    niche: str
    status: str
    current_stage: StageStatus
    config: Dict[str, Any] = field(default_factory=dict)
    assets: Dict[str, Any] = field(default_factory=dict)

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.llm = GeminiClient()
        self.tools = {}

    def register_tool(self, name: str, func):
        self.tools[name] = func

    async def run(self, job: JobData) -> AgentResult:
        start_time = time.time()
        try:
            result = await self._run_impl(job)
            result.duration = round(time.time() - start_time, 2)
            await Repository.record_cost(job.id, self.name, result.tokens, result.cost)
            await Repository.create_stage(job.id, job.current_stage, result.output)
            await Repository.log_event(
                f"Agent {self.name} completed stage {job.current_stage.value} with success={result.success}",
                job_id=job.id
            )
            return result
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            await Repository.log_event(f"Agent {self.name} failed: {str(e)}", job_id=job.id)
            return AgentResult(success=False, output={}, error=str(e), duration=duration)

    async def _run_impl(self, job: JobData) -> AgentResult:
        raise NotImplementedError("Agents must implement _run_impl")
