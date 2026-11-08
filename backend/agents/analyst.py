from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.agents.base import AgentResult, Job as AgentJob, BaseAgent
from backend.agents.llm_client import get_gemini_client
from backend.vault.repository import (
    get_job,
    get_jobs,
    get_job_analytics,
    get_analytics_by_niche,
    upsert_style_guide,
    upsert_hook_formula,
)


@dataclass
class RetentionPoint:
    timestamp: float
    retention_rate: float
    viewers: int


@dataclass
class PerformanceReport:
    job_id: int
    niche: str
    platform: str
    views: int
    likes: int
    comments: int
    shares: int
    retention_curve: List[RetentionPoint]
    avg_watch_time: float
    ctr: float
    revenue_estimate: float
    viral_score: float
    insights: List[str]
    recommendations: List[str]


class AnalystAgent(BaseAgent):
    name = "analyst"
    description = "Analyzes content performance, extracts insights, updates style guides"

    def __init__(self):
        super().__init__(agent_id="analyst")
        self.llm = get_gemini_client()

    async def _create_llm_client(self):
        return self.llm

    async def _run_impl(self, job: AgentJob, context: Dict[str, Any]) -> AgentResult:
        db_job = await get_job(job.id)
        if not db_job:
            return AgentResult(success=False, error="Job not found in DB")

        niche = (db_job.config_json or {}).get("niche", "finance")
        platform = (db_job.config_json or {}).get("platform", "tiktok")

        recent_jobs = await get_jobs(niche=niche, limit=50)
        completed_jobs = [j for j in recent_jobs if j.status.value == "completed"]

        if not completed_jobs:
            return AgentResult(
                success=True,
                output={"message": "No completed jobs to analyze yet"},
            )

        reports = []
        for completed_job in completed_jobs[:20]:
            analytics = await get_job_analytics(completed_job.id)
            if analytics:
                report = await self._analyze_job(completed_job, analytics)
                reports.append(report)

        if not reports:
            return AgentResult(
                success=True,
                output={"message": "No analytics data available yet"},
            )

        aggregate = self._aggregate_reports(reports)
        insights = await self._generate_insights(aggregate, niche)
        recommendations = await self._generate_recommendations(aggregate, niche)

        await self._update_style_guides(niche, insights, recommendations)
        await self._update_hook_formulas(niche, reports)

        return AgentResult(
            success=True,
            output={
                "analyzed_jobs": len(reports),
                "aggregate": aggregate,
                "insights": insights,
                "recommendations": recommendations,
            },
        )

    async def _analyze_job(self, job, analytics: List) -> PerformanceReport:
        latest = analytics[-1] if analytics else None
        if not latest:
            return PerformanceReport(
                job_id=job.id,
                niche=job.config.get("niche", ""),
                platform=job.config.get("platform", ""),
                views=0, likes=0, comments=0, shares=0,
                retention_curve=[], avg_watch_time=0, ctr=0,
                revenue_estimate=0, viral_score=0,
                insights=[], recommendations=[],
            )

        retention_curve = []
        if latest.raw_json and "retention_data" in latest.raw_json:
            for point in latest.raw_json["retention_data"]:
                retention_curve.append(RetentionPoint(
                    timestamp=point.get("timestamp", 0),
                    retention_rate=point.get("retention_rate", 0),
                    viewers=point.get("viewers", 0),
                ))

        viral_score = self._calculate_viral_score(latest)

        raw = latest.raw_json or {}
        return PerformanceReport(
            job_id=job.id,
            niche=job.config.get("niche", ""),
            platform=job.config.get("platform", ""),
            views=latest.views or 0,
            likes=raw.get("likes", 0),
            comments=raw.get("comments", 0),
            shares=raw.get("shares", 0),
            retention_curve=retention_curve,
            avg_watch_time=latest.watch_time_seconds or 0,
            ctr=latest.ctr or 0,
            revenue_estimate=latest.revenue_usd or 0,
            viral_score=viral_score,
            insights=[],
            recommendations=[],
        )

    def _calculate_viral_score(self, analytics) -> float:
        views = analytics.views or 1
        raw = analytics.raw_json or {}
        engagement = raw.get("likes", 0) + raw.get("comments", 0) * 2 + raw.get("shares", 0) * 3
        engagement_rate = engagement / views
        retention_bonus = (analytics.watch_time_seconds or 0) / 30.0
        ctr_bonus = (analytics.ctr or 0) * 10
        return min(100, (engagement_rate * 100) + retention_bonus + ctr_bonus)

    def _aggregate_reports(self, reports: List[PerformanceReport]) -> Dict[str, Any]:
        if not reports:
            return {}

        total_views = sum(r.views for r in reports)
        total_engagement = sum(r.likes + r.comments + r.shares for r in reports)
        avg_viral = sum(r.viral_score for r in reports) / len(reports)

        by_platform = {}
        for r in reports:
            if r.platform not in by_platform:
                by_platform[r.platform] = {"views": 0, "count": 0, "viral_sum": 0}
            by_platform[r.platform]["views"] += r.views
            by_platform[r.platform]["count"] += 1
            by_platform[r.platform]["viral_sum"] += r.viral_score

        for p in by_platform.values():
            p["avg_viral"] = p["viral_sum"] / p["count"]

        return {
            "total_jobs": len(reports),
            "total_views": total_views,
            "total_engagement": total_engagement,
            "engagement_rate": total_engagement / max(total_views, 1),
            "avg_viral_score": avg_viral,
            "by_platform": by_platform,
            "top_performers": sorted(reports, key=lambda x: x.viral_score, reverse=True)[:5],
        }

    async def _generate_insights(self, aggregate: Dict, niche: str) -> List[str]:
        prompt = f"""
Analyze these performance metrics for {niche} niche content:
{json.dumps(aggregate, indent=2, default=str)}

Generate 5-7 specific, actionable insights about:
1. What content patterns drive highest viral scores
2. Platform-specific performance differences
3. Optimal posting times/frequency signals
4. Hook/retention patterns that work
5. Audience engagement preferences
6. Revenue correlation signals
7. Any anomalies or opportunities

Return as JSON array of strings.
"""
        result = await self.llm.generate_structured(
            prompt=prompt,
            schema={"type": "array", "items": {"type": "string"}},
            temperature=0.5,
        )
        return result.get("data", []) if result.get("success") else []

    async def _generate_recommendations(self, aggregate: Dict, niche: str) -> List[str]:
        prompt = f"""
Based on these {niche} niche performance metrics:
{json.dumps(aggregate, indent=2, default=str)}

Generate 5-7 specific recommendations for future content:
1. Content topics/themes to double down on
2. Hook formulas to reuse
3. Visual/style adjustments
4. Posting schedule optimizations
5. Platform allocation strategy
6. CTA improvements
7. Budget/premium content triggers

Return as JSON array of strings.
"""
        result = await self.llm.generate_structured(
            prompt=prompt,
            schema={"type": "array", "items": {"type": "string"}},
            temperature=0.5,
        )
        return result.get("data", []) if result.get("success") else []

    async def _update_style_guides(self, niche: str, insights: List[str], recommendations: List[str]):
        from backend.vault.repository import get_style_guide, upsert_style_guide
        from backend.vault.models import StyleGuide

        guide = await get_style_guide(niche)
        if not guide:
            guide = StyleGuide(name=niche)

        guide.insights_log = (guide.insights_log or "") + f"\n[{datetime.utcnow().isoformat()}] " + "; ".join(insights)
        guide.recommendations_log = (guide.recommendations_log or "") + f"\n[{datetime.utcnow().isoformat()}] " + "; ".join(recommendations)
        guide.updated_at = datetime.utcnow()

        await upsert_style_guide(guide)

    async def _update_hook_formulas(self, niche: str, reports: List[PerformanceReport]):
        from backend.vault.repository import get_hook_formula, upsert_hook_formula
        from backend.vault.models import HookFormula

        top_hooks = []
        for r in sorted(reports, key=lambda x: x.viral_score, reverse=True)[:10]:
            job = await get_job(r.job_id)
            if job and (job.config_json or {}).get("hook"):
                top_hooks.append({
                    "hook": job.config_json["hook"],
                    "viral_score": r.viral_score,
                    "retention_3s": r.retention_curve[0].retention_rate if r.retention_curve else 0,
                })

        for h in top_hooks:
            formula = await get_hook_formula(niche, h["hook"][:50])
            if not formula:
                formula = HookFormula(name=h["hook"][:50], platform=niche)

            usage_count = formula.usage_count or 0
            formula.usage_count = usage_count + 1
            success_rate = formula.success_rate or 0.0
            formula.success_rate = (
                (success_rate * usage_count + h["viral_score"] / 100)
                / formula.usage_count
            )
            avg_retention_3s = formula.avg_retention_3s or 0.0
            formula.avg_retention_3s = (
                (avg_retention_3s * usage_count + h["retention_3s"])
                / formula.usage_count
            )
            formula.last_used = datetime.utcnow()
            await upsert_hook_formula(formula)