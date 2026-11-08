from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import delete, desc, func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.vault.models import (
    Analytics,
    Asset,
    Approval,
    ApprovalDecision,
    AssetType,
    CharacterBible,
    Cost,
    HookFormula,
    Job,
    JobStage,
    JobStatus,
    Log,
    RevenueStream,
    SkillManifest,
    StageStatus,
    StyleGuide,
)
from backend.vault.database import get_session


# =============================================================================
# Jobs
# =============================================================================

async def create_job(
    niche: str,
    config: Dict[str, Any],
    priority: int = 0,
) -> Job:
    async with get_session() as session:
        job = Job(niche=niche, config_json=config, priority=priority)
        session.add(job)
        await session.flush()
        await session.refresh(job)
        return job


async def get_job(job_id: int) -> Optional[Job]:
    async with get_session() as session:
        return await session.get(Job, job_id)


async def get_jobs(
    status: Optional[JobStatus] = None,
    niche: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[Job]:
    async with get_session() as session:
        stmt = select(Job).order_by(desc(Job.created_at))
        if status:
            stmt = stmt.where(Job.status == status)
        if niche:
            stmt = stmt.where(Job.niche == niche)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.scalars().all()


async def update_job_status(job_id: int, status: JobStatus, current_stage: Optional[str] = None) -> bool:
    async with get_session() as session:
        stmt = update(Job).where(Job.id == job_id).values(status=status, updated_at=datetime.utcnow())
        if current_stage:
            stmt = stmt.values(current_stage=current_stage)
        result = await session.execute(stmt)
        return result.rowcount > 0


async def get_pending_jobs(limit: int = 10) -> Sequence[Job]:
    async with get_session() as session:
        stmt = (
            select(Job)
            .where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Job Stages
# =============================================================================

async def create_stage(
    job_id: int,
    stage_name: str,
    agent_id: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None,
) -> JobStage:
    async with get_session() as session:
        stmt = select(JobStage).where(JobStage.job_id == job_id, JobStage.stage_name == stage_name)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.status = StageStatus.PENDING
            existing.agent_id = agent_id or existing.agent_id
            if input_data:
                existing.input_json = input_data
            await session.commit()
            await session.refresh(existing)
            return existing
            
        stage = JobStage(
            job_id=job_id,
            stage_name=stage_name,
            agent_id=agent_id,
            input_json=input_data or {},
            status=StageStatus.PENDING,
        )
        session.add(stage)
        await session.commit()
        await session.refresh(stage)
        return stage


async def start_stage(stage_id: int, agent_id: str) -> bool:
    async with get_session() as session:
        stmt = (
            update(JobStage)
            .where(JobStage.id == stage_id)
            .values(status=StageStatus.RUNNING, agent_id=agent_id, started_at=datetime.utcnow())
        )
        result = await session.execute(stmt)
        return result.rowcount > 0


async def complete_stage(
    stage_id: int,
    output_data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> bool:
    async with get_session() as session:
        status = StageStatus.FAILED if error else StageStatus.COMPLETED
        stmt = (
            update(JobStage)
            .where(JobStage.id == stage_id)
            .values(
                status=status,
                output_json=output_data or {},
                error=error,
                completed_at=datetime.utcnow(),
            )
        )
        result = await session.execute(stmt)
        return result.rowcount > 0


async def get_job_stages(job_id: int) -> Sequence[JobStage]:
    async with get_session() as session:
        stmt = select(JobStage).where(JobStage.job_id == job_id).order_by(JobStage.started_at)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_stage(job_id: int, stage_name: str) -> Optional[JobStage]:
    async with get_session() as session:
        stmt = select(JobStage).where(JobStage.job_id == job_id, JobStage.stage_name == stage_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# =============================================================================
# Assets
# =============================================================================

async def add_asset(
    job_id: int,
    asset_type: str,
    path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Asset:
    async with get_session() as session:
        asset = Asset(job_id=job_id, asset_type=asset_type, path=path, metadata_json=metadata or {})
        session.add(asset)
        await session.flush()
        await session.refresh(asset)
        return asset


async def get_job_assets(job_id: int, asset_type: Optional[str] = None) -> Sequence[Asset]:
    async with get_session() as session:
        stmt = select(Asset).where(Asset.job_id == job_id)
        if asset_type:
            stmt = stmt.where(Asset.asset_type == asset_type)
        stmt = stmt.order_by(Asset.created_at)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_latest_asset(job_id: int, asset_type: str) -> Optional[Asset]:
    async with get_session() as session:
        stmt = (
            select(Asset)
            .where(Asset.job_id == job_id, Asset.asset_type == asset_type)
            .order_by(desc(Asset.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# =============================================================================
# Approvals
# =============================================================================

async def create_approval(
    job_id: int,
    stage: str,
) -> Approval:
    async with get_session() as session:
        approval = Approval(job_id=job_id, stage=stage)
        session.add(approval)
        await session.flush()
        await session.refresh(approval)
        return approval


async def resolve_approval(
    approval_id: int,
    decision: ApprovalDecision,
    decided_by: str,
    notes: Optional[str] = None,
) -> bool:
    async with get_session() as session:
        stmt = (
            update(Approval)
            .where(Approval.id == approval_id)
            .values(
                decision=decision,
                decided_by=decided_by,
                resolved_at=datetime.utcnow(),
                notes=notes,
            )
        )
        result = await session.execute(stmt)
        return result.rowcount > 0


async def get_pending_approvals() -> Sequence[Approval]:
    async with get_session() as session:
        stmt = select(Approval).where(Approval.decision.is_(None)).order_by(Approval.requested_at)
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Costs
# =============================================================================

async def record_cost(
    job_id: int,
    provider: str,
    operation: str,
    tokens_in: int,
    tokens_out: int,
    usd_estimate: float,
) -> Cost:
    async with get_session() as session:
        cost = Cost(
            job_id=job_id,
            provider=provider,
            operation=operation,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            usd_estimate=usd_estimate,
        )
        session.add(cost)
        await session.flush()
        await session.refresh(cost)
        return cost


async def get_job_costs(job_id: int) -> Sequence[Cost]:
    async with get_session() as session:
        stmt = select(Cost).where(Cost.job_id == job_id).order_by(Cost.created_at)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_total_costs(
    since: Optional[datetime] = None,
    provider: Optional[str] = None,
) -> float:
    async with get_session() as session:
        stmt = select(func.sum(Cost.usd_estimate))
        if since:
            stmt = stmt.where(Cost.created_at >= since)
        if provider:
            stmt = stmt.where(Cost.provider == provider)
        result = await session.execute(stmt)
        return result.scalar() or 0.0


# =============================================================================
# Style Guides
# =============================================================================

async def create_style_guide(
    name: str,
    source_video_url: Optional[str],
    extracted: Dict[str, Any],
) -> StyleGuide:
    async with get_session() as session:
        guide = StyleGuide(
            name=name,
            source_video_url=source_video_url,
            extracted_json=extracted,
        )
        session.add(guide)
        await session.flush()
        await session.refresh(guide)
        return guide


async def get_style_guide(name: str) -> Optional[StyleGuide]:
    async with get_session() as session:
        stmt = select(StyleGuide).where(StyleGuide.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def list_style_guides(limit: int = 50) -> Sequence[StyleGuide]:
    async with get_session() as session:
        stmt = select(StyleGuide).order_by(desc(StyleGuide.created_at)).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Character Bible
# =============================================================================

async def create_character_bible(
    name: str,
    prompt: str,
    reference_images: Dict[str, Any],
    style_guide_id: Optional[int] = None,
) -> CharacterBible:
    async with get_session() as session:
        bible = CharacterBible(
            name=name,
            prompt=prompt,
            reference_images_json=reference_images,
            style_guide_id=style_guide_id,
        )
        session.add(bible)
        await session.flush()
        await session.refresh(bible)
        return bible


async def get_character_bible(name: str) -> Optional[CharacterBible]:
    async with get_session() as session:
        stmt = select(CharacterBible).where(CharacterBible.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# =============================================================================
# Hook Formulas
# =============================================================================

async def create_hook_formula(
    name: str,
    pattern: str,
    platform: str,
    retention_data: Dict[str, Any],
) -> HookFormula:
    async with get_session() as session:
        formula = HookFormula(
            name=name,
            pattern=pattern,
            platform=platform,
            retention_data_json=retention_data,
        )
        session.add(formula)
        await session.flush()
        await session.refresh(formula)
        return formula


async def get_hook_formula(name: str) -> Optional[HookFormula]:
    async with get_session() as session:
        stmt = select(HookFormula).where(HookFormula.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def list_hook_formulas(platform: Optional[str] = None, limit: int = 50) -> Sequence[HookFormula]:
    async with get_session() as session:
        stmt = select(HookFormula).order_by(desc(HookFormula.created_at))
        if platform:
            stmt = stmt.where(HookFormula.platform == platform)
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Analytics
# =============================================================================

async def record_analytics(
    job_id: int,
    platform: str,
    video_id: Optional[str],
    views: int,
    watch_time_seconds: int,
    retention_pct: Optional[float],
    ctr: Optional[float],
    revenue_usd: Optional[float],
    raw: Dict[str, Any],
) -> Analytics:
    async with get_session() as session:
        analytics = Analytics(
            job_id=job_id,
            platform=platform,
            video_id=video_id,
            views=views,
            watch_time_seconds=watch_time_seconds,
            retention_pct=retention_pct,
            ctr=ctr,
            revenue_usd=revenue_usd,
            raw_json=raw,
        )
        session.add(analytics)
        await session.flush()
        await session.refresh(analytics)
        return analytics


async def get_job_analytics(job_id: int) -> Sequence[Analytics]:
    async with get_session() as session:
        stmt = select(Analytics).where(Analytics.job_id == job_id).order_by(Analytics.fetched_at)
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_analytics_by_niche(limit: int = 100) -> Sequence[Analytics]:
    async with get_session() as session:
        stmt = select(Analytics).order_by(desc(Analytics.fetched_at)).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


async def upsert_style_guide(guide: StyleGuide) -> StyleGuide:
    async with get_session() as session:
        existing = await session.get(StyleGuide, guide.id) if guide.id else None
        if existing:
            existing.visual_dna_json = guide.visual_dna_json
            existing.hook_formulas_json = guide.hook_formulas_json
            existing.character_bible_json = guide.character_bible_json
            existing.insights_log = guide.insights_log
            existing.recommendations_log = guide.recommendations_log
            existing.updated_at = guide.updated_at
            await session.flush()
            await session.refresh(existing)
            return existing
        else:
            session.add(guide)
            await session.flush()
            await session.refresh(guide)
            return guide


async def find_hook_formula(niche: str, pattern: str) -> Optional[HookFormula]:
    async with get_session() as session:
        stmt = select(HookFormula).where(
            HookFormula.name.like(f"%{niche}%"),
            HookFormula.pattern.like(f"%{pattern}%")
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def upsert_hook_formula(formula: HookFormula) -> HookFormula:
    async with get_session() as session:
        existing = await session.get(HookFormula, formula.id) if formula.id else None
        if existing:
            existing.usage_count = formula.usage_count
            existing.success_rate = formula.success_rate
            existing.avg_retention_3s = formula.avg_retention_3s
            existing.last_used = formula.last_used
            await session.flush()
            await session.refresh(existing)
            return existing
        else:
            session.add(formula)
            await session.flush()
            await session.refresh(formula)
            return formula


async def update_job_config(job_id: int, config: Dict[str, Any]) -> bool:
    async with get_session() as session:
        stmt = update(Job).where(Job.id == job_id).values(config_json=config, updated_at=datetime.utcnow())
        result = await session.execute(stmt)
        return result.rowcount > 0


# =============================================================================
# Revenue Streams
# =============================================================================

async def record_revenue(
    job_id: int,
    source: str,
    amount: float,
    currency: str = "USD",
    date: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> RevenueStream:
    async with get_session() as session:
        rev = RevenueStream(
            job_id=job_id,
            source=source,
            amount=amount,
            currency=currency,
            date=date or datetime.utcnow(),
            metadata_json=metadata or {},
        )
        session.add(rev)
        await session.flush()
        await session.refresh(rev)
        return rev


async def get_job_revenue(job_id: int) -> Sequence[RevenueStream]:
    async with get_session() as session:
        stmt = select(RevenueStream).where(RevenueStream.job_id == job_id).order_by(RevenueStream.date)
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Retention Curves
# =============================================================================

async def record_retention_curve(
    job_id: int,
    platform: str,
    time_points: List[float],
    retention_values: List[float],
) -> None:
    async with get_session() as session:
        curve = RetentionCurve(
            job_id=job_id,
            platform=platform,
            time_points_json=time_points,
            retention_values_json=retention_values,
        )
        session.add(curve)
        await session.flush()


# =============================================================================
# Logs
# =============================================================================

async def log_event(
    level: str,
    agent: Optional[str],
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    async with get_session() as session:
        log = Log(level=level.upper(), agent=agent, message=message, context_json=context or {})
        session.add(log)


async def get_recent_logs(limit: int = 100, agent: Optional[str] = None) -> Sequence[Log]:
    async with get_session() as session:
        stmt = select(Log).order_by(desc(Log.created_at)).limit(limit)
        if agent:
            stmt = stmt.where(Log.agent == agent)
        result = await session.execute(stmt)
        return result.scalars().all()


# =============================================================================
# Skill Manifests
# =============================================================================

async def create_skill_manifest(name: str, yaml_content: str, version: str = "1.0") -> SkillManifest:
    async with get_session() as session:
        skill = SkillManifest(name=name, yaml_content=yaml_content, version=version)
        session.add(skill)
        await session.flush()
        await session.refresh(skill)
        return skill


async def get_skill_manifest(name: str) -> Optional[SkillManifest]:
    async with get_session() as session:
        stmt = select(SkillManifest).where(SkillManifest.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# =============================================================================
# Cleanup / Maintenance
# =============================================================================

async def cleanup_old_jobs(days: int = 90) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with get_session() as session:
        # Delete old completed/failed jobs and cascade
        stmt = delete(Job).where(
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
            Job.updated_at < cutoff,
        )
        result = await session.execute(stmt)
        return result.rowcount


async def vacuum_database() -> None:
    from backend.vault.database import engine
    if engine is None:
        return
    async with engine.connect() as conn:
        await conn.execute(text("VACUUM"))
        await conn.commit()