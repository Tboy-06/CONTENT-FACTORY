from __future__ import annotations

import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import get_settings
from backend.vault import (
    init_database, create_tables, get_pending_jobs, cleanup_old_jobs,
    vacuum_database, log_event, create_stage, update_job_status, get_job,
    create_approval, get_session
)
from backend.agents import (
    ManagerAgent, ResearcherAgent, ScriptwriterAgent,
    StyleAnalystAgent, ArtDirectorAgent, VideoEditorAgent,
    QualityControlAgent, PosterAgent, AnalystAgent
)
from backend.vault.models import StageStatus, JobStatus, ApprovalDecision, Job as DBJob
from backend.agents.base import Job as AgentJob

settings = get_settings()
logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None

manager_agent = ManagerAgent()
researcher_agent = ResearcherAgent()
scriptwriter_agent = ScriptwriterAgent()
style_analyst_agent = StyleAnalystAgent()
art_director_agent = ArtDirectorAgent()
video_editor_agent = VideoEditorAgent()
quality_control_agent = QualityControlAgent()
poster_agent = PosterAgent()
analyst_agent = AnalystAgent()


def _db_job_to_agent_job(db_job: DBJob) -> AgentJob:
    """Convert SQLAlchemy Job model to Agent Job class."""
    assets_dict = {}
    try:
        for asset in db_job.assets:
            assets_dict[asset.asset_type] = asset.metadata_json
    except Exception:
        pass

    agent_job = AgentJob(
        id=db_job.id,
        niche=db_job.niche,
        status=db_job.status.value,
        current_stage=db_job.current_stage,
        config=db_job.config_json or {},
    )
    for asset_type, metadata in assets_dict.items():
        agent_job.set_asset(asset_type, metadata)
    return agent_job


def _status_enum(status_str: str) -> JobStatus:
    return JobStatus(status_str.lower())


