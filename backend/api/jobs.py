import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import asyncio
from datetime import datetime

from backend.vault import repository
from backend.vault.models import JobStatus, ApprovalDecision
from backend.scheduler import process_job_stage, _db_job_to_agent_job
from backend.agents.niche_scorer import niche_scorer_agent
from backend.tools.instant_pipeline import run_instant_pipeline, render_scene_card, render_video_from_scenes, get_audio_duration

logger = logging.getLogger(__name__)

router = APIRouter()

class InstantJobRequest(BaseModel):
    topic: str
    voice: Optional[str] = "en-US-AriaNeural"
    style_preset: Optional[str] = "Dark Documentary"
    aspect_ratio: Optional[str] = "9:16"
    duration: Optional[str] = "45s"
    genre: Optional[str] = "auto"

class BrainstormRequest(BaseModel):
    topic: str

class RerollVisualRequest(BaseModel):
    scene_index: int
    custom_prompt: Optional[str] = None
    style_preset: Optional[str] = "Dark Documentary"

class RegenerateAudioRequest(BaseModel):
    voice: Optional[str] = "en-US-AriaNeural"
    scenes: Optional[List[Dict[str, Any]]] = None

class PublishRequest(BaseModel):
    platforms: List[str] = ["TikTok", "YouTube Shorts", "Instagram Reels"]

class JobCreateRequest(BaseModel):
    niche: str
    referenceUrl: Optional[str] = None
    duration: str = "60s"
    format: str = "9:16"
    voice: Optional[str] = "en-US-AriaNeural"
    style_preset: Optional[str] = "Dark Documentary"
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
    logger.info(f"Received instant video creation request: {req.topic} (style: {req.style_preset}, voice: {req.voice})")
    aspect_ratio = req.aspect_ratio or "9:16"
    duration = req.duration or "45s"
    platforms = ["YouTube Channel", "Vimeo"] if aspect_ratio == "16:9" else ["TikTok", "Instagram Reels", "YouTube Shorts"]

    config = {
        "format": aspect_ratio,
        "duration": duration,
        "platforms": platforms,
        "premium": False,
        "mode": "Instant 1-Click",
        "voice": req.voice or "en-US-AriaNeural",
        "style_preset": req.style_preset or "Dark Documentary",
        "genre": req.genre or "auto"
    }
    job = await repository.create_job(niche=req.topic, config=config, priority=1)
    await repository.update_job_status(job.id, JobStatus.RUNNING, "SCRIPT")
    
    # Launch instant documentary pipeline in background
    asyncio.create_task(run_instant_pipeline(
        job.id,
        req.topic,
        req.voice or "en-US-AriaNeural",
        req.style_preset or "Dark Documentary",
        aspect_ratio,
        duration,
        genre=req.genre or "auto"
    ))
    
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
        "duration": req.duration,
        "platforms": req.platforms,
        "premium": req.premium,
        "mode": req.pipelineMode,
        "referenceUrl": req.referenceUrl,
        "voice": req.voice,
        "style_preset": req.style_preset
    }
    
    job = await repository.create_job(niche=req.niche, config=config, priority=0)
    await repository.update_job_status(job.id, JobStatus.RUNNING, "IDEA")
    
    # Continuous execution: Run pipeline stages directly instead of 5-minute scheduler idle delays
    async def _run_continuous_stages(job_id: int):
        stages = ["IDEA", "RESEARCH", "SCRIPT", "ART", "VIDEO", "QC1"]
        for stg in stages:
            try:
                current_db = await repository.get_job(job_id)
                if not current_db or current_db.status != JobStatus.RUNNING:
                    break
                if current_db.current_stage == "QC1":
                    await repository.create_approval(job_id, "QC1")
                    break
                agent_job = _db_job_to_agent_job(current_db)
                await process_job_stage(agent_job)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"[continuous_pipeline] Stage {stg} failed for job #{job_id}: {e}")
                await repository.update_job_status(job_id, JobStatus.FAILED, stg)
                break

    asyncio.create_task(_run_continuous_stages(job.id))

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
    jobs = await repository.get_jobs(limit=20)
    status_dict = {}
    stage_weights = {
        "IDEA": "15%",
        "RESEARCH": "30%",
        "SCRIPT": "45%",
        "ART": "60%",
        "PLATES": "70%",
        "AUDIO": "80%",
        "VIDEO": "90%",
        "FFMPEG": "95%",
        "QC1": "100%",
        "QC2": "100%",
        "PUBLISHED": "100%"
    }
    for j in jobs:
        status_dict[str(j.id)] = {
            "niche": j.niche,
            "status": j.status.value if j.status else "pending",
            "stage": j.current_stage,
            "progress": stage_weights.get(j.current_stage or "", "20%")
        }
    return {"status": "success", "jobs": status_dict}

@router.post('/brainstorm-hooks')
async def brainstorm_hooks(req: BrainstormRequest):
    topic = req.topic.strip() or "Productivity Hacks"
    hooks = [
        f"Stop doing {topic} the normal way if you actually want results.",
        f"The psychological rule behind {topic} that 99% of people get backwards.",
        f"Here is why your approach to {topic} is quietly failing you right now."
    ]
    try:
        from backend.engine.brain import ask_brain
        import json, re
        prompt = f"Generate exactly 3 short, punchy, high-retention viral hook sentences (under 14 words each) for a 30s vertical video about: '{topic}'. Return as a JSON array of 3 strings."
        llm_res = await asyncio.wait_for(ask_brain(prompt, format_json=True), timeout=15.0)
        match = re.search(r'\[.*?\]', llm_res, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0), strict=False)
            if isinstance(parsed, list) and len(parsed) >= 3:
                hooks = [str(h).strip(' "\'') for h in parsed[:3]]
    except Exception as e:
        logger.warning(f"[brainstorm_hooks] Falling back to structured hooks: {e}")
    return {"status": "success", "topic": topic, "hooks": hooks}

@router.get('/system/cache')
async def get_cache_status():
    temp_bytes = 0
    temp_count = 0
    if os.path.exists("temp"):
        for root, _, files in os.walk("temp"):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    temp_bytes += os.path.getsize(fp)
                    temp_count += 1
                except OSError:
                    pass
    output_bytes = 0
    output_count = 0
    if os.path.exists("output"):
        for root, _, files in os.walk("output"):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    output_bytes += os.path.getsize(fp)
                    output_count += 1
                except OSError:
                    pass
    return {
        "temp_mb": round(temp_bytes / (1024 * 1024), 2),
        "temp_count": temp_count,
        "output_mb": round(output_bytes / (1024 * 1024), 2),
        "output_count": output_count,
    }

@router.post('/system/cache/clear')
async def clear_cache():
    freed_bytes = 0
    cleaned_count = 0
    if os.path.exists("temp"):
        for f in os.listdir("temp"):
            fp = os.path.join("temp", f)
            try:
                if os.path.isfile(fp):
                    freed_bytes += os.path.getsize(fp)
                    os.remove(fp)
                    cleaned_count += 1
            except OSError:
                pass
    return {
        "status": "success",
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "cleaned_count": cleaned_count,
        "message": f"Freed {round(freed_bytes / (1024 * 1024), 2)} MB from temporary storage."
    }

@router.post('/{job_id}/reroll-visual')
async def reroll_visual(job_id: int, req: RerollVisualRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    if not video_asset or not video_asset.metadata_json:
        raise HTTPException(status_code=400, detail="Video asset not found for job")
    
    meta = dict(video_asset.metadata_json)
    scenes = meta.get("scenes", [])
    if req.scene_index < 0 or req.scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail="Invalid scene index")
    
    sc = scenes[req.scene_index]
    style = req.style_preset or meta.get("style_preset", "Dark Documentary")
    ts = int(datetime.utcnow().timestamp())
    img_path = f"temp/instant_{job_id}_{req.scene_index}_{ts}.jpg"
    
    render_scene_card(
        output_path=img_path,
        topic=meta.get("title", job.niche),
        badge=sc.get("badge", "SCENE"),
        scene_index=req.scene_index,
        total_scenes=len(scenes),
        text=sc.get("text", ""),
        style_preset=style,
        image_prompt=req.custom_prompt or sc.get("prompt")
    )
    sc["image_path"] = img_path
    if req.custom_prompt:
        try:
            from backend.engine.reflexion import log_editorial_mistake
            topic = meta.get("title", job.niche)
            old_p = sc.get("prompt", "")
            log_editorial_mistake(
                category="user_prompt_edit",
                context_topic=topic,
                bad_state={"scene_index": req.scene_index, "old_prompt": old_p},
                fixed_state={"scene_index": req.scene_index, "new_prompt": req.custom_prompt},
                lesson_rule=f"Scene visual prompt revised: prefer '{req.custom_prompt[:60]}' for authentic archival atmosphere."
            )
        except Exception:
            pass
        sc["prompt"] = req.custom_prompt
    
    audio_asset = next((a for a in assets if (a.asset_type or "").upper() == "AUDIO"), None)
    audio_path = audio_asset.path if audio_asset else f"output/audio_{job_id}.mp3"
    final_video_path = f"output/video_{job_id}_9x16.mp4"
    
    success = await render_video_from_scenes(job_id, scenes, audio_path, final_video_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assemble updated video")
        
    meta["scenes"] = scenes
    meta["style_preset"] = style
    meta["video_url"] = f"/output/video_{job_id}_9x16.mp4?t={ts}"
    await repository.update_asset_metadata(video_asset.id, meta)
    
    return {"status": "success", "scene": sc, "video_url": meta["video_url"]}

@router.post('/{job_id}/scenes/{scene_index}/upload-custom-media')
async def upload_custom_scene_media(
    job_id: int,
    scene_index: int,
    file: UploadFile = File(...)
):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    if not video_asset or not video_asset.metadata_json:
        raise HTTPException(status_code=400, detail="Video asset not found for job")
    
    meta = dict(video_asset.metadata_json)
    scenes = meta.get("scenes", [])
    if scene_index < 0 or scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail="Invalid scene index")
    
    sc = scenes[scene_index]
    aspect_ratio = meta.get("aspect_ratio", "9:16")
    duration = float(sc.get("duration", 4.0))
    ts = int(datetime.utcnow().timestamp())
    
    raw_ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    raw_path = f"temp/custom_upload_{job_id}_{scene_index}_{ts}_raw{raw_ext}"
    os.makedirs("temp", exist_ok=True)
    
    content = await file.read()
    with open(raw_path, "wb") as f:
        f.write(content)
        
    from backend.engine.visual_cortex import normalize_custom_media
    is_video = raw_ext in (".mp4", ".mov", ".mkv", ".webm", ".avi")
    normalized_path = f"temp/custom_{job_id}_{scene_index}_{ts}{'.mp4' if is_video else '.jpg'}"
    norm_result = normalize_custom_media(
        input_file=raw_path,
        output_path=normalized_path,
        aspect_ratio=aspect_ratio,
        duration=duration
    )
    
    if os.path.exists(raw_path):
        try:
            os.remove(raw_path)
        except OSError:
            pass
            
    if not norm_result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to normalize uploaded media")
        
    if norm_result["type"] == "video":
        sc["video_path"] = normalized_path
        sc["image_path"] = None
        sc["visual_type"] = "broll_video"
    else:
        sc["image_path"] = normalized_path
        sc["video_path"] = None
        sc["visual_type"] = "treated_image"
        
    audio_asset = next((a for a in assets if (a.asset_type or "").upper() == "AUDIO"), None)
    audio_path = audio_asset.path if audio_asset else f"output/audio_{job_id}.mp3"
    final_video_path = f"output/video_{job_id}_9x16.mp4"
    
    success = await render_video_from_scenes(job_id, scenes, audio_path, final_video_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assemble updated video")
        
    meta["scenes"] = scenes
    meta["video_url"] = f"/output/video_{job_id}_9x16.mp4?t={ts}"
    await repository.update_asset_metadata(video_asset.id, meta)
    
    return {
        "status": "success",
        "scene": sc,
        "video_url": meta["video_url"],
        "media_type": norm_result["type"],
        "message": f"Custom {norm_result['type']} applied to Scene #{scene_index + 1}"
    }

@router.post('/{job_id}/regenerate-audio')
async def regenerate_audio(job_id: int, req: RegenerateAudioRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    if not video_asset or not video_asset.metadata_json:
        raise HTTPException(status_code=400, detail="Video asset not found")
    
    meta = dict(video_asset.metadata_json)
    scenes = req.scenes or meta.get("scenes", [])
    voice = req.voice or meta.get("voice", "en-US-AriaNeural")
    
    full_narration = " ".join(s["text"] for s in scenes)
    audio_path = f"output/audio_{job_id}.mp3"
    
    import edge_tts
    communicate = edge_tts.Communicate(full_narration, voice)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
                
    total_audio_duration = get_audio_duration(audio_path)
    total_words = sum(len(s["text"].split()) for s in scenes) or 1
    current_time = 0.0
    for s in scenes:
        w_count = len(s["text"].split())
        calc_dur = round((w_count / total_words) * total_audio_duration, 2)
        calc_dur = max(calc_dur, 2.5)
        s["start"] = round(current_time, 2)
        s["duration"] = calc_dur
        current_time += calc_dur
        
    scale_factor = total_audio_duration / max(current_time, 1.0)
    for s in scenes:
        s["duration"] = round(s["duration"] * scale_factor, 2)
        
    final_video_path = f"output/video_{job_id}_9x16.mp4"
    await render_video_from_scenes(job_id, scenes, audio_path, final_video_path)
    
    ts = int(datetime.utcnow().timestamp())
    meta["scenes"] = scenes
    meta["duration"] = total_audio_duration
    meta["voice"] = voice
    meta["video_url"] = f"/output/video_{job_id}_9x16.mp4?t={ts}"
    await repository.update_asset_metadata(video_asset.id, meta)
    
    return {"status": "success", "duration": total_audio_duration, "video_url": meta["video_url"], "scenes": scenes}

@router.post('/{job_id}/publish')
async def publish_job(job_id: int, req: PublishRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await repository.update_job_status(job_id, JobStatus.COMPLETED, "PUBLISHED")
    return {
        "status": "success",
        "job_id": job_id,
        "published_platforms": req.platforms,
        "cookie_status": "Active",
        "message": f"Approved and scheduled to {', '.join(req.platforms)}"
    }

@router.post('/{job_id}/upload-anchor')
async def upload_job_anchor(job_id: int, file: UploadFile = File(...)):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dir = os.path.abspath(f"jobs/{job_id}")
    os.makedirs(job_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1].lower() or ".png"
    anchor_filename = f"anchor_reference{file_ext}"
    anchor_path = os.path.join(job_dir, anchor_filename)
    
    content = await file.read()
    with open(anchor_path, "wb") as f:
        f.write(content)
        
    config = dict(job.config or {})
    config["anchor_image_path"] = anchor_path
    config["anchor_url"] = f"/jobs/{job_id}/{anchor_filename}"
    await repository.update_job_config(job_id, config)
    
    return {
        "status": "success",
        "job_id": job_id,
        "anchor_path": anchor_path,
        "anchor_url": config["anchor_url"],
        "message": "Custom visual anchor uploaded successfully"
    }

@router.post('/{job_id}/delete-temp')
async def delete_job_temp(job_id: int):
    cleaned = 0
    if os.path.exists("temp"):
        for f in os.listdir("temp"):
            if f.startswith(f"instant_{job_id}"):
                try:
                    os.remove(os.path.join("temp", f))
                    cleaned += 1
                except OSError:
                    pass
    return {"status": "success", "cleaned_files": cleaned, "message": f"Cleaned {cleaned} temporary scene files"}

@router.get('/{job_id}/thumbnails')
async def get_job_thumbnails(job_id: int):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    meta = dict(video_asset.metadata_json or {}) if video_asset else {}

    if "thumbnails" in meta and meta["thumbnails"]:
        return meta["thumbnails"]

    from backend.engine.thumbnail_engine import generate_job_thumbnails
    manifest = None
    manifest_path = os.path.join("jobs", str(job_id), "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    if not manifest:
        manifest = {
            "topic": meta.get("title", job.niche),
            "fact_dossier": meta.get("fact_dossier", {})
        }

    thumb_data = await generate_job_thumbnails(job_id=job_id, manifest=manifest, job_dir=f"jobs/{job_id}")
    if video_asset:
        meta["thumbnails"] = thumb_data
        await repository.update_asset_metadata(video_asset.id, meta)

    return thumb_data

@router.post('/{job_id}/thumbnails/generate')
async def regenerate_job_thumbnails(job_id: int):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    meta = dict(video_asset.metadata_json or {}) if video_asset else {}

    from backend.engine.thumbnail_engine import generate_job_thumbnails
    manifest = None
    manifest_path = os.path.join("jobs", str(job_id), "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    if not manifest:
        manifest = {
            "topic": meta.get("title", job.niche),
            "fact_dossier": meta.get("fact_dossier", {})
        }

    thumb_data = await generate_job_thumbnails(job_id=job_id, manifest=manifest, job_dir=f"jobs/{job_id}")
    if video_asset:
        meta["thumbnails"] = thumb_data
        await repository.update_asset_metadata(video_asset.id, meta)

    return {"status": "success", "thumbnails": thumb_data, "message": "Thumbnails regenerated successfully"}

@router.delete('/{job_id}')
async def delete_job(job_id: int):
    success = await repository.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "message": f"Job #{job_id} deleted"}

@router.delete('')
async def clear_all_jobs(status: Optional[str] = None):
    deleted_count = await repository.delete_all_jobs(status_filter=status)
    return {"status": "success", "deleted_count": deleted_count, "message": f"Cleared {deleted_count} jobs"}
