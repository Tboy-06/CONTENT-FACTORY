# Project: Content Factory Live Metrics Integration

## Architecture
Content Factory integrates a FastAPI backend (`dashboard/main.py`), a SQLAlchemy async ORM repository over SQLite (`backend/vault/`), an Express/Vite dev server (`server.ts`), and a React 19 SPA (`src/`).
The application displays pipeline execution metrics and vault data.

Data flow:
`SQLite (vault.db)` -> `Repository (backend/vault/repository.py)` -> `FastAPI GET /api/vault (dashboard/main.py)` -> `React App.tsx (fetch /api/vault)` -> `vaultData.metrics` -> `BottomStatusBar.tsx`, `Header.tsx`, `VaultExplorer.tsx`.

Development server (`server.ts`) provides an identical in-memory parity implementation of `GET /api/vault` with Vite middleware for local development.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Repository Aggregations | Add `get_total_views()`, `get_completed_jobs_count()`, and `get_active_jobs_count()` to `Repository` | M1 | Survey (Backend) |
| 2 | FastAPI /api/vault Endpoint | Implement `GET /api/vault` returning live `metrics` (including `totalViews`, `totalSpent`, `totalTokens`, `totalRevenue`, `dailyBudget`, `activeJobsCount`, `completedJobsCount`) and vault collections | M1 | Survey (Backend) |
| 3 | Dev Server Parity | Update `GET /api/vault` in `server.ts` to calculate `totalViews` from `jobsStore` | M1 | Survey (Integration) |
| 4 | Backend Automated Tests | Add `tests/test_vault.py` covering repository aggregations and `GET /api/vault` endpoint | M1 | Survey (Backend/Testing) |
| 5 | Frontend Types Definition | Update `VaultData.metrics` in `src/types.ts` to include `totalViews: number;` | M2 | Survey (Frontend) |
| 6 | BottomStatusBar Refactoring | Remove hardcoded `"12.4K"` string and fallbacks `1.20`, `10.00`, `3`. Consume `totalViews`, `completedJobsCount`, `totalSpent`, `dailyBudget` strictly from `vaultData.metrics` | M2 | Survey (Frontend) |
| 7 | Layout Components Cleanup | Clean up hardcoded budget in `Header.tsx` and fallback analytics strings in `PipelineBoard.tsx` | M2 | Survey (Frontend) |
| 8 | E2E & System Verification | Run pytest, tsc --noEmit, build bundle, and verify zero mock strings remaining | M3 | Survey (Integration) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Live Metrics | Repository queries, FastAPI `/api/vault`, `server.ts` parity, backend tests | none | DONE |
| M2 | Frontend Types & UI Components | `src/types.ts`, `BottomStatusBar.tsx`, `Header.tsx`, `App.tsx` | M1 | DONE |
| M3 | Comprehensive E2E Verification & Hardening | Full test suite execution, adversarial edge case verification, forensic audit | M1, M2 | DONE |

## Code Layout
- `backend/vault/repository.py`: Async database aggregations (Total views, jobs counts, costs).
- `dashboard/main.py`: FastAPI endpoints and Pydantic schemas for `/api/vault`.
- `server.ts`: Express development server `/api/vault` parity.
- `src/types.ts`: TypeScript definitions for `VaultData` and `metrics`.
- `src/components/BottomStatusBar.tsx`: Persistent bottom status bar displaying dynamic metrics.
- `src/components/Header.tsx`: Header and Settings modal showing dynamic daily budget.
- `src/App.tsx`: Top-level React container fetching `/api/vault` and passing `vaultData`.
- `tests/test_vault.py`: Automated pytest test suite for vault metrics and API endpoints.

## Interface Contracts
### Backend ↔ Frontend `/api/vault` Contract
Response JSON payload:
```json
{
  "metrics": {
    "totalViews": 184500,
    "totalSpent": 1.2345,
    "totalTokens": 45000,
    "totalRevenue": 25.50,
    "dailyBudget": 5.00,
    "activeJobsCount": 2,
    "completedJobsCount": 5
  },
  "styleGuides": [...],
  "characterBibles": [...],
  "hookFormulas": [...],
  "logs": [...]
}
```
Rules:
- All `metrics` properties are raw numeric types (`number`).
- No pre-formatted strings in `metrics`.
- Formatting (`K`, `M`, `$`, decimals, commas) is done on the frontend.
