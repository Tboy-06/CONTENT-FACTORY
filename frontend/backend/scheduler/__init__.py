import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.vault.repository import Repository
from backend.vault.models import JobStatus, StageStatus
from backend.agents.implementations import AGENT_MAP
from backend.agents.base import JobData

logger = logging.getLogger("content_factory.scheduler")
scheduler = AsyncIOScheduler()

def _db_job_to_agent_job(db_job) -> JobData:
    return JobData(
        id=db_job.id,
        niche=db_job.niche,
        status=db_job.status.value,
        current_stage=db_job.current_stage,
        config=db_job.config or {},
        assets={}
    )

async def process_job_stage(db_job):
    # Approval Gates for SCRIPT, QC1, QC2
    if db_job.current_stage in [StageStatus.SCRIPT, StageStatus.QC1, StageStatus.QC2]:
        if db_job.status != JobStatus.IN_PROGRESS and not db_job.config.get(f"approved_{db_job.current_stage.value.lower()}"):
            await Repository.update_job_status(db_job.id, JobStatus.AWAITING_APPROVAL)
            logger.info(f"Job {db_job.id} at stage {db_job.current_stage.value} held for human approval.")
            return

    agent = AGENT_MAP.get(db_job.current_stage.value)
    if not agent:
        logger.error(f"No agent registered for stage {db_job.current_stage.value}")
        return

    await Repository.update_job_status(db_job.id, JobStatus.IN_PROGRESS)
    job_data = _db_job_to_agent_job(db_job)
    result = await agent.run(job_data)

    if result.success:
        stages = list(StageStatus)
        curr_idx = stages.index(db_job.current_stage)
        if curr_idx < len(stages) - 1:
            next_stage = stages[curr_idx + 1]
            await Repository.update_job_status(db_job.id, JobStatus.PENDING, next_stage)
            logger.info(f"Job {db_job.id} progressed from {db_job.current_stage.value} to {next_stage.value}")
        else:
            await Repository.update_job_status(db_job.id, JobStatus.COMPLETED)
            logger.info(f"Job {db_job.id} completed entire 10-stage pipeline!")
    elif result.error == "PREMIUM_WAIT":
        await Repository.update_job_status(db_job.id, JobStatus.AWAITING_PREMIUM)
        logger.info(f"Job {db_job.id} awaiting premium video generation asset.")
    else:
        await Repository.update_job_status(db_job.id, JobStatus.FAILED)
        logger.error(f"Job {db_job.id} failed at {db_job.current_stage.value}: {result.error}")

async def pipeline_tick():
    """Main scheduler tick: processes pending jobs in batch"""
    jobs = await Repository.get_jobs()
    for db_job in jobs:
        if db_job.status in [JobStatus.PENDING, JobStatus.IN_PROGRESS]:
            await process_job_stage(db_job)

async def daily_research():
    logger.info("Running daily autonomous niche research scan...")

async def analytics_fetch():
    logger.info("Running daily analytics refresh across published channels...")

async def weekly_cleanup():
    logger.info("Running weekly asset vault pruning for items older than 90 days...")

async def daily_vacuum():
    logger.info("Running daily database vacuum and index optimization...")

# Schedule jobs
scheduler.add_job(pipeline_tick, 'interval', minutes=1, id="pipeline_tick")
scheduler.add_job(daily_research, 'cron', hour=6, id="daily_research")
scheduler.add_job(analytics_fetch, 'cron', hour=23, id="analytics_fetch")
scheduler.add_job(weekly_cleanup, 'cron', day_of_week='sun', id="weekly_cleanup")
scheduler.add_job(daily_vacuum, 'cron', hour=3, id="daily_vacuum")
