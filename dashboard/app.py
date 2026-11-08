from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime, timedelta, timezone

from backend.config import get_settings
from backend.vault import (
    get_jobs, get_job, get_job_assets, get_job_analytics,
    get_total_costs, get_style_guide, get_analytics_by_niche
)

settings = get_settings()

_this_dir = Path(__file__).parent

app = FastAPI(title="CONTENT-FACTORY Dashboard")

templates = Jinja2Templates(directory=str(_this_dir / "templates"))

# Only mount static if directory exists and has files
_static_dir = _this_dir / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


def _job_to_dict(job) -> dict:
    """Convert a Job ORM model to a serializable dict."""
    return {
        "id": job.id,
        "niche": job.niche,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "current_stage": job.current_stage,
        "config": job.config_json or {},
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        jobs = await get_jobs(limit=20)
        total_cost = await get_total_costs()
    except Exception:
        jobs = []
        total_cost = 0.0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "jobs": jobs,
        "total_cost": total_cost,
        "settings": settings,
    })


@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = await get_job_assets(job_id)
    analytics = await get_job_analytics(job_id)

    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job": job,
        "assets": assets,
        "analytics": analytics,
        "settings": settings,
    })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    analytics_data = await get_analytics_by_niche(limit=50)

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "analytics": analytics_data,
        "settings": settings,
    })


@app.get("/style-guides", response_class=HTMLResponse)
async def style_guides(request: Request):
    guides = []
    for niche in ["finance", "tech", "health", "business", "education"]:
        guide = await get_style_guide(niche)
        if guide:
            guides.append(guide)

    return templates.TemplateResponse("style_guides.html", {
        "request": request,
        "guides": guides,
        "settings": settings,
    })


@app.get("/api/jobs")
async def api_jobs(limit: int = 50, status: Optional[str] = None):
    jobs = await get_jobs(limit=limit)
    if status:
        # Use lowercase comparison — JobStatus enum values are lowercase
        jobs = [j for j in jobs if j.status.value == status.lower()]
    return {"jobs": [_job_to_dict(j) for j in jobs]}


@app.get("/api/jobs/{job_id}")
async def api_job(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@app.get("/api/analytics/summary")
async def api_analytics_summary(days: int = 30):
    analytics_data = await get_analytics_by_niche(limit=100)

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    recent = [a for a in analytics_data if a.fetched_at and a.fetched_at > cutoff]

    total_views = sum(a.views or 0 for a in recent)
    total_watch_time = sum(a.watch_time_seconds or 0 for a in recent)
    total_revenue = sum(a.revenue_usd or 0 for a in recent)

    # Extract engagement from raw_json if available
    total_engagement = 0
    for a in recent:
        raw = a.raw_json or {}
        total_engagement += (raw.get("likes", 0) or 0) + (raw.get("comments", 0) or 0) + (raw.get("shares", 0) or 0)

    avg_retention = 0
    avg_ctr = 0
    if recent:
        retentions = [a.retention_pct for a in recent if a.retention_pct is not None]
        ctrs = [a.ctr for a in recent if a.ctr is not None]
        avg_retention = sum(retentions) / max(len(retentions), 1)
        avg_ctr = sum(ctrs) / max(len(ctrs), 1)

    return {
        "period_days": days,
        "total_posts": len(recent),
        "total_views": total_views,
        "total_engagement": total_engagement,
        "engagement_rate": total_engagement / max(total_views, 1),
        "avg_views": total_views / max(len(recent), 1),
        "avg_watch_time": total_watch_time / max(len(recent), 1),
        "ctr": avg_ctr,
        "avg_retention": avg_retention,
        "total_revenue": total_revenue,
    }


@app.get("/api/analytics/posts")
async def api_analytics_posts(days: int = 30, limit: int = 50):
    analytics_data = await get_analytics_by_niche(limit=limit)

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    recent = [a for a in analytics_data if a.fetched_at and a.fetched_at > cutoff]

    posts = []
    for a in recent:
        job = await get_job(a.job_id) if a.job_id else None
        raw = a.raw_json or {}
        posts.append({
            "job_id": a.job_id,
            "niche": job.niche if job else "unknown",
            "platform": a.platform,
            "views": a.views,
            "likes": raw.get("likes", 0),
            "comments": raw.get("comments", 0),
            "shares": raw.get("shares", 0),
            "retention_pct": a.retention_pct or 0,
            "avg_watch_time": a.watch_time_seconds or 0,
            "ctr": a.ctr or 0,
            "revenue_usd": a.revenue_usd or 0,
            "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None,
        })

    return {"posts": posts}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


def create_dashboard_app() -> FastAPI:
    return app