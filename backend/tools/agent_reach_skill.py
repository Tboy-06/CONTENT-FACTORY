from __future__ import annotations

import json
import subprocess
import tempfile
import os
from typing import Any, Dict, List, Optional

from backend.config import get_settings
from backend.vault import log_event

settings = get_settings()


class AgentReachSkill:
    def __init__(self):
        self.skills_dir = os.path.join(os.getcwd(), "skills")
        os.makedirs(self.skills_dir, exist_ok=True)

    def _get_claude_path(self) -> str:
        return "claude"  # Assumes claude CLI is in PATH

    async def install_skill(self, skill_name: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                [self._get_claude_path(), "skills", "install", skill_name],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                await log_event("INFO", "agent_reach", f"Installed skill: {skill_name}")
                return {"success": True, "output": result.stdout}
            else:
                await log_event("ERROR", "agent_reach", f"Install failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except Exception as e:
            await log_event("ERROR", "agent_reach", f"Install exception: {e}")
            return {"success": False, "error": str(e)}

    async def run_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Write params to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(params, f)
                param_file = f.name

            result = subprocess.run(
                [self._get_claude_path(), "skills", "run", skill_name, "--input", param_file],
                capture_output=True,
                text=True,
                timeout=120,
            )

            os.unlink(param_file)

            if result.returncode == 0:
                await log_event("INFO", "agent_reach", f"Ran skill: {skill_name}")
                try:
                    output = json.loads(result.stdout)
                    return {"success": True, "data": output}
                except json.JSONDecodeError:
                    return {"success": True, "raw": result.stdout}
            else:
                await log_event("ERROR", "agent_reach", f"Skill run failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except Exception as e:
            await log_event("ERROR", "agent_reach", f"Skill run exception: {e}")
            return {"success": False, "error": str(e)}

    async def list_skills(self) -> List[str]:
        try:
            result = subprocess.run(
                [self._get_claude_path(), "skills", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                skills = [line.strip() for line in result.stdout.split("\n") if line.strip()]
                return skills
            return []
        except Exception:
            return []

    async def get_builtin_skills(self) -> Dict[str, Dict[str, Any]]:
        return {
            "youtube-summarize": {
                "description": "Summarize a YouTube video from URL",
                "params": {"url": "string"},
            },
            "reddit-trends": {
                "description": "Get trending topics from Reddit",
                "params": {"subreddit": "string", "time_filter": "day|week|month"},
            },
            "web-scrape": {
                "description": "Scrape and summarize a web page",
                "params": {"url": "string"},
            },
            "github-trending": {
                "description": "Get trending GitHub repos",
                "params": {"language": "string", "since": "daily|weekly|monthly"},
            },
            "stock-data": {
                "description": "Get stock price and info",
                "params": {"symbol": "string"},
            },
        }


_agent_reach: Optional[AgentReachSkill] = None


def get_agent_reach() -> AgentReachSkill:
    global _agent_reach
    if _agent_reach is None:
        _agent_reach = AgentReachSkill()
    return _agent_reach