## 2026-09-05T22:53:09Z

<USER_REQUEST>
You are the Project Orchestrator for this task.

Your Working Directory: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\orchestrator_1
Workspace Directory: C:\Users\User\antigravity\CONTENT-FACTORY
Original Request File: C:\Users\User\antigravity\CONTENT-FACTORY\.agents\ORIGINAL_REQUEST.md

Please read C:\Users\User\antigravity\CONTENT-FACTORY\.agents\ORIGINAL_REQUEST.md for the authoritative specifications and acceptance criteria.
Note: While the user's prompt mentions D:\CONTENT-FACTORY, the repository is located at C:\Users\User\antigravity\CONTENT-FACTORY.

Objective:
1. Update the FastAPI backend to calculate and return actual live metrics (total views across platforms, total jobs completed, real daily budget, and total spent) instead of static or missing fields in the VaultData payload.
2. Update the frontend types (`src/types.ts`) to include the new metric fields provided by the backend.
3. Update frontend React components (specifically `BottomStatusBar.tsx` and any relevant dashboard components) to remove hardcoded placeholder strings and dynamically consume live data from `vaultData.metrics`.
4. Ensure acceptance criteria are completely satisfied and verified with tests.

Maintain your `BRIEFING.md`, `plan.md`, and continuous updates in `progress.md` in your working directory.
When finished, send a completion message with full verification details.
</USER_REQUEST>