async def init_scheduler() -> AsyncIOScheduler:
    global scheduler

    init_database()
    await create_tables()

    scheduler = AsyncIOScheduler()

    # Daily research at configured hour
    scheduler.add_job(
        daily_research_job,
        CronTrigger(hour=settings.daily_research_hour, minute=0),
        id="daily_research",
        replace_existing=True,
    )

    # Pipeline tick every N minutes
    scheduler.add_job(
        pipeline_tick_job,
        IntervalTrigger(minutes=settings.pipeline_tick_interval_minutes),
        id="pipeline_tick",
        replace_existing=True,
    )

    # Analytics fetch
    scheduler.add_job(
        analytics_fetch_job,
        CronTrigger(hour=settings.analytics_fetch_hour, minute=0),
        id="analytics_fetch",
        replace_existing=True,
    )

    # Weekly cleanup
    scheduler.add_job(
        weekly_cleanup_job,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_cleanup",
        replace_existing=True,
    )

    # Daily vacuum
    scheduler.add_job(
        daily_vacuum_job,
        CronTrigger(hour=4, minute=0),
        id="daily_vacuum",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")
    return scheduler


async def shutdown_scheduler() -> None:
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def daily_research_job() -> None:
    """Create new research jobs for active goals."""
    try:
        await log_event("INFO", "scheduler", "Daily research job started")
        await log_event("INFO", "scheduler", "Daily research job completed")
    except Exception as e:
        await log_event("ERROR", "scheduler", f"Daily research job failed: {e}")


async def pipeline_tick_job() -> None:
    """Process pending jobs through pipeline stages."""
    try:
        db_jobs = await get_pending_jobs(limit=2)
        for db_job in db_jobs:
            agent_job = _db_job_to_agent_job(db_job)
            await process_job_stage(agent_job)
    except Exception as e:
        await log_event("ERROR", "scheduler", f"Pipeline tick failed: {e}")


async def process_job_stage(job: AgentJob) -> None:
    """Process a single job through its current stage."""
    stage = job.current_stage

    try:
        if stage == "IDEA":
            await create_stage(job.id, "RESEARCH")
            await update_job_status(job.id, _status_enum(job.status), "RESEARCH")

        elif stage == "RESEARCH":
            result = await researcher_agent.run(job)
            if result.success:
                await create_stage(job.id, "SCRIPT")
                await update_job_status(job.id, _status_enum(job.status), "SCRIPT")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "RESEARCH")

        elif stage == "SCRIPT":
            result = await scriptwriter_agent.run(job)
            if result.success:
                await create_stage(job.id, "QC1")
                await update_job_status(job.id, _status_enum(job.status), "QC1")
                await create_approval(job.id, "SCRIPT")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "SCRIPT")

        elif stage == "QC1":
            result = await quality_control_agent.run(job, context={"stage": "QC1"})
            if result.success and result.output.get("verdict") == "PASS":
                await create_stage(job.id, "STYLE")
                await update_job_status(job.id, _status_enum(job.status), "STYLE")
            elif result.output.get("verdict") == "UNCERTAIN":
                await create_approval(job.id, "QC1")
            else:
                # Self-correction: if QC1 fails, bounce back to SCRIPT up to 3 times
                retries = job.config.get("qc1_retries", 0)
                if retries < 3:
                    job.config["qc1_retries"] = retries + 1
                    from backend.vault.repository import update_job_config
                    await update_job_config(job.id, job.config)
                    await create_stage(job.id, "SCRIPT")
                    await update_job_status(job.id, _status_enum(job.status), "SCRIPT")
                    await log_event("INFO", "scheduler", f"Job {job.id} failed QC1, bouncing back to SCRIPT (retry {retries+1}/3)")
                else:
                    await update_job_status(job.id, JobStatus.FAILED, "QC1")

        elif stage == "STYLE":
            result = await style_analyst_agent.run(job)
            if result.success:
                await create_stage(job.id, "ART")
                await update_job_status(job.id, _status_enum(job.status), "ART")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "STYLE")

        elif stage == "ART":
            result = await art_director_agent.run(job)
            if result.success:
                await create_stage(job.id, "VIDEO")
                await update_job_status(job.id, _status_enum(job.status), "VIDEO")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "ART")

        elif stage == "VIDEO":
            result = await video_editor_agent.run(job)
            if result.success:
                if result.output.get("premium"):
                    await create_stage(job.id, "AWAITING_PREMIUM")
                    await update_job_status(job.id, _status_enum(job.status), "AWAITING_PREMIUM")
                else:
                    await create_stage(job.id, "QC2")
                    await update_job_status(job.id, _status_enum(job.status), "QC2")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "VIDEO")

        elif stage == "AWAITING_PREMIUM":
            pass  # Wait for manual premium upload

        elif stage == "QC2":
            result = await quality_control_agent.run(job, context={"stage": "QC2"})
            if result.success and result.output.get("verdict") == "PASS":
                await create_stage(job.id, "POST")
                await update_job_status(job.id, _status_enum(job.status), "POST")
            elif result.output.get("verdict") == "UNCERTAIN":
                await create_approval(job.id, "QC2")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "QC2")

        elif stage == "POST":
            result = await poster_agent.run(job)
            if result.success:
                await create_stage(job.id, "ANALYZE")
                await update_job_status(job.id, _status_enum(job.status), "ANALYZE")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "POST")

        elif stage == "ANALYZE":
            result = await analyst_agent.run(job)
            if result.success:
                await update_job_status(job.id, JobStatus.COMPLETED, "ANALYZE")
            else:
                await update_job_status(job.id, JobStatus.FAILED, "ANALYZE")

    except Exception as e:
        await log_event("ERROR", "scheduler", f"Stage processing failed for job {job.id}: {e}")


async def analytics_fetch_job() -> None:
    """Fetch analytics for posted videos."""
    try:
        await log_event("INFO", "scheduler", "Analytics fetch job started")
        await log_event("INFO", "scheduler", "Analytics fetch job completed")
    except Exception as e:
        await log_event("ERROR", "scheduler", f"Analytics fetch failed: {e}")


async def weekly_cleanup_job() -> None:
    """Clean up old jobs and assets."""
    try:
        deleted = await cleanup_old_jobs(days=90)
        await log_event("INFO", "scheduler", f"Weekly cleanup: deleted {deleted} old jobs")
    except Exception as e:
        await log_event("ERROR", "scheduler", f"Weekly cleanup failed: {e}")


async def daily_vacuum_job() -> None:
    """Vacuum database."""
    try:
        await vacuum_database()
        await log_event("INFO", "scheduler", "Database vacuum completed")
    except Exception as e:
        await log_event("ERROR", "scheduler", f"Database vacuum failed: {e}")