from fastapi import APIRouter
from pydantic import BaseModel
import logging
import time
from backend.state import ACTIVE_JOBS
from backend.vault import repository

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkflowRunRequest(BaseModel):
    niche: str
    triggerType: str


@router.get('/spec')
async def get_workflow_spec():
    return {"workflow": {"nodes": [], "edges": []}}


@router.post('/run')
async def run_workflow(req: WorkflowRunRequest):
    logger.info(f"Running workflow for niche: {req.niche}")
    return {"status": "success", "message": "Triggered via jobs endpoint normally."}


@router.get('/executions')
async def get_executions():
    """
    Builds workflow execution telemetry from real persisted Job and JobStage records
    in SQLite (`repository.get_jobs` + `repository.get_job_stages`), supplemented by live `ACTIVE_JOBS`.
    Never fabricates hardcoded 3500ms/4200ms/8000ms stage durations.
    """
    executions = []
    seen_ids = set()

    # 1. Query persisted jobs and their real JobStage rows from SQLite
    try:
        db_jobs = await repository.get_jobs(limit=25)
        for job in db_jobs:
            seen_ids.add(str(job.id))
            db_stages = await repository.get_job_stages(job.id)

            raw_status = (job.status.value if hasattr(job.status, "value") else str(job.status)).upper()
            if raw_status == "COMPLETED":
                status_enum = "SUCCESS"
            elif raw_status == "FAILED":
                status_enum = "ERROR"
            else:
                status_enum = "RUNNING"

            steps = []
            for st in db_stages:
                st_status_raw = (st.status.value if hasattr(st.status, "value") else str(st.status)).upper()
                if st_status_raw == "COMPLETED":
                    step_status = "success"
                elif st_status_raw == "FAILED":
                    step_status = "error"
                else:
                    step_status = "running"

                dur_ms = 0
                if st.started_at and st.completed_at:
                    dur_ms = int(max(0.0, (st.completed_at - st.started_at).total_seconds() * 1000))
                elif st.started_at:
                    from datetime import datetime
                    dur_ms = int(max(0.0, (datetime.utcnow() - st.started_at).total_seconds() * 1000))

                steps.append({
                    "nodeId": f"stage-{st.id}",
                    "nodeName": st.stage_name,
                    "status": step_status,
                    "durationMs": dur_ms,
                    "outputData": st.output_json or {"stage": st.stage_name},
                })

            if not steps and job.current_stage:
                steps.append({
                    "nodeId": f"stage-current-{job.id}",
                    "nodeName": job.current_stage,
                    "status": "success" if status_enum == "SUCCESS" else ("error" if status_enum == "ERROR" else "running"),
                    "durationMs": 0,
                    "outputData": {"stage": job.current_stage},
                })

            started_ms = int(job.created_at.timestamp() * 1000) if job.created_at else int(time.time() * 1000)
            updated_ms = int(job.updated_at.timestamp() * 1000) if job.updated_at else started_ms
            total_dur_ms = max(0, updated_ms - started_ms) if status_enum != "RUNNING" else max(0, int(time.time() * 1000) - started_ms)

            executions.append({
                "id": str(job.id),
                "workflowName": "Documentary Video Pipeline",
                "status": status_enum,
                "triggerType": "MANUAL",
                "startedAt": str(started_ms),
                "durationMs": total_dur_ms,
                "niche": job.niche or "Untitled Job",
                "nodesCount": len(steps),
                "steps": steps,
            })
    except Exception as e:
        logger.warning(f"[workflow] Could not load persisted job stages: {e}")

    # 2. Include any transient in-memory ACTIVE_JOBS not yet in seen_ids
    for j_id, j_data in ACTIVE_JOBS.items():
        if str(j_id) in seen_ids:
            continue
        status_enum = "RUNNING"
        if j_data.get("status") == "success":
            status_enum = "SUCCESS"
        elif j_data.get("status") == "error":
            status_enum = "ERROR"

        started_at = float(j_data.get("started_at", time.time() * 1000))
        completed_at = j_data.get("completed_at")
        duration_ms = int((completed_at - started_at) if completed_at else ((time.time() * 1000) - started_at))
        current_stage_name = j_data.get("stage", "Processing")

        steps = [{
            "nodeId": "live-stage",
            "nodeName": current_stage_name,
            "status": "success" if status_enum == "SUCCESS" else ("error" if status_enum == "ERROR" else "running"),
            "durationMs": max(0, duration_ms),
            "outputData": {"stage": current_stage_name, "progress": j_data.get("progress", "0%")},
        }]

        executions.append({
            "id": str(j_id),
            "workflowName": "Documentary Video Pipeline",
            "status": status_enum,
            "triggerType": "MANUAL",
            "startedAt": str(int(started_at)),
            "durationMs": max(0, duration_ms),
            "niche": j_data.get("niche", "Unknown Job"),
            "nodesCount": len(steps),
            "steps": steps,
        })

    return executions
