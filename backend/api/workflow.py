from fastapi import APIRouter
from pydantic import BaseModel
import logging
import time
from backend.state import ACTIVE_JOBS

logger = logging.getLogger(__name__)

router = APIRouter()

class WorkflowRunRequest(BaseModel):
    niche: str
    triggerType: str

@router.get('/spec')
async def get_workflow_spec():
    # In a real app, this could return the JSON spec of nodes/edges.
    # The frontend falls back to defaultWorkflowSpec if this returns empty.
    return {"workflow": {"nodes": [], "edges": []}}

@router.post('/run')
async def run_workflow(req: WorkflowRunRequest):
    logger.info(f"Running workflow for niche: {req.niche}")
    # Note: Real execution is launched from /api/jobs. This is just for the mock "Run" button on the execution board.
    return {"status": "success", "message": "Triggered via jobs endpoint normally."}

@router.get('/executions')
async def get_executions():
    # Convert ACTIVE_JOBS into WorkflowExecution array for the UI
    executions = []
    for j_id, j_data in ACTIVE_JOBS.items():
        # Determine status enum
        status_enum = "RUNNING"
        if j_data.get("status") == "success":
            status_enum = "SUCCESS"
        elif j_data.get("status") == "error":
            status_enum = "ERROR"
            
        progress_str = j_data.get("progress", "0%")
        progress_val = int(progress_str.replace('%', '')) if '%' in progress_str else 0
        
        # Build mock steps based on progress
        steps = []
        if progress_val >= 10:
            steps.append({
                "nodeId": "llm-1",
                "nodeName": "Director Agent (Script)",
                "status": "success",
                "durationMs": 3500,
                "outputData": {"stage": "Script Generation"}
            })
        if progress_val >= 40:
            steps.append({
                "nodeId": "tts-1",
                "nodeName": "Voice Actor Agent (TTS)",
                "status": "success",
                "durationMs": 4200,
                "outputData": {"stage": "Audio Generation"}
            })
        if progress_val >= 70:
            steps.append({
                "nodeId": "ffmpeg-1",
                "nodeName": "Video Editor (FFmpeg)",
                "status": "success" if progress_val == 100 else "running",
                "durationMs": 8000,
                "outputData": {"stage": "Video Assembly"}
            })
            
        # If it's still running, add a running step for current stage
        if status_enum == "RUNNING" and progress_val < 100:
             steps.append({
                "nodeId": "current-step",
                "nodeName": j_data.get("stage", "Processing"),
                "status": "running",
                "durationMs": 0
            })
            
        started_at = j_data.get("started_at", time.time() * 1000)
        
        # Calculate duration based on completion or current time
        completed_at = j_data.get("completed_at")
        if completed_at:
            duration_ms = completed_at - started_at
        else:
            duration_ms = (time.time() * 1000) - started_at
            
        executions.append({
            "id": j_id,
            "workflowName": "Default Video Pipeline",
            "status": status_enum,
            "triggerType": "MANUAL",
            "startedAt": str(int(started_at)),
            "durationMs": max(0, duration_ms),
            "niche": j_data.get("niche", "Unknown Job"),
            "nodesCount": len(steps),
            "steps": steps
        })
        
    return executions
