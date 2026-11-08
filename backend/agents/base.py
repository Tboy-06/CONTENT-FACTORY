from __future__ import annotations

import abc
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from backend.config import get_settings
from backend.vault import log_event
from backend.vault.repository import record_cost

settings = get_settings()


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Awaitable[Any]]


@dataclass
class AgentResult:
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0


class BaseAgent(abc.ABC):
    def __init__(
        self,
        agent_id: str,
        tools: Optional[List[Tool]] = None,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.agent_id = agent_id
        self.tools = {t.name: t for t in (tools or [])}
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._llm_client = None

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = self._create_llm_client()
        return self._llm_client

    @abc.abstractmethod
    def _create_llm_client(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def _run_impl(self, job: "Job", context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError

    async def run(self, job: "Job", context: Optional[Dict[str, Any]] = None) -> AgentResult:
        ctx = context or {}
        ctx.update({"job_id": job.id, "agent_id": self.agent_id})

        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                await log_event("INFO", self.agent_id, f"Starting attempt {attempt + 1}/{self.max_retries + 1}", ctx)
                result = await self._run_impl(job, ctx)
                duration_ms = int((time.time() - start_time) * 1000)

                if result.success:
                    await log_event(
                        "INFO",
                        self.agent_id,
                        f"Completed successfully in {duration_ms}ms",
                        {**ctx, "duration_ms": duration_ms, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out},
                    )
                    if result.cost_usd > 0:
                        await record_cost(
                            job_id=job.id,
                            provider="gemini",
                            operation=self.agent_id,
                            tokens_in=result.tokens_in,
                            tokens_out=result.tokens_out,
                            usd_estimate=result.cost_usd,
                        )
                    return AgentResult(
                        success=True,
                        output=result.output,
                        tokens_in=result.tokens_in,
                        tokens_out=result.tokens_out,
                        cost_usd=result.cost_usd,
                        duration_ms=duration_ms,
                    )
                else:
                    last_error = result.error
                    await log_event("WARNING", self.agent_id, f"Attempt failed: {last_error}", ctx)

            except Exception as e:
                last_error = str(e)
                await log_event("ERROR", self.agent_id, f"Exception on attempt {attempt + 1}: {e}", ctx)

            if attempt < self.max_retries:
                wait_time = self.retry_backoff * (2 ** attempt)
                await log_event("INFO", self.agent_id, f"Retrying in {wait_time}s...", ctx)
                await asyncio.sleep(wait_time)

        duration_ms = int((time.time() - start_time) * 1000)
        await log_event("ERROR", self.agent_id, f"All attempts failed: {last_error}", {**ctx, "duration_ms": duration_ms})
        return AgentResult(
            success=False,
            error=last_error or "Max retries exceeded",
            duration_ms=duration_ms,
        )

    async def call_tool(self, name: str, **kwargs) -> Any:
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not available for agent {self.agent_id}")
        tool = self.tools[name]
        return await tool.handler(**kwargs)

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        return 0.0


class Job:
    def __init__(self, id: int, niche: str, status: str, current_stage: str, config: Dict[str, Any]):
        self.id = id
        self.niche = niche
        self.status = status
        self.current_stage = current_stage
        self.config = config
        self._assets: Dict[str, Any] = {}

    def get_asset(self, key: str) -> Any:
        return self._assets.get(key)

    def set_asset(self, key: str, value: Any) -> None:
        self._assets[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)