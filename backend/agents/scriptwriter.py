from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.vault import add_asset, get_job_assets, list_hook_formulas
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()


class ScriptwriterAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="apply_hook_formula",
                description="Apply a proven hook formula to a script",
                parameters={
                    "type": "object",
                    "properties": {
                        "formula_name": {"type": "string"},
                        "topic": {"type": "string"},
                        "angle": {"type": "string"},
                    },
                    "required": ["formula_name", "topic"],
                },
                handler=self._apply_hook_formula,
            ),
            Tool(
                name="format_per_platform",
                description="Format script for specific platform",
                parameters={
                    "type": "object",
                    "properties": {
                        "script": {"type": "object"},
                        "platform": {"type": "string", "enum": ["tiktok", "youtube", "instagram", "x", "linkedin"]},
                    },
                    "required": ["script", "platform"],
                },
                handler=self._format_per_platform,
            ),
        ]
        super().__init__(agent_id="scriptwriter", tools=tools)

    async def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        # Get research briefs
        briefs = await get_job_assets(job.id, asset_type="research_brief")
        if not briefs:
            return AgentResult(success=False, error="No research briefs found")

        # Get hook formulas
        hook_formulas = await list_hook_formulas(limit=20)

        all_scripts = []
        for brief in briefs[:1]:  # Limit to 1 brief to prevent LLM rate limit storms
            meta = brief.metadata_json
            topic = meta.get("topic", "")
            angle = meta.get("angle", "")
            virality_score = meta.get("virality_score", 50)
            mode = job.config.get("mode", "Generate from Scratch")

            # Select best hook formula for this platform
            platform = job.config.get("platforms", ["tiktok"])[0]
            
            if mode == "Remix & Spin (Copyright Bypass)":
                variants = await self._generate_remix_variant(topic, brief, platform)
                all_scripts.extend(variants)
            elif mode == "Clone a Video (Template Extraction)":
                variants = await self._generate_clone_variant(topic, brief, platform)
                all_scripts.extend(variants)
            else:
                best_formula = self._select_formula(hook_formulas, platform, virality_score)
                # Generate script variants
                variants = await self._generate_variants(topic, angle, best_formula, platform, virality_score)
                all_scripts.extend(variants)

        # Save scripts as assets
        for i, script in enumerate(all_scripts):
            await add_asset(
                job_id=job.id,
                asset_type="script",
                path=f"scripts/script_{i+1}.json",
                metadata=script,
            )

        return AgentResult(
            success=True,
            output={"scripts_count": len(all_scripts), "scripts": all_scripts},
        )

    def _select_formula(self, formulas: List, platform: str, score: int) -> Dict[str, Any]:
        # Prefer platform-specific formulas, then high-retention ones
        platform_formulas = [f for f in formulas if f.platform == platform]
        if platform_formulas:
            return max(platform_formulas, key=lambda f: f.retention_data_json.get("avg_retention", 0))
        return formulas[0] if formulas else {"name": "Problem-Agitate-Solution", "pattern": "Problem → Agitate → Solution → Proof → CTA"}

    async def _generate_variants(
        self,
        topic: str,
        angle: str,
        formula: Dict[str, Any],
        platform: str,
        virality_score: int,
    ) -> List[Dict[str, Any]]:
        variants = []

        # Variant 1: Direct formula application
        v1 = await self._apply_hook_formula(
            formula_name=getattr(formula, "name", "Problem-Agitate-Solution"),
            topic=topic,
            angle=angle,
            platform=platform,
        )
        if v1.get("success") and v1.get("data"):
            v1_data = v1["data"]
            v1_data["variant"] = "formula_direct"
            v1_data["platform"] = platform
            variants.append(v1_data)

        return variants

    async def _generate_remix_variant(self, topic: str, brief: Any, platform: str) -> List[Dict[str, Any]]:
        prompt = f"""
        CRITICAL INSTRUCTION: You MUST provide at least 3 beats, at least 3 captions, and at least 3 hashtags. DO NOT OUTPUT EMPTY ARRAYS OR OBJECTS.

        Write a {platform}-optimized script by REMIXING and SPINNING the following topic from a reference video.
        
        Reference Video Topic: {topic}
        
        Requirements:
        - Completely paraphrase the core message to bypass copyright.
        - Create a totally new hook in first 3 seconds.
        - Same meaning, entirely different words.
        - Clear beats with timestamps.
        
        Return JSON structure as requested in schema.
        """
        result = await gemini.generate_structured(
            prompt=prompt,
            schema=self._get_script_schema(),
            system_prompt="You are an expert at paraphrasing and spinning video scripts.",
            temperature=0.8,
        )
        if result.get("success") and result.get("data"):
            data = result["data"]
            data["variant"] = "remix_spin"
            data["platform"] = platform
            return [data]
        return []

    async def _generate_clone_variant(self, topic: str, brief: Any, platform: str) -> List[Dict[str, Any]]:
        prompt = f"""
        CRITICAL INSTRUCTION: You MUST provide at least 3 beats, at least 3 captions, and at least 3 hashtags. DO NOT OUTPUT EMPTY ARRAYS OR OBJECTS.

        Write a {platform}-optimized script by CLONING the structure of the reference video but for a totally different niche or angle.
        
        Reference Video Topic: {topic}
        
        Requirements:
        - Analyze the pacing and structure (hook, problem, body, CTA).
        - Write a NEW script with the same structural template.
        - Clear beats with timestamps.
        
        Return JSON structure as requested in schema.
        """
        result = await gemini.generate_structured(
            prompt=prompt,
            schema=self._get_script_schema(),
            system_prompt="You are an expert at extracting pacing templates and applying them to new scripts.",
            temperature=0.8,
        )
        if result.get("success") and result.get("data"):
            data = result["data"]
            data["variant"] = "clone_video"
            data["platform"] = platform
            return [data]
        return []

    def _get_script_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hook": {"type": "string"},
                "beats": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "time": {"type": "string"},
                            "text": {"type": "string"},
                            "visual_cue": {"type": "string"}
                        },
                        "required": ["time", "text", "visual_cue"]
                    }
                },
                "captions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "number"},
                            "end": {"type": "number"},
                            "text": {"type": "string"}
                        },
                        "required": ["start", "end", "text"]
                    }
                },
                "cta": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "title": {"type": "string"},
                "variant_type": {"type": "string"},
            },
            "required": ["hook", "beats", "captions", "cta", "hashtags", "title", "variant_type"],
        }

    async def _apply_hook_formula(self, formula_name: str, topic: str, angle: str, platform: str) -> Dict[str, Any]:
        formula_obj = None
        # Would fetch from vault - for now use defaults
        formulas = {
            "Problem-Agitate-Solution": "Hook: State the problem → Agitate the pain → Reveal solution → Proof → CTA",
            "Question-Curiosity": "Hook: Ask a compelling question → Build curiosity → Answer → Value → CTA",
            "Story-Transformation": "Hook: Start with transformation result → Flashback to struggle → Journey → Lesson → CTA",
            "Contrarian": "Hook: State controversial opinion → Explain why → Evidence → Nuanced take → CTA",
            "Listicle-Promise": "Hook: Number + outcome promise → Quick items → Best one last → CTA",
        }
        pattern = formulas.get(formula_name, formulas["Problem-Agitate-Solution"])

        prompt = f"""
        CRITICAL INSTRUCTION: You MUST provide at least 3 beats, at least 3 captions, and at least 3 hashtags. DO NOT OUTPUT EMPTY ARRAYS OR OBJECTS.

        Write a {platform}-optimized script using this hook formula:
        
        Formula: {formula_name}
        Pattern: {pattern}
        
        Topic: {topic}
        Angle: {angle}
        
        Requirements:
        - Hook in first 3 seconds
        - Clear beats with timestamps
        - Platform-native style (fast for TikTok, deeper for YouTube)
        - Word-level caption timing cues
        - Strong CTA at end
        
        Return JSON:
        {{
            "hook": "exact first 3 seconds text",
            "beats": [
                {{"time": "0-3s", "text": "...", "visual_cue": "..."}},
                {{"time": "3-10s", "text": "...", "visual_cue": "..."}}
            ],
            "captions": [{{"start": 0.0, "end": 3.0, "text": "..."}}],
            "cta": "exact CTA text",
            "hashtags": ["#tag1", "#tag2"],
            "title": "video title",
            "variant_type": "formula_direct"
        }}
        """
        result = await gemini.generate_structured(
            prompt=prompt,
            schema=self._get_script_schema(),
            system_prompt="You are a viral scriptwriter. Write platform-native, high-retention scripts.",
            temperature=0.8,
        )
        return result

    async def _generate_story_variant(self, topic: str, angle: str, platform: str) -> Dict[str, Any]:
        prompt = f"""
        Write a {platform} script using STORY-TRANSFORMATION formula:
        Topic: {topic}
        Angle: {angle}
        
        Structure: Hook (result) → Flashback (struggle) → Journey → Lesson → CTA
        Return same JSON structure as above with variant_type: "story"
        """
        result = await gemini.generate_structured(
            prompt=prompt,
            schema=self._get_script_schema(),
            system_prompt="You are a viral scriptwriter. Write emotional, story-driven scripts.",
            temperature=0.9,
        )
        return result.get("data", {})

    async def _generate_listicle_variant(self, topic: str, angle: str, platform: str) -> Dict[str, Any]:
        prompt = f"""
        Write a {platform} script using LISTICLE formula:
        Topic: {topic}
        Angle: {angle}
        
        Structure: Number + Promise → Quick items (save best for last) → CTA
        Return same JSON structure with variant_type: "listicle"
        """
        result = await gemini.generate_structured(
            prompt=prompt,
            schema=self._get_script_schema(),
            system_prompt="You are a viral scriptwriter. Write punchy, scannable listicle scripts.",
            temperature=0.7,
        )
        return result.get("data", {})

    async def _format_per_platform(self, script: Dict[str, Any], platform: str) -> Dict[str, Any]:
        # Adjust script for platform specifics
        adjusted = script.copy()
        if platform == "tiktok":
            adjusted["max_duration"] = 60
            adjusted["caption_style"] = "fast_paced"
        elif platform == "youtube":
            adjusted["max_duration"] = 600
            adjusted["caption_style"] = "readable"
        elif platform == "instagram":
            adjusted["max_duration"] = 90
            adjusted["caption_style"] = "aesthetic"
        return adjusted