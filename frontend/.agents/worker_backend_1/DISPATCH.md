## 2026-09-06T00:00:05Z

You are teamwork_preview_worker (Backend Implementation Specialist).
Your working directory is: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\worker_backend_1
Workspace Directory: C:\Users\User\antigravity\CONTENT-FACTORY
Authoritative Original Request: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\ORIGINAL_REQUEST.md (MANDATORY: You must read this file first before proceeding).

Please also read:
- Project Specification: C:\Users\User\antigravity\CONTENT-FACTORY\PROJECT.md
- Backend Exploration Report: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\explorer_survey_1\handoff.md
- Integration Report: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\explorer_survey_3\handoff.md

FILE WRITE OWNERSHIP:
You exclusively own and may edit the following files:
- backend/vault/repository.py
- dashboard/main.py
- server.ts
- tests/test_vault.py (new test file)
Do NOT edit any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Tasks (Milestone 1: Backend Live Metrics):
1. In `backend/vault/repository.py`:
   - Implement `get_total_views() -> int` using SQLAlchemy async aggregation over `Analytics.views` with `func.coalesce(func.sum(Analytics.views), 0)`.
   - Implement `get_completed_jobs_count() -> int` querying count of jobs with `status == JobStatus.COMPLETED`.
   - Implement `get_active_jobs_count() -> int` querying count of jobs with `status != JobStatus.COMPLETED`.
2. In `dashboard/main.py`:
   - Implement `GET /api/vault` returning `VaultDataResponse` with `metrics` (`totalSpent`, `totalTokens`, `totalRevenue`, `dailyBudget`, `activeJobsCount`, `completedJobsCount`, `totalViews`) and lists for `styleGuides`, `characterBibles`, `hookFormulas`, `logs`.
   - Ensure all `metrics` fields are raw numbers.
3. In `server.ts` (Express dev server):
   - Update `app.get("/api/vault")` (lines ~891-910) so `totalViews` is calculated dynamically across jobs (`jobsStore.reduce((acc, j) => acc + (j.analytics?.views || 0), 0)`) and included in the `metrics` payload for dev server parity.
4. In `tests/test_vault.py`:
   - Create automated pytest tests validating:
     - Repository methods (`get_total_views`, `get_completed_jobs_count`, `get_active_jobs_count`).
     - FastAPI `GET /api/vault` response status 200 and schema contract.
5. Verification:
   - Run `pytest` or `python -m unittest discover tests` to ensure all tests pass.
6. Write a complete handoff report to `C:\Users\User\antigravity\CONTENT-FACTORY\.agents\worker_backend_1\handoff.md` with Observation, Logic Chain, Caveats, Conclusion, Verification Method (exact command and terminal output).
7. Send a message to parent reporting completion and referencing the handoff path.
