from __future__ import annotations

import json
import tempfile
import os
from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.tools.gemini_vision import get_gemini_vision
from backend.vault import add_asset, get_latest_asset, list_hook_formulas, create_hook_formula, log_event
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()
vision = get_gemini_vision()


class StyleAnalystAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="analyze_reference_video",
                description="Analyze a reference video file/URL and extract style DNA",
                parameters={
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "YouTube URL or local file path"},
                        "custom_prompt": {"type": "string", "description": "Optional custom analysis prompt"},
                    },
                    "required": ["video_url"],
                },
                handler=self._analyze_reference_video,
            ),
            Tool(
                name="extract_hook_formula",
                description="Extract and save a hook formula from style analysis",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "pattern": {"type": "string"},
                        "platform": {"type": "string"},
                        "retention_data": {"type": "object"},
                    },
                    "required": ["name", "pattern", "platform"],
                },
                handler=self._extract_hook_formula,
            ),
            Tool(
                name="extract_character_ref_specs",
                description="Extract character reference specifications for Flow/Veo",
                parameters={
                    "type": "object",
                    "properties": {
                        "style_guide_id": {"type": "integer"},
                    },
                    "required": ["style_guide_id"],
                },
                handler=self._extract_character_ref_specs,
            ),
        ]
        super().__init__(agent_id="style_analyst", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        config = job.config
        style_reference = config.get("style_reference")

        if not style_reference:
            return AgentResult(success=False, error="No style_reference in job config")

        await log_event("INFO", self.agent_id, f"Analyzing style reference: {style_reference}", {"job_id": job.id})

        # Analyze the reference video
        analysis = await self.call_tool("analyze_reference_video", video_url=style_reference)

        if "error" in analysis:
            return AgentResult(success=False, error=analysis["error"])

        # Save style guide
        from backend.vault.repository import create_style_guide
        style_guide = await create_style_guide(
            name=f"style_{job.id}",
            source_video_url=style_reference,
            extracted=analysis,
        )

        # Extract and save hook formulas
        hook_formula = analysis.get("hook_formula", {})
        if hook_formula.get("pattern"):
            await self.call_tool("extract_hook_formula", name=f"hook_{job.id}", pattern=hook_formula["pattern"], platform="tiktok", retention_data=hook_formula)

        # Extract character reference specs
        char_ref = await self.call_tool("extract_character_ref_specs", style_guide_id=style_guide.id)

        # Save style guide as asset
        await add_asset(
            job_id=job.id,
            asset_type="style_guide",
            path=f"style_guides/style_{job.id}.json",
            metadata={"style_guide_id": style_guide.id, "analysis": analysis, "character_ref": char_ref},
        )

        return AgentResult(
            success=True,
            output={"style_guide_id": style_guide.id, "analysis": analysis, "character_ref": char_ref},
        )

    async def _analyze_reference_video(self, video_url: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        # If it's a YouTube URL, we'd need to download first
        # For now, assume local file path or direct video URL
        if video_url.startswith("http"):
            # TODO: Add yt-dlp download
            return {"error": "YouTube URLs not yet supported - provide local file path"}

        # Analyze local video file
        return await vision.analyze_video_style(video_url, custom_prompt)

    async def _extract_hook_formula(self, name: str, pattern: str, platform: str, retention_data: Dict[str, Any]) -> Dict[str, Any]:
        hook = await create_hook_formula(name=name, pattern=pattern, platform=platform, retention_data=retention_data)
        return {"success": True, "hook_formula_id": hook.id}

    async def _extract_character_ref_specs(self, style_guide_id: int) -> Dict[str, Any]:
        # Get the style guide
        from backend.vault.repository import get_session
        from backend.vault.models import StyleGuide
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(select(StyleGuide).where(StyleGuide.id == style_guide_id))
            guide = result.scalar_one_or_none()

        if not guide:
            return {"error": "Style guide not found"}

        extracted = guide.extracted_json
        char_design = extracted.get("character_design", {})
        visual_style = extracted.get("visual_style", {})

        char_ref_specs = {
            "style": char_design.get("style", "cartoon"),
            "proportions": char_design.get("proportions", "exaggerated"),
            "key_features": char_design.get("key_features", []),
            "color_palette": visual_style.get("color_palette", ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFBE0B"]),
            "consistency_markers": char_design.get("consistency_markers", []),
            "flow_prompts": {
                "character_sheet": f"Character turnaround sheet: {char_design.get('style', 'cartoon')} style, {char_design.get('proportions', 'normal')} proportions, features: {', '.join(char_design.get('key_features', []))}, color palette: {', '.join(visual_style.get('color_palette', []))}",
                "expressions": "Character expression sheet: 8 expressions (happy, surprised, thinking, concerned, excited, neutral, sad, confident), same character design",
                "poses": "Character pose sheet: 6 poses (standing, sitting, walking, pointing, typing, celebrating), consistent proportions and colors",
            },
            "scene_style_prompts": {
                "intro": f"{visual_style.get('camera_style', 'static')} shot, {visual_style.get('lighting', 'natural')} lighting, {visual_style.get('composition_rules', ['centered'])[0]} composition",
                "problem": "Close-up shot, dramatic lighting, centered composition, tension",
                "solution": "Medium shot, bright lighting, rule of thirds, positive energy",
                "demo": "Screen capture style, clean composition, clear visual hierarchy",
                "cta": "Direct address to camera, warm lighting, engaging eye contact",
            }
        }

        return char_ref_specs