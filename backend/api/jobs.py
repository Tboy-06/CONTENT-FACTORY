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

class GenerateBeatVideoRequest(BaseModel):
    prompt: Optional[str] = None
    image_path: Optional[str] = None
    duration: float = 4.0
    engine: str = "hf_ltx25"

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
    await repository.update_job_status(job.id, JobStatus.RUNNING, "SCRIPT")

    # Route directly through the unified 2-pass Documentary Engine so Copilot jobs never hang at SCRIPT
    asyncio.create_task(run_instant_pipeline(
        job.id,
        req.niche,
        req.voice or "en-US-AriaNeural",
        req.style_preset or "Dark Documentary",
        req.format or "9:16",
        req.duration or "60s",
        genre="auto"
    ))

    return {
        "id": job.id, 
        "niche": job.niche, 
        "status": "RUNNING", 
        "current_stage": "SCRIPT", 
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
    from backend.engine.assembler import (
        BEAT_CACHE_DIR,
        AI_CLIPS_CACHE_DIR,
        EXPORTS_CACHE_DIR,
        MAX_TEMP_CACHE_MB,
        enforce_lru_cache_cap,
    )
    enforce_lru_cache_cap(MAX_TEMP_CACHE_MB)

    def _scan_dir(d_path: str) -> tuple[int, int]:
        b_total = 0
        c_total = 0
        if os.path.exists(d_path):
            for root, _, files in os.walk(d_path):
                for fname in files:
                    if fname == "active_render.lock":
                        continue
                    fp = os.path.join(root, fname)
                    try:
                        b_total += os.path.getsize(fp)
                        c_total += 1
                    except OSError:
                        pass
        return b_total, c_total

    local_b, local_c = _scan_dir("temp")
    beat_b, beat_c = _scan_dir(BEAT_CACHE_DIR)
    ai_b, ai_c = _scan_dir(AI_CLIPS_CACHE_DIR)
    exp_b, exp_c = _scan_dir(EXPORTS_CACHE_DIR)
    temp_bytes = local_b + beat_b + ai_b + exp_b
    temp_count = local_c + beat_c + ai_c + exp_c

    output_bytes, output_count = _scan_dir("output")
    return {
        "temp_mb": round(temp_bytes / (1024 * 1024), 2),
        "temp_count": temp_count,
        "beat_cache_mb": round(beat_b / (1024 * 1024), 2),
        "ai_clips_mb": round(ai_b / (1024 * 1024), 2),
        "exports_mb": round(exp_b / (1024 * 1024), 2),
        "max_cap_mb": MAX_TEMP_CACHE_MB,
        "output_mb": round(output_bytes / (1024 * 1024), 2),
        "output_count": output_count,
    }

@router.post('/system/cache/clear')
async def clear_cache():
    from backend.engine.assembler import BEAT_CACHE_DIR, AI_CLIPS_CACHE_DIR, EXPORTS_CACHE_DIR
    freed_bytes = 0
    cleaned_count = 0
    for target_dir in ("temp", BEAT_CACHE_DIR, AI_CLIPS_CACHE_DIR, EXPORTS_CACHE_DIR):
        if os.path.exists(target_dir):
            for root, _, files in os.walk(target_dir):
                for f in files:
                    if f == "active_render.lock":
                        continue
                    fp = os.path.join(root, f)
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
        "message": f"Freed {round(freed_bytes / (1024 * 1024), 2)} MB across beat_cache, ai_clips, exports, and temp storage."
    }

async def _rebuild_job_via_pass2(
    job_id: int,
    scenes: List[Dict[str, Any]],
    action_label: str = "qc1_edit",
    modified_indices: Optional[List[int]] = None,
    regenerate_voice: Optional[str] = None,
) -> tuple[str, List[Dict[str, Any]], float]:
    """
    Unified 2-Pass Documentary Re-Assembler for all `QC1` edits (`AI Video`, `Re-roll`, `Upload Clip`, `Regenerate Audio`).
    - Saves a `manifest_history/v{N}.json` undo snapshot first
    - Preserves `.ASS` active-word captions, sidechain-ducked BGM, timed SFX, and SHA-256 cached beats
    - Writes master output to `output/instant_{job_id}.mp4`
    """
    import json
    from backend.api.copilot import get_or_create_manifest, save_manifest_history_snapshot
    from backend.engine.assembler import (
        assemble_final_pass2,
        get_job_scratch_dir,
        render_beat_pass1,
        resolve_local_media_path,
        to_public_job_url,
    )
    from backend.engine.audio_subs import synthesize_documentary_audio_and_subs

    job_dir = get_job_scratch_dir(job_id)
    manifest = await get_or_create_manifest(job_id)
    save_manifest_history_snapshot(job_id, manifest, action_label=action_label)

    # Flatten beats from manifest
    beats = manifest.get("beats") or []
    if not beats and manifest.get("sentences"):
        for s in manifest["sentences"]:
            beats.extend(s.get("beats", []))
        manifest["beats"] = beats

    # Sync scene edits onto beats
    mod_set = set(modified_indices or [])
    for idx, sc in enumerate(scenes):
        if idx >= len(beats):
            break
        b = beats[idx]
        if sc.get("prompt"):
            b["prompt"] = sc["prompt"]
            b["visual_prompt"] = sc["prompt"]
        if sc.get("duration"):
            b["duration"] = max(0.65, float(sc["duration"]))

        vid_cand = resolve_local_media_path(sc.get("video_path"))
        img_cand = resolve_local_media_path(sc.get("image_path"))
        if idx in mod_set:
            b["_force_reroll"] = True
            if vid_cand and os.path.exists(vid_cand):
                b["custom_media"] = vid_cand
                b["type"] = "ai_video" if sc.get("visual_type") == "ai_video" else "broll_video"
            elif sc.get("_uploaded_image") and img_cand and os.path.exists(img_cand):
                b["custom_media"] = img_cand
                b["type"] = "treated_image"
            else:
                b.pop("custom_media", None)
                if b.get("type") in ("motion_card", "declassified_scan", "evidence_board", "map_flyover"):
                    b["type"] = "treated_image"
                old_plate = os.path.join(job_dir, "beats", f"{b['id']}_plate.png")
                if os.path.exists(old_plate):
                    try:
                        os.remove(old_plate)
                    except OSError:
                        pass

    # Optional full voice + active-word .ASS subtitle regeneration when narration or voice changes
    if regenerate_voice:
        sentences = manifest.get("sentences") or []
        if sentences:
            # Map non-empty scene text edits back onto sentences (each sentence owns ~2 beats)
            non_empty_texts = [str(sc.get("text") or "").strip() for sc in scenes if str(sc.get("text") or "").strip()]
            if len(non_empty_texts) == len(sentences):
                for s_i, s_obj in enumerate(sentences):
                    s_obj["text"] = non_empty_texts[s_i]
        manifest = await synthesize_documentary_audio_and_subs(manifest, job_dir, voice=regenerate_voice)

    # Re-render modified beats via Pass 1 (untouched beats hit SHA-256 cache in ~0ms)
    for idx in sorted(mod_set):
        if 0 <= idx < len(beats):
            b = beats[idx]
            rendered_p = await render_beat_pass1(b, job_dir)
            plate_p = os.path.join(job_dir, "beats", f"{b['id']}_plate.png")
            if os.path.exists(plate_p):
                scenes[idx]["image_path"] = to_public_job_url(plate_p, job_id)
            elif rendered_p and os.path.exists(rendered_p):
                scenes[idx]["image_path"] = to_public_job_url(rendered_p, job_id)

    manifest_path = os.path.join(job_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    final_video_path = f"output/instant_{job_id}.mp4"
    ok = await assemble_final_pass2(manifest, job_dir, final_video_path)
    if not ok or not os.path.exists(final_video_path):
        raise HTTPException(status_code=500, detail="Failed to assemble documentary master video")

    ts = int(datetime.utcnow().timestamp())
    total_dur = float(manifest.get("actual_duration") or manifest.get("total_duration") or 45.0)
    return f"/output/instant_{job_id}.mp4?t={ts}", scenes, total_dur


@router.get('/video-gen/status')
async def get_video_gen_engine_status():
    from backend.engine.video_gen import get_video_gen_status
    return get_video_gen_status()


@router.post('/{job_id}/beats/{beat_id}/generate-video')
async def generate_beat_ai_video(job_id: int, beat_id: str, req: GenerateBeatVideoRequest):
    """
    Generates a real moving AI video clip for a specific beat using Hugging Face ZeroGPU
    (`Lightricks/LTX-2.5` with native audio or `Wan 2.2 14B I2V`) at $0 cost, and re-stitches
    via Pass 2 while preserving `.ASS` captions, BGM ducking, and SFX.
    """
    from backend.engine import video_gen
    from backend.engine.assembler import resolve_local_media_path

    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    if not video_asset or not video_asset.metadata_json:
        raise HTTPException(status_code=400, detail="Video asset not found for job")

    meta = dict(video_asset.metadata_json)
    scenes = meta.get("scenes", [])

    scene_index = 0
    if beat_id.isdigit():
        scene_index = int(beat_id)
    else:
        import re
        m = re.search(r"(\d+)", beat_id)
        if m:
            val = int(m.group(1))
            scene_index = val - 1 if beat_id.lower().startswith("beat_") and val > 0 else val

    if scene_index < 0 or scene_index >= len(scenes):
        raise HTTPException(status_code=400, detail=f"Invalid beat index: {beat_id}")

    sc = scenes[scene_index]
    prompt = (req.prompt or sc.get("prompt") or sc.get("text") or job.niche).strip()
    raw_ref = req.image_path or sc.get("image_path") or (job.config or {}).get("anchor_image_path")
    ref_img = resolve_local_media_path(raw_ref)

    dur = float(req.duration or sc.get("duration") or 4.0)
    gen_res = await asyncio.to_thread(
        video_gen.generate_ai_video_clip,
        prompt=prompt,
        image_path=ref_img,
        duration=dur,
        mode="free_hf",
        engine=req.engine or "hf_ltx25",
    )

    if gen_res.get("status") != "success" or not gen_res.get("video_path"):
        return {
            "status": gen_res.get("status", "quota_exhausted"),
            "scene_index": scene_index,
            "scene": sc,
            "reason": gen_res.get("reason") or gen_res.get("message"),
            "flow_handoff": gen_res.get("flow_handoff"),
        }

    clip_path = gen_res["video_path"]
    sc["video_path"] = clip_path
    sc["visual_type"] = "ai_video"
    sc["prompt"] = prompt
    sc["ai_engine"] = gen_res.get("engine_used")
    sc["has_native_audio"] = gen_res.get("has_native_audio", False)

    video_url, scenes, _ = await _rebuild_job_via_pass2(
        job_id=job_id,
        scenes=scenes,
        action_label=f"ai_video_beat_{scene_index + 1}",
        modified_indices=[scene_index],
    )
    meta["scenes"] = scenes
    meta["video_url"] = video_url
    await repository.update_asset_metadata(video_asset.id, meta)

    return {
        "status": "success",
        "scene_index": scene_index,
        "scene": scenes[scene_index],
        "video_url": video_url,
        "video_gen": gen_res,
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
    sc.pop("video_path", None)

    video_url, scenes, _ = await _rebuild_job_via_pass2(
        job_id=job_id,
        scenes=scenes,
        action_label=f"reroll_beat_{req.scene_index + 1}",
        modified_indices=[req.scene_index],
    )
    meta["scenes"] = scenes
    meta["style_preset"] = style
    meta["video_url"] = video_url
    await repository.update_asset_metadata(video_asset.id, meta)

    return {"status": "success", "scene": scenes[req.scene_index], "video_url": video_url}


@router.post('/{job_id}/scenes/{scene_index}/upload-custom-media')
async def upload_custom_scene_media(
    job_id: int,
    scene_index: int,
    file: UploadFile = File(...)
):
    from backend.engine.assembler import AI_CLIPS_CACHE_DIR
    from backend.engine.visual_cortex import normalize_custom_media

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

    os.makedirs(AI_CLIPS_CACHE_DIR, exist_ok=True)
    raw_ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    raw_path = os.path.join(AI_CLIPS_CACHE_DIR, f"custom_upload_{job_id}_{scene_index}_{ts}_raw{raw_ext}")

    content = await file.read()
    with open(raw_path, "wb") as f:
        f.write(content)

    is_video = raw_ext in (".mp4", ".mov", ".mkv", ".webm", ".avi")
    normalized_path = os.path.join(AI_CLIPS_CACHE_DIR, f"custom_{job_id}_{scene_index}_{ts}{'.mp4' if is_video else '.jpg'}")
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
        sc["visual_type"] = "broll_video"
        sc.pop("_uploaded_image", None)
    else:
        sc["image_path"] = normalized_path
        sc["video_path"] = None
        sc["visual_type"] = "treated_image"
        sc["_uploaded_image"] = True

    video_url, scenes, _ = await _rebuild_job_via_pass2(
        job_id=job_id,
        scenes=scenes,
        action_label=f"upload_media_beat_{scene_index + 1}",
        modified_indices=[scene_index],
    )
    scenes[scene_index].pop("_uploaded_image", None)
    meta["scenes"] = scenes
    meta["video_url"] = video_url
    await repository.update_asset_metadata(video_asset.id, meta)

    return {
        "status": "success",
        "scene": scenes[scene_index],
        "video_url": video_url,
        "media_type": norm_result["type"],
        "message": f"Custom {norm_result['type']} applied to Scene #{scene_index + 1} with captions & BGM preserved"
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
    voice = req.voice or meta.get("voice", "en-US-AndrewMultilingualNeural")

    video_url, scenes, total_audio_duration = await _rebuild_job_via_pass2(
        job_id=job_id,
        scenes=scenes,
        action_label="regenerate_audio_and_pacing",
        modified_indices=list(range(len(scenes))),
        regenerate_voice=voice,
    )

    meta["scenes"] = scenes
    meta["duration"] = total_audio_duration
    meta["voice"] = voice
    meta["video_url"] = video_url
    await repository.update_asset_metadata(video_asset.id, meta)

    return {"status": "success", "duration": total_audio_duration, "video_url": video_url, "scenes": scenes}

@router.post('/{job_id}/publish')
async def publish_job(job_id: int, req: PublishRequest):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from backend.config import get_settings
    cfg = get_settings()
    env_postiz = os.environ.get("POSTIZ_API_KEY")
    raw_postiz_key = env_postiz if env_postiz is not None else (cfg.postiz_api_key or "")
    postiz_key = raw_postiz_key.strip()
    if any(p in postiz_key.lower() for p in ("your_", "placeholder", "changeme", "none", "todo", "xxx")):
        postiz_key = ""
    postiz_url = (cfg.postiz_url or os.environ.get("POSTIZ_URL") or "").strip()

    # Never falsely claim "PUBLISHED" without a real external provider post_id
    if not postiz_key:
        await repository.update_job_status(job_id, JobStatus.COMPLETED, "READY_TO_PUBLISH")
        return {
            "status": "READY_TO_PUBLISH",
            "publish_state": "READY_TO_PUBLISH",
            "published": False,
            "post_id": None,
            "job_id": job_id,
            "published_platforms": [],
            "requested_platforms": req.platforms,
            "cookie_status": "Not Configured",
            "message": (
                f"Video passed QC1 and is marked READY_TO_PUBLISH for {', '.join(req.platforms)}. "
                "Configure POSTIZ_API_KEY in Settings to enable automated social upload."
            ),
        }

    await repository.update_job_status(job_id, JobStatus.RUNNING, "PUBLISHING")
    try:
        import urllib.request
        payload = json.dumps({
            "job_id": job_id,
            "title": job.niche,
            "platforms": req.platforms,
        }).encode("utf-8")
        api_req = urllib.request.Request(
            f"{postiz_url.rstrip('/')}/api/posts",
            data=payload,
            headers={
                "Authorization": f"Bearer {postiz_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(api_req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            external_post_id = resp_data.get("id") or resp_data.get("post_id")

        if not external_post_id:
            await repository.update_job_status(job_id, JobStatus.COMPLETED, "PUBLISH_FAILED")
            return {
                "status": "PUBLISH_FAILED",
                "publish_state": "PUBLISH_FAILED",
                "published": False,
                "post_id": None,
                "job_id": job_id,
                "published_platforms": [],
                "requested_platforms": req.platforms,
                "message": "Uploader responded without a verified external post_id.",
            }

        await repository.update_job_status(job_id, JobStatus.COMPLETED, "PUBLISHED")
        return {
            "status": "PUBLISHED",
            "publish_state": "PUBLISHED",
            "published": True,
            "post_id": str(external_post_id),
            "job_id": job_id,
            "published_platforms": req.platforms,
            "cookie_status": "Active",
            "message": f"Published to {', '.join(req.platforms)} (post_id={external_post_id})",
        }
    except Exception as pub_err:
        await repository.update_job_status(job_id, JobStatus.COMPLETED, "PUBLISH_FAILED")
        return {
            "status": "PUBLISH_FAILED",
            "publish_state": "PUBLISH_FAILED",
            "published": False,
            "post_id": None,
            "job_id": job_id,
            "published_platforms": [],
            "requested_platforms": req.platforms,
            "message": f"Social provider upload failed: {pub_err}",
        }

@router.post('/{job_id}/upload-anchor')
async def upload_job_anchor(job_id: int, file: UploadFile = File(...)):
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    from backend.engine.assembler import get_job_scratch_dir
    job_dir = get_job_scratch_dir(job_id)
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
    from backend.engine.assembler import get_job_scratch_dir
    job_dir = get_job_scratch_dir(job_id)
    manifest = None
    manifest_path = os.path.join(job_dir, "manifest.json")
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

    thumb_data = await generate_job_thumbnails(job_id=job_id, manifest=manifest, job_dir=job_dir)
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
    from backend.engine.assembler import get_job_scratch_dir
    job_dir = get_job_scratch_dir(job_id)
    manifest = None
    manifest_path = os.path.join(job_dir, "manifest.json")
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

    thumb_data = await generate_job_thumbnails(job_id=job_id, manifest=manifest, job_dir=job_dir)
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


from backend.config import get_settings as _get_job_settings

EXPORTS_DIR = _get_job_settings().exports_dir
os.makedirs(EXPORTS_DIR, exist_ok=True)


def _ass_timestamp_to_srt(ass_ts: str) -> str:
    """Converts ASS timestamp H:MM:SS.cc to SRT timestamp HH:MM:SS,mmm."""
    parts = ass_ts.strip().split(":")
    if len(parts) != 3:
        return "00:00:00,000"
    h = int(parts[0])
    m = int(parts[1])
    sec_parts = parts[2].split(".")
    s = int(sec_parts[0])
    cs = int(sec_parts[1][:2]) if len(sec_parts) > 1 else 0
    return f"{h:02d}:{m:02d}:{s:02d},{cs * 10:03d}"


def _convert_ass_to_srt(ass_content: str) -> str:
    """Converts ASS Dialogue lines into clean SRT subtitle blocks."""
    import re
    srt_blocks = []
    idx = 1
    for line in ass_content.splitlines():
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) >= 10:
                start_srt = _ass_timestamp_to_srt(parts[1])
                end_srt = _ass_timestamp_to_srt(parts[2])
                raw_text = parts[9].strip()
                clean_text = re.sub(r"\{.*?\}", "", raw_text).replace("\\N", "\n").strip()
                if clean_text:
                    srt_blocks.append(f"{idx}\n{start_srt} --> {end_srt}\n{clean_text}\n")
                    idx += 1
    return "\n".join(srt_blocks) if srt_blocks else "1\n00:00:00,000 --> 00:00:02,000\nDocumentary Audio Track\n"


async def build_job_export_zip(job_id: int, job_dir_override: Optional[str] = None) -> str:
    """
    Bundles final_9x16.mp4, thumbnail.jpg (if present), captions.ass, captions.srt,
    and upload_copy.txt into exports/job_{job_id}_export.zip in external scratch storage.
    """
    import json
    import re
    import zipfile
    from backend.engine.vault_graph import format_topic_title

    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = await repository.get_job_assets(job_id)
    video_asset = next((a for a in assets if (a.asset_type or "").upper() == "VIDEO"), None)
    meta = dict(video_asset.metadata_json or {}) if video_asset and getattr(video_asset, "metadata_json", None) else {}

    from backend.engine.assembler import get_job_scratch_dir
    job_dir = job_dir_override or get_job_scratch_dir(job_id)
    manifest_path = os.path.join(job_dir, "manifest.json")
    manifest: Dict[str, Any] = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            pass

    # 1. Locate final video file
    video_candidates = [
        video_asset.path if (video_asset and getattr(video_asset, "path", None)) else None,
        os.path.join(job_dir, "final_9x16.mp4"),
        f"output/instant_{job_id}.mp4",
        f"output/video_{job_id}_9x16.mp4",
        os.path.join(_get_job_settings().archive_outputs_dir, f"instant_{job_id}.mp4"),
    ]
    resolved_video = next((p for p in video_candidates if p and os.path.exists(p)), None)

    # 2. Locate thumbnail if present
    thumb_candidates = [
        f"output/thumb_{job_id}_v1_9x16.jpg",
        f"output/thumb_{job_id}_v1_16x9.jpg",
        os.path.join(job_dir, "hero_plate.png"),
    ]
    resolved_thumb = next((p for p in thumb_candidates if p and os.path.exists(p)), None)

    # 3. Locate captions.ass
    ass_candidates = [
        meta.get("captions_ass_path"),
        manifest.get("captions_ass_path"),
        os.path.join(job_dir, "captions.ass"),
    ]
    resolved_ass = next((p for p in ass_candidates if p and os.path.exists(p)), None)

    # 4. Build upload_copy.txt
    raw_topic = manifest.get("topic") or meta.get("title") or getattr(job, "niche", f"Job {job_id}")
    clean_title = format_topic_title(raw_topic)
    sentences = manifest.get("sentences", [])
    hook_line = (
        sentences[0].get("text")
        if sentences and isinstance(sentences[0], dict)
        else (meta.get("hook") or f"The documented story behind {clean_title}.")
    )
    tag_words = [re.sub(r"[^a-zA-Z0-9]", "", w).lower() for w in clean_title.split() if len(w) > 2]
    hashtags = " ".join([f"#{w}" for w in tag_words[:5]] + ["#documentary", "#shorts", "#investigation"])
    verification_state = manifest.get("verification_status") or (
        manifest.get("fact_dossier", {}).get("verification_status") if isinstance(manifest.get("fact_dossier"), dict) else "VERIFIED"
    )

    upload_copy = (
        f"TITLE:\n{clean_title}\n\n"
        f"HOOK:\n{hook_line}\n\n"
        f"DESCRIPTION:\n{hook_line}\n\n"
        f"Investigative documentary breakdown on {clean_title}.\n\n"
        f"HASHTAGS:\n{hashtags}\n\n"
        f"VERIFICATION STATUS:\n{verification_state}\n"
    )

    os.makedirs(EXPORTS_DIR, exist_ok=True)
    zip_path = os.path.join(EXPORTS_DIR, f"job_{job_id}_export.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if resolved_video and os.path.exists(resolved_video):
            zf.write(resolved_video, arcname="final_9x16.mp4")
        if resolved_thumb and os.path.exists(resolved_thumb):
            zf.write(resolved_thumb, arcname="thumbnail.jpg")
        if resolved_ass and os.path.exists(resolved_ass):
            zf.write(resolved_ass, arcname="captions.ass")
            try:
                ass_text = open(resolved_ass, "r", encoding="utf-8", errors="ignore").read()
                zf.writestr("captions.srt", _convert_ass_to_srt(ass_text))
            except Exception:
                zf.writestr("captions.srt", "1\n00:00:00,000 --> 00:00:02,000\nDocumentary Audio Track\n")
        else:
            zf.writestr("captions.srt", f"1\n00:00:00,000 --> 00:00:03,000\n{hook_line}\n")
        zf.writestr("upload_copy.txt", upload_copy)

    return zip_path


@router.get('/{job_id}/export')
async def download_job_export_pack(job_id: int):
    from fastapi.responses import FileResponse
    zip_path = await build_job_export_zip(job_id)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"content_factory_job_{job_id}_export.zip",
    )


@router.post('/{job_id}/export')
async def create_job_export_pack(job_id: int):
    zip_path = await build_job_export_zip(job_id)
    return {
        "status": "success",
        "job_id": job_id,
        "export_zip_path": zip_path,
        "download_url": f"/api/jobs/{job_id}/export",
        "message": f"Publish-ready export bundle created at {zip_path}",
    }
