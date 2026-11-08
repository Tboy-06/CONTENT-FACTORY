from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import asyncio
from datetime import datetime

from backend.vault import repository
from backend.vault.models import JobStatus, ApprovalDecision
from backend.scheduler import process_job_stage, _db_job_to_agent_job
from backend.agents.niche_scorer import niche_scorer_agent
from backend.tools.instant_pipeline import run_instant_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

class InstantJobRequest(BaseModel):
    topic: str
    voice: Optional[str] = "en-US-AriaNeural"

class JobCreateRequest(BaseModel):
    niche: str
    referenceUrl: Optional[str] = None
    duration: str = "60s"
    format: str = "9:16"
    premium: bool = False
    manual_approval: bool = False
    pipelineMode: str = "Generate from Scratch"
    spinStrategy: Optional[str] = None
    publishingStrategy: Optional[str] = None
    platforms: Optional[List[str]] = ["TikTok", "Instagram Reels", "YouTube Shorts"]

class ScoreNicheRequest(BaseModel):
    niche: str

class RejectRequest(BaseModel):
    reason: str

class ApproveRequest(BaseModel):
    notes: Optional[str] = None

@router.get('')
async def get_jobs():
    jobs = await repository.get_jobs(limit=50)
    formatted_jobs = []
    for j in jobs:
        stages = await repository.get_job_stages(j.id)
        assets = await repository.get_job_assets(j.id)
        approvals = await repository.get_pending_approvals()  # just approximation
        # we need approvals for this job
        approvals = [a for a in approvals if a.job_id == j.id]
        costs = await repository.get_job_costs(j.id)
        
        # formatting stages
        stages_data = []
        for s in stages:
            stages_data.append({
                "id": s.id,
                "stage": s.stage_name,
                "output": s.output_json,
                "timestamp": s.started_at.isoformat() if s.started_at else s.completed_at.isoformat() if s.completed_at else None
            })
            
        assets_data = []
        for a in assets:
            meta = a.metadata_json if isinstance(a.metadata_json, dict) else {}
            assets_data.append({
                "id": a.id,
                "type": (a.asset_type or "UNKNOWN").upper(),
                "path": a.path,
                "description": meta.get("description", a.asset_type),
                "metadata": meta,
            })
            
        costs_data = []
        for c in costs:
            costs_data.append({
                "id": c.id,
                "agent_name": c.provider,
                "tokens": c.tokens_in + c.tokens_out,
                "usd_estimate": c.usd_estimate,
                "timestamp": c.created_at.isoformat() if c.created_at else None
            })
            
        approvals_data = []
        for ap in approvals:
            approvals_data.append({
                "id": ap.id,
                "stage": ap.stage,
                "decision": ap.decision.name if ap.decision else "PENDING",
                "timestamp": ap.resolved_at.isoformat() if ap.resolved_at else ap.requested_at.isoformat() if ap.requested_at else None,
                "notes": ap.notes
            })
            
        formatted_jobs.append({
            "id": j.id,
            "niche": j.niche or "Unknown",
            "status": j.status.value.upper() if j.status else "PENDING",
            "current_stage": j.current_stage.upper() if j.current_stage else "IDEA",
            "config": j.config_json or {},
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "stages": stages_data,
            "assets": assets_data,
            "approvals": approvals_data,
            "costs": costs_data,
            "analytics": {
                "views": 0, "likes": 0, "comments": 0, "shares": 0, "retention_rate": 0, "revenue": 0
            }
        })
    return formatted_jobs

@router.get('/spend')
async def get_spend():
    jobs = await repository.get_jobs(limit=1000)
    total = 0.0
    for j in jobs:
        costs = await repository.get_job_costs(j.id)
        for c in costs:
            total += (c.usd_estimate or 0.0)
    return {"status": "success", "total_spend": total}

@router.post('/instant')
async def create_instant_job(req: InstantJobRequest):
    logger.info(f"Received instant video creation request: {req.topic}")
    config = {
        "format": "9:16",
        "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
        "premium": False,
        "mode": "Instant 1-Click",
        "voice": req.voice or "en-US-AriaNeural"
    }
    job = await repository.create_job(niche=req.topic, config=config, priority=1)
    await repository.update_job_status(job.id, JobStatus.RUNNING, "SCRIPT")
    
    # Launch instant 4-step pipeline in background
    asyncio.create_task(run_instant_pipeline(job.id, req.topic, req.voice or "en-US-AriaNeural"))
    
    return {
        "id": job.id,
        "niche": job.niche,
        "status": "RUNNING",
        "current_stage": "SCRIPT",
        "message": "Instant 4-step generation started"
    }

@router.post('')
async def create_job(req: JobCreateRequest):
    logger.info(f"Received new job creation request: {req.dict()}")
    
    config = {
        "format": req.format,
        "platforms": req.platforms,
        "premium": req.premium,
        "mode": req.pipelineMode,
        "referenceUrl": req.referenceUrl
    }
    
    job = await repository.create_job(niche=req.niche, config=config, priority=0)
    await repository.update_job_status(job.id, JobStatus.RUNNING, "IDEA")
    
    return {
        "id": job.id, 
        "niche": job.niche, 
        "status": "RUNNING", 
        "current_stage": "IDEA", 
        "created_at": job.created_at.isoformat() if job.created_at else None
    }

@router.post('/score-niche')
async def score_niche(req: ScoreNicheRequest):
    result = await niche_scorer_agent.run(req.niche)
    return {"status": "success", "data": result}

@router.post('/{job_id}/advance')
async def advance_job(job_id: int):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    approvals = await repository.get_pending_approvals()
    if any(a.job_id == job_id for a in approvals):
        raise HTTPException(status_code=400, detail="Cannot advance while waiting for approval")
        
    agent_job = _db_job_to_agent_job(job)
    asyncio.create_task(process_job_stage(agent_job))
    return {"status": "success", "message": "Advancing stage"}

@router.post('/{job_id}/approve')
async def approve_job(job_id: int, req: ApproveRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    approvals = await repository.get_pending_approvals()
    job_approvals = [a for a in approvals if a.job_id == job_id]
    
    for a in job_approvals:
        await repository.resolve_approval(a.id, ApprovalDecision.APPROVED, "User", req.notes)
        
    await repository.update_job_status(job_id, JobStatus.RUNNING, job.current_stage)
    
    # Auto-advance
    agent_job = _db_job_to_agent_job(job)
    agent_job.status = JobStatus.RUNNING.value
    asyncio.create_task(process_job_stage(agent_job))
    
    return {"status": "success"}

@router.post('/{job_id}/reject')
async def reject_job(job_id: int, req: RejectRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    approvals = await repository.get_pending_approvals()
    job_approvals = [a for a in approvals if a.job_id == job_id]
    
    for a in job_approvals:
        await repository.resolve_approval(a.id, ApprovalDecision.REJECTED, "User", req.reason)
        
    # Revert to previous stage based on current stage logic
    prev_stage = "SCRIPT"
    if job.current_stage == "QC2":
        prev_stage = "VIDEO"
        
    await repository.update_job_status(job_id, JobStatus.RUNNING, prev_stage)
    await repository.log_event("INFO", "User", f"Job {job_id} rejected, reverted to {prev_stage}. Reason: {req.reason}")
    
    return {"status": "success"}

@router.post('/{job_id}/upload-premium')
async def upload_premium(job_id: int):
    job = await repository.get_job(job_id)
    if not job or job.status != JobStatus.AWAITING_PREMIUM:
        raise HTTPException(status_code=400, detail="Job not awaiting premium")
        
    await repository.add_asset(job_id, "VIDEO", f"/vault/renders/premium_{job_id}.mp4", {"description": "Premium 4K Render Uploaded"})
    await repository.update_job_status(job_id, JobStatus.RUNNING, "QC2")
    
    agent_job = _db_job_to_agent_job(job)
    agent_job.status = JobStatus.RUNNING.value
    agent_job.current_stage = "QC2"
    asyncio.create_task(process_job_stage(agent_job))
    
    return {"status": "success"}

@router.get('/status')
async def get_jobs_status():
    # Keep this for TelegramSimulator if needed, or point it to the main format
    jobs = await repository.get_jobs(limit=20)
    status_dict = {}
    for j in jobs:
        status_dict[str(j.id)] = {
            "niche": j.niche,
            "status": j.status.value if j.status else "pending",
            "stage": j.current_stage,
            "progress": "50%" # mock
        }
    return {"status": "success", "jobs": status_dict}
