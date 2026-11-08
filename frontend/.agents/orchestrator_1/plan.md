# Implementation Plan: Live Metrics Integration

## Mission
Transition from hardcoded mock metrics in the frontend UI to actual dynamic metrics calculated by the FastAPI backend and returned in the VaultData payload.

## Phases
1. **Phase 0: Architecture Survey & Discovery**
   - Survey the FastAPI backend: find where VaultData is generated, what models/database/API exist for platform views, completed jobs, daily budget, and total spent.
   - Survey frontend: locate `src/types.ts` or `src/types/index.ts`, `BottomStatusBar.tsx`, and any dashboard/layout components containing hardcoded metric strings.
   - Verify existing build/test tooling (pytest, npm/vite/tsc/jest/vitest).

2. **Phase 1: Backend Live Metrics Calculation**
   - Implement live calculations in FastAPI backend for `totalViews`, `completedJobsCount`, `dailyBudget`, and `totalSpent` (and any other related metric fields required by VaultData).
   - Add backend tests verifying endpoint responses.

3. **Phase 2: Frontend Types & UI Dynamic Data Integration**
   - Update `types.ts` / `src/types/index.ts` to include the new metric definitions in `VaultData`.
   - Update `BottomStatusBar.tsx` and any relevant dashboard components to read directly from `vaultData.metrics`.
   - Remove hardcoded mock strings (e.g. `"12.4K views"`, `"$0.02 spent"`, `"3 videos posted"`).

4. **Phase 3: Verification & Integrity Audit**
   - Review and adversarial testing with Challenger and Reviewer.
   - Forensic Auditor check for zero hardcoded mock values, authentic backend calculation, and complete test verification.
   - Final status report.
