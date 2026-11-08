# Original User Request

## Initial Request — 2026-09-05T22:52:35Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Remove hardcoded data from the frontend and integrate live data from the backend
> Requested team: [none]

Remove all hardcoded mock data (such as views, completed jobs, and budget) from the React frontend UI and update the backend to supply this live data in the VaultData payload.

Working directory: D:\CONTENT-FACTORY

## Requirements

### R1. Backend API Update
Update the FastAPI backend to calculate and return actual live metrics (such as total views across platforms, total jobs completed, real daily budget, and total spent) instead of static or missing fields. Ensure these are included in the `VaultData` payload sent to the frontend.

### R2. Frontend Types Update
Update the `VaultData` interface in `D:\CONTENT-FACTORY\frontend\src\types\index.ts` or `src\types.ts` to include the new metric fields (e.g., `totalViews`, `completedJobsCount`, etc.) provided by the backend.

### R3. UI Component Updates
Scan the frontend React components (specifically `BottomStatusBar.tsx` and any other layout components) for hardcoded placeholder strings (like `"12.4K views"`, `$0.02 spent`, `3 videos posted`). Replace all hardcoded values with dynamic data from the `vaultData` props.

## Acceptance Criteria

### Backend Validation
- [ ] The backend API endpoint that serves VaultData correctly fetches or calculates real metrics from the database or external APIs (where applicable) and includes them in the JSON response.

### Frontend Validation
- [ ] `BottomStatusBar.tsx` accesses views, spent, and completed jobs exclusively through `vaultData.metrics`.
- [ ] No hardcoded placeholder numbers (e.g., `"12.4K"`) remain in the status bar or primary dashboard components.
