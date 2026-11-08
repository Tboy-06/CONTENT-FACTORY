# API Notes

Real endpoints based on `backend/api/*.py` analysis:

## Jobs (`/api/jobs`)
- `GET /api/jobs`: Returns array of formatted jobs (id, niche, status, current_stage, stages[], assets[], approvals[], costs[], analytics)
- `POST /api/jobs`: Creates a job. Body: `niche`, `referenceUrl`, `duration`, `format`, `premium`, `manual_approval`, `pipelineMode`, `spinStrategy`, `publishingStrategy`, `platforms`. Returns created job snippet.
- `POST /api/jobs/score-niche`: Body `{niche: string}`. Returns `{"status": "success", "data": ...}`
- `POST /api/jobs/{job_id}/advance`: Advances a job.
- `POST /api/jobs/{job_id}/approve`: Approves a job. Body `{notes?: string}`.
- `POST /api/jobs/{job_id}/reject`: Rejects a job. Body `{reason: string}`.
- `POST /api/jobs/{job_id}/upload-premium`: Upload premium asset.
- `GET /api/jobs/status`: Returns `{"status": "success", "jobs": { "job_id": {niche, status, stage, progress} }}`

## Workflow (`/api/workflow`)
- `GET /api/workflow/spec`: Returns `{"workflow": {"nodes": [], "edges": []}}`
- `POST /api/workflow/run`: Triggers a workflow.
- `GET /api/workflow/executions`: Returns array of execution steps and durations.

## Copilot (`/api/copilot`)
- `POST /api/copilot/chat`: Body `{prompt, system_prompt}`. Returns `{"response": "..."}`.

## Settings (`/api/settings`)
- `GET /api/settings`: Returns settings dict.
- `POST /api/settings`: Updates settings.

## WebSocket
- `/ws/pipeline`

## Missing Backend Capabilities for UI:
1. **Monthly Spend Cap:** The API returns `costs` per job in `GET /api/jobs`, but there is no endpoint for aggregated monthly spend. UI will show "unavailable" as per rules.
2. **Capabilities Data:** The backend does not expose which stages work offline vs online vs premium. The UI must be driven by backend data, but this data is missing.
3. **Health Check:** There is no `/api/health` endpoint for the connectivity checker to ping.
