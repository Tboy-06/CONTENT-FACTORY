from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.vault import get_latest_asset, log_event
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()


class QualityControlAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="check_originality",
                description="Check script/video originality against references",
                parameters={
                    "type": "object",
                    "properties": {
                        "script": {"type": "object"},
                        "references": {"type": "array", "items": {"type": "object"}},
                        "threshold": {"type": "number", "default": 0.3},
                    },
                    "required": ["script", "references"],
                },
                handler=self._check_originality,
            ),
            Tool(
                name="check_policy_compliance",
                description="Check content against platform policy risks",
                parameters={
                    "type": "object",
                    "properties": {
                        "script": {"type": "object"},
                        "platforms": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["script", "platforms"],
                },
                handler=self._check_policy_compliance,
            ),
            Tool(
                name="check_av_sync",
                description="Verify audio/video sync and caption accuracy",
                parameters={
                    "type": "object",
                    "properties": {
                        "video_path": {"type": "string"},
                        "captions": {"type": "array"},
                    },
                    "required": ["video_path"],
                },
                handler=self._check_av_sync,
            ),
            Tool(
                name="check_brand_consistency",
                description="Verify brand consistency (fonts, colors, tone)",
                parameters={
                    "type": "object",
                    "properties": {
                        "assets": {"type": "object"},
                        "brand_guide": {"type": "object"},
                    },
                    "required": ["assets"],
                },
                handler=self._check_brand_consistency,
            ),
            Tool(
                name="validate_structured_output",
                description="Validate agent outputs match expected schemas",
                parameters={
                    "type": "object",
                    "properties": {
                        "output": {"type": "object"},
                        "schema": {"type": "object"},
                    },
                    "required": ["output", "schema"],
                },
                handler=self._validate_structured_output,
            ),
            Tool(
                name="check_retention_risk",
                description="Check for retention risk flags (weak hook, early drop, missing CTA)",
                parameters={
                    "type": "object",
                    "properties": {
                        "script": {"type": "object"},
                        "shot_list": {"type": "array"},
                    },
                    "required": ["script", "shot_list"],
                },
                handler=self._check_retention_risk,
            ),
        ]
        super().__init__(agent_id="quality_control", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        stage = context.get("stage", "QC1")
        await log_event("INFO", self.agent_id, f"Quality control ({stage}) for job {job.id}", {"job_id": job.id})

        # Get assets based on stage
        script_asset = await get_latest_asset(job.id, "script")
        if not script_asset:
            return AgentResult(success=False, error="No script asset found")

        script = script_asset.metadata_json
        references = []

        # Get reference assets for originality check
        if stage == "QC1":
            research_assets = await get_latest_asset(job.id, "research_brief")
            # Would get all research briefs - simplified
            references = []

        # Run checks
        results = {}
        all_passed = True

        # 1. Originality check
        orig_result = await self.call_tool("check_originality", script=script, references=references)
        results["originality"] = orig_result
        if orig_result.get("verdict") == "FAIL":
            all_passed = False

        # 2. Policy compliance
        platforms = job.config.get("platforms", ["tiktok", "youtube"])
        policy_result = await self.call_tool("check_policy_compliance", script=script, platforms=platforms)
        results["policy"] = policy_result
        if policy_result.get("verdict") == "FAIL":
            all_passed = False

        # 3. Structured output validation
        schema = self._get_script_schema()
        struct_result = await self.call_tool("validate_structured_output", output=script, schema=schema)
        results["structured_output"] = struct_result
        if struct_result.get("verdict") == "FAIL":
            all_passed = False

        # 4. Retention risk (if shot list available)
        if stage == "QC2":
            shot_list_asset = await get_latest_asset(job.id, "shot_list")
            if shot_list_asset:
                retention_result = await self.call_tool("check_retention_risk", script=script, shot_list=shot_list_asset.metadata_json.get("shots", []))
                results["retention_risk"] = retention_result
                if retention_result.get("verdict") == "FAIL":
                    all_passed = False

        # 5. Brand consistency (if brand guide exists)
        # brand_result = await self.call_tool("check_brand_consistency", assets={}, brand_guide={})
        # results["brand"] = brand_result

        verdict = "PASS" if all_passed else "FAIL"
        uncertain = any(r.get("verdict") == "UNCERTAIN" for r in results.values())
        if uncertain and verdict == "PASS":
            verdict = "UNCERTAIN"

        return AgentResult(
            success=(verdict != "FAIL"),
            output={"verdict": verdict, "checks": results, "stage": stage},
            error=None if verdict != "FAIL" else f"QC failed: {', '.join([k for k, v in results.items() if v.get('verdict') == 'FAIL'])}",
        )

    def _get_script_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["hook", "beats", "captions", "cta", "hashtags", "title"],
            "properties": {
                "hook": {"type": "string", "minLength": 10},
                "beats": {"type": "array", "minItems": 3, "items": {"type": "object", "required": ["time", "text", "visual_cue"]}},
                "captions": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["start", "end", "text"]}},
                "cta": {"type": "string", "minLength": 5},
                "hashtags": {"type": "array", "minItems": 3, "items": {"type": "string"}},
                "title": {"type": "string", "minLength": 5},
                "variant_type": {"type": "string"},
            },
        }

    async def _check_originality(self, script: Dict, references: List[Dict], threshold: float = 0.3) -> Dict[str, Any]:
        script_text = " ".join([beat.get("text", "") for beat in script.get("beats", [])])
        script_text += " " + script.get("hook", "") + " " + script.get("cta", "")

        max_similarity = 0.0
        most_similar = None

        for ref in references:
            ref_text = ref.get("title", "") + " " + ref.get("description", "")
            if not ref_text.strip():
                continue
            similarity = SequenceMatcher(None, script_text.lower(), ref_text.lower()).ratio()
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar = ref.get("title", "Unknown")

        verdict = "PASS" if max_similarity < threshold else "FAIL"
        if max_similarity > threshold * 0.7:
            verdict = "UNCERTAIN"

        return {
            "verdict": verdict,
            "max_similarity": round(max_similarity, 3),
            "threshold": threshold,
            "most_similar_reference": most_similar,
            "details": f"Script similarity to references: {max_similarity:.1%} (threshold: {threshold:.0%})",
        }

    async def _check_policy_compliance(self, script: Dict, platforms: List[str]) -> Dict[str, Any]:
        # Platform-specific banned words/phrases
        platform_policies = {
            "tiktok": {
                "banned": ["click link in bio", "follow for part 2", "fake giveaway", "guaranteed money", "get rich quick"],
                "restricted": ["medical advice", "financial advice", "legal advice"],
                "disclosure_required": ["#ad", "#sponsored", "#affiliate"],
            },
            "youtube": {
                "banned": ["sub bot", "view bot", "misleading title", "scam"],
                "restricted": ["dangerous activities", "harmful content"],
                "disclosure_required": ["#ad", "#sponsored"],
            },
            "instagram": {
                "banned": ["follow for follow", "like for like", "fake engagement"],
                "restricted": ["before/after weight loss", "medical claims"],
                "disclosure_required": ["#ad", "#sponsored", "#partner"],
            },
        }

        script_text = " ".join([
            script.get("hook", ""),
            script.get("cta", ""),
            *[beat.get("text", "") for beat in script.get("beats", [])]
        ]).lower()

        violations = []
        warnings = []

        for platform in platforms:
            policy = platform_policies.get(platform, {})
            for banned in policy.get("banned", []):
                if banned.lower() in script_text:
                    violations.append(f"{platform}: banned phrase '{banned}'")
            for restricted in policy.get("restricted", []):
                if restricted.lower() in script_text:
                    warnings.append(f"{platform}: restricted topic '{restricted}'")
            for disclosure in policy.get("disclosure_required", []):
                if disclosure not in script_text:
                    warnings.append(f"{platform}: missing disclosure '{disclosure}'")

        verdict = "FAIL" if violations else ("UNCERTAIN" if warnings else "PASS")

        return {
            "verdict": verdict,
            "violations": violations,
            "warnings": warnings,
            "details": f"Checked {len(platforms)} platforms. Violations: {len(violations)}, Warnings: {len(warnings)}",
        }

    async def _check_av_sync(self, video_path: str, captions: List[Dict]) -> Dict[str, Any]:
        # Placeholder - would use ffprobe to check audio/video sync
        return {
            "verdict": "PASS",
            "details": "AV sync check not fully implemented - placeholder",
            "checks": ["duration_match", "caption_timing", "audio_presence"],
        }

    async def _check_brand_consistency(self, assets: Dict, brand_guide: Dict) -> Dict[str, Any]:
        # Placeholder for brand consistency checks
        return {
            "verdict": "PASS",
            "details": "Brand consistency check not fully implemented - placeholder",
        }

    async def _validate_structured_output(self, output: Dict, schema: Dict) -> Dict[str, Any]:
        """Validate output against JSON schema using basic checks."""
        errors = []

        def check_required(obj: Dict, required: List[str], path: str = ""):
            for field in required:
                if field not in obj:
                    errors.append(f"{path}.{field}: required field missing")
                elif obj[field] is None:
                    errors.append(f"{path}.{field}: value is null")

        def check_type(obj: Dict, field: str, expected_type: str, path: str = ""):
            if field in obj and obj[field] is not None:
                type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
                if expected_type in type_map:
                    if not isinstance(obj[field], type_map[expected_type]):
                        errors.append(f"{path}.{field}: expected {expected_type}, got {type(obj[field]).__name__}")

        check_required(output, schema.get("required", []))
        for field, field_schema in schema.get("properties", {}).items():
            if field in output:
                check_type(output, field, field_schema.get("type", ""), field)
                if field_schema.get("type") == "array" and isinstance(output[field], list):
                    min_items = field_schema.get("minItems")
                    if min_items and len(output[field]) < min_items:
                        errors.append(f"{field}: array has {len(output[field])} items, minimum {min_items} required")
                if field_schema.get("type") == "string" and isinstance(output[field], str):
                    min_len = field_schema.get("minLength")
                    if min_len and len(output[field]) < min_len:
                        errors.append(f"{field}: string length {len(output[field])} < minimum {min_len}")

        verdict = "FAIL" if errors else "PASS"
        return {
            "verdict": verdict,
            "errors": errors,
            "details": f"Schema validation: {len(errors)} errors" if errors else "Schema validation passed",
        }

    async def _check_retention_risk(self, script: Dict, shot_list: List[Dict]) -> Dict[str, Any]:
        risks = []

        # Check hook strength (first 3 seconds)
        hook = script.get("hook", "")
        if len(hook) < 20:
            risks.append({"type": "weak_hook", "severity": "high", "message": "Hook text very short (<20 chars), may not grab attention in 3s"})
        elif not any(w in hook.lower() for w in ["you", "your", "how", "why", "what", "secret", "mistake", "stop", "warning"]):
            risks.append({"type": "weak_hook", "severity": "medium", "message": "Hook lacks direct address or curiosity trigger"})

        # Check for early drop risk (no visual change in first 10s)
        early_shots = [s for s in shot_list if s.get("time_end", 0) <= 10]
        if len(early_shots) < 2:
            risks.append({"type": "static_early", "severity": "medium", "message": "Fewer than 2 visual changes in first 10s, risk of early drop"})

        # Check CTA presence
        cta = script.get("cta", "")
        if not cta or len(cta) < 10:
            risks.append({"type": "missing_cta", "severity": "high", "message": "CTA missing or too short (<10 chars)"})

        # Check caption coverage
        captions = script.get("captions", [])
        total_caption_time = sum(c.get("end", 0) - c.get("start", 0) for c in captions)
        if shot_list:
            total_duration = max(s.get("time_end", 0) for s in shot_list)
            caption_coverage = total_caption_time / total_duration if total_duration > 0 else 0
            if caption_coverage < 0.8:
                risks.append({"type": "low_caption_coverage", "severity": "medium", "message": f"Captions cover only {caption_coverage:.0%} of video duration"})

        verdict = "FAIL" if any(r["severity"] == "high" for r in risks) else ("UNCERTAIN" if risks else "PASS")

        return {
            "verdict": verdict,
            "risks": risks,
            "details": f"Retention risk check: {len(risks)} flags ({sum(1 for r in risks if r['severity']=='high')} high, {sum(1 for r in risks if r['severity']=='medium')} medium)",
        }