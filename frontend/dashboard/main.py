from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.vault.repository import Repository
from backend.vault.models import JobStatus, StageStatus
from backend.config import settings

app = FastAPI(title="CONTENT-FACTORY Dashboard", version="1.0.0")
templates = Jinja2Templates(directory="dashboard/templates")

class VaultMetrics(BaseModel):
    totalSpent: float
    totalTokens: int
    totalRevenue: float
    dailyBudget: float
    activeJobsCount: int
    completedJobsCount: int
    totalViews: int

class StyleGuideSchema(BaseModel):
    niche: str
    archetype: str
    primaryColor: str
    accentColor: str
    typography: str
    cutFrequency: str
    music: str

class CharacterBibleSchema(BaseModel):
    niche: str
    characterName: str
    persona: str
    visualDescription: str

class HookFormulaSchema(BaseModel):
    formula: str
    score: float
    count: int

class LogSchema(BaseModel):
    id: int
    time: str
    message: str

class VaultDataResponse(BaseModel):
    metrics: VaultMetrics
    styleGuides: List[StyleGuideSchema] = []
    characterBibles: List[CharacterBibleSchema] = []
    hookFormulas: List[HookFormulaSchema] = []
    logs: List[LogSchema] = []

@app.get("/")
async def root(request: Request):
    jobs = await Repository.get_jobs()
    total_costs = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "jobs": jobs,
        "total_costs": round(total_costs, 4),
        "total_tokens": total_tokens,
        "budget": settings.daily_budget_usd
    })

@app.get("/job/{job_id}")
async def job_detail(request: Request, job_id: int):
    job = await Repository.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = await Repository.get_stages_by_job(job_id)
    assets = await Repository.get_assets_by_job(job_id)
    analytics = await Repository.get_analytics_by_job(job_id)
    costs = await Repository.get_costs_by_job(job_id)
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job": job,
        "stages": stages,
        "assets": assets,
        "analytics": analytics,
        "costs": costs
    })

@app.get("/analytics")
async def analytics_view(request: Request):
    total_costs = await Repository.get_total_costs()
    total_revenue = await Repository.get_total_revenue()
    jobs = await Repository.get_jobs()
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "jobs": jobs,
        "total_costs": total_costs,
        "total_revenue": total_revenue
    })

@app.get("/style-guides")
async def style_guides_view(request: Request):
    style_guides = await Repository.get_style_guides()
    character_bibles = await Repository.get_character_bibles()
    hook_formulas = await Repository.get_hook_formulas()
    return templates.TemplateResponse("style_guides.html", {
        "request": request,
        "style_guides": style_guides,
        "character_bibles": character_bibles,
        "hook_formulas": hook_formulas
    })

@app.get("/health")
async def health():
    return {"status": "ok", "service": "CONTENT-FACTORY", "version": "1.0.0"}

@app.get("/api/jobs")
async def api_jobs():
    jobs = await Repository.get_jobs()
    return [{
        "id": j.id,
        "niche": j.niche,
        "status": j.status.value,
        "stage": j.current_stage.value,
        "created_at": j.created_at.isoformat() if hasattr(j, "created_at") and j.created_at else None,
        "config": j.config
    } for j in jobs]

@app.get("/api/jobs/{job_id}")
async def api_job_detail(job_id: int):
    job = await Repository.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = await Repository.get_stages_by_job(job_id)
    assets = await Repository.get_assets_by_job(job_id)
    costs = await Repository.get_costs_by_job(job_id)
    return {
        "id": job.id,
        "niche": job.niche,
        "status": job.status.value,
        "stage": job.current_stage.value,
        "config": job.config,
        "stages": [{"id": s.id, "stage": s.stage.value, "output": s.output} for s in stages],
        "assets": [{"id": a.id, "type": a.asset_type.value, "path": a.file_path} for a in assets],
        "costs": [{"agent": c.agent_name, "tokens": c.tokens, "usd": c.usd_estimate} for c in costs]
    }

@app.get("/api/analytics/summary")
async def api_analytics_summary():
    total_costs = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    total_rev = await Repository.get_total_revenue()
    jobs = await Repository.get_jobs()
    return {
        "total_jobs": len(jobs),
        "total_spend_usd": round(total_costs, 4),
        "total_tokens": total_tokens,
        "total_revenue_usd": round(total_rev, 2),
        "daily_budget_usd": settings.daily_budget_usd,
        "budget_remaining": max(0.0, round(settings.daily_budget_usd - total_costs, 4))
    }

@app.get("/api/analytics/posts")
async def api_analytics_posts():
    jobs = await Repository.get_jobs()
    posts_data = []
    for j in jobs:
        analytics = await Repository.get_analytics_by_job(j.id)
        if analytics:
            for a in analytics:
                posts_data.append({
                    "job_id": j.id,
                    "niche": j.niche,
                    "views": a.views,
                    "likes": a.likes,
                    "comments": a.comments,
                    "shares": a.shares,
                    "retention": a.retention_rate
                })
    return posts_data

@app.get("/api/vault", response_model=VaultDataResponse)
async def api_vault():
    total_spent = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    total_revenue = await Repository.get_total_revenue()
    total_views = await Repository.get_total_views()
    completed_jobs = await Repository.get_completed_jobs_count()
    active_jobs = await Repository.get_active_jobs_count()

    style_guides_raw = await Repository.get_style_guides()
    character_bibles_raw = await Repository.get_character_bibles()
    hook_formulas_raw = await Repository.get_hook_formulas()
    logs_raw = await Repository.get_logs(limit=30)

    formatted_styles: List[StyleGuideSchema] = []
    for sg in style_guides_raw:
        data = sg.data if isinstance(sg.data, dict) else {}
        formatted_styles.append(
            StyleGuideSchema(
                niche=sg.niche,
                archetype=str(data.get("archetype") or data.get("visual_archetype") or "Cinematic Tech Noir"),
                primaryColor=str(data.get("primaryColor") or data.get("primary_color") or "#0F172A"),
                accentColor=str(data.get("accentColor") or data.get("accent_neon") or "#38BDF8"),
                typography=str(data.get("typography") or data.get("font_family") or "Syne / Montserrat Bold"),
                cutFrequency=str(data.get("cutFrequency") or data.get("cut_frequency") or "Every 1.8s"),
                music=str(data.get("music") or data.get("bg_music_genre") or "Tension Synth")
            )
        )

    formatted_bibles: List[CharacterBibleSchema] = []
    for cb in character_bibles_raw:
        data = cb.data if isinstance(cb.data, dict) else {}
        formatted_bibles.append(
            CharacterBibleSchema(
                niche=cb.niche,
                characterName=str(data.get("characterName") or data.get("narrator_persona") or "The Architect"),
                persona=str(data.get("persona") or data.get("tone") or "High-signal authoritative"),
                visualDescription=str(data.get("visualDescription") or data.get("costume_style") or "Dark techwear")
            )
        )

    formatted_hooks: List[HookFormulaSchema] = []
    for hf in hook_formulas_raw:
        formatted_hooks.append(
            HookFormulaSchema(
                formula=hf.formula,
                score=round(float(hf.virality_score), 1),
                count=1
            )
        )

    formatted_logs: List[LogSchema] = []
    for log in logs_raw:
        log_time = "Now"
        if hasattr(log, "created_at") and log.created_at:
            try:
                log_time = log.created_at.strftime("%H:%M:%S")
            except Exception:
                log_time = str(log.created_at)
        formatted_logs.append(
            LogSchema(
                id=log.id,
                time=log_time,
                message=log.message
            )
        )

    return VaultDataResponse(
        metrics=VaultMetrics(
            totalSpent=round(float(total_spent), 4),
            totalTokens=int(total_tokens),
            totalRevenue=round(float(total_revenue), 2),
            dailyBudget=float(settings.daily_budget_usd),
            activeJobsCount=int(active_jobs),
            completedJobsCount=int(completed_jobs),
            totalViews=int(total_views)
        ),
        styleGuides=formatted_styles,
        characterBibles=formatted_bibles,
        hookFormulas=formatted_hooks,
        logs=formatted_logs
    )
