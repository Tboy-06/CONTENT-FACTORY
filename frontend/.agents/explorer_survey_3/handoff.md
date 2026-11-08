# E2E & Integration Exploration Survey: VaultData Flow, Contract Specification & Test Infrastructure

**Agent**: `teamwork_preview_explorer` (`explorer_survey_3`)  
**Role**: E2E & Integration Exploration Specialist  
**Working Directory**: `C:\Users\User\antigravity\CONTENT-FACTORY\.agents\explorer_survey_3`  
**Workspace**: `C:\Users\User\antigravity\CONTENT-FACTORY`  
**Date**: 2026-09-05T23:15:00Z  
**Status**: Survey Complete

---

## Executive Summary

This investigation explores the end-to-end (E2E) integration boundary between the backend (FastAPI / SQLite repository / `server.ts`) and the React frontend UI (`App.tsx`, `BottomStatusBar.tsx`, `VaultExplorer.tsx`).

Key discoveries:
1. **Critical Endpoint Gap**: FastAPI (`dashboard/main.py`) **does not have a `GET /api/vault` endpoint**. The frontend (`src/App.tsx:24`) fetches `/api/vault` on mount. While `server.ts` provides an in-memory mock implementation of `/api/vault` (lines 891–910), it **omits `totalViews`** from `metrics`. The FastAPI backend must implement `GET /api/vault` returning live data aggregated from SQLite (`backend/vault/repository.py`).
2. **Type Contract Mismatch**: `VaultData.metrics` in `src/types.ts` defines 6 numeric properties (`totalSpent`, `totalTokens`, `totalRevenue`, `dailyBudget`, `activeJobsCount`, `completedJobsCount`), but lacks `totalViews`.
3. **Hardcoded Mock Values in UI**:
   - `BottomStatusBar.tsx` contains 4 distinct hardcoded mock values: `"12.4K"` views string (line 16), `1.20` spent fallback (line 14), `10.00` budget fallback (line 15), and `3` videos posted fallback (line 24). Furthermore, `completedJobsCount` is accepted as an external prop instead of being read from `vaultData.metrics.completedJobsCount`.
   - `Header.tsx` line 188 hardcodes `$10.00 / day` inside the Settings modal.
   - `PipelineBoard.tsx` line 158 hardcodes `$842.10` and `+12%` under Total Savings, and lines 594, 600, 606, 612 contain hardcoded fallbacks (`"148,200"` views, `76.4%` retention, `"2,840"` shares, `"$64.20"` revenue).
4. **Test Infrastructure Ready for Extension**: Backend test runner is `pytest` with `unittest.TestCase` in `tests/test_config.py`. Frontend uses `tsc --noEmit` via `npm run lint` and Vite/esbuild via `npm run build`. Automated verification can be achieved by adding a FastAPI TestClient suite (`tests/test_vault_api.py`) and running `tsc --noEmit`.

---

## 1. Observation

### 1.1 Original Authoritative Requirements (`.agents/ORIGINAL_REQUEST.md`)
- **Lines 11, 17–25, 28–33**:
  - **R1. Backend API Update**: Update FastAPI backend to calculate and return actual live metrics (`totalViews`, `completedJobsCount`, `dailyBudget`, `totalSpent`) in the `VaultData` payload.
  - **R2. Frontend Types Update**: Update `VaultData` interface in `src/types.ts` to include the new metric fields (e.g., `totalViews`, `completedJobsCount`).
  - **R3. UI Component Updates**: Scan frontend React components (specifically `BottomStatusBar.tsx`) for hardcoded placeholder strings (`"12.4K views"`, `$0.02 spent`, `3 videos posted`). Replace all hardcoded values with dynamic data from `vaultData` props.
  - **Acceptance Criteria**:
    - Backend API endpoint serving `VaultData` correctly fetches/calculates real metrics from database/APIs and includes them in JSON response.
    - `BottomStatusBar.tsx` accesses views, spent, and completed jobs exclusively through `vaultData.metrics`.
    - No hardcoded placeholder numbers remain in the status bar or primary dashboard components.

### 1.2 Frontend Consumption & State (`src/App.tsx`)
- **`src/App.tsx` (lines 15, 20–43)**:
  ```typescript
  15: const [vaultData, setVaultData] = useState<VaultData | null>(null);
  ...
  20: const fetchData = async () => {
  21:   try {
  22:     const [jobsRes, vaultRes] = await Promise.all([
  23:       fetch("/api/jobs"),
  24:       fetch("/api/vault")
  25:     ]);
  ...
  36:     if (vaultRes.ok) {
  37:       const vaultJson: VaultData = await vaultRes.json();
  38:       setVaultData(vaultJson);
  39:     }
  ```
- **`src/App.tsx` (lines 187–190)**:
  ```typescript
  187: <BottomStatusBar 
  188:   vaultData={vaultData}
  189:   completedJobsCount={jobs.filter(j => j.status === "COMPLETED").length}
  190: />
  ```
  *Observation*: `BottomStatusBar` receives `vaultData` but also receives `completedJobsCount` calculated from `jobs` array in `App.tsx`, rather than deriving it directly from `vaultData.metrics.completedJobsCount`.

### 1.3 `BottomStatusBar.tsx` Code Inspection (`src/components/BottomStatusBar.tsx`)
- **Lines 5–46**:
  ```typescript
  5: interface BottomStatusBarProps {
  6:   vaultData: VaultData | null;
  7:   completedJobsCount: number;
  8: }
  9: 
  10: export const BottomStatusBar: React.FC<BottomStatusBarProps> = ({
  11:   vaultData,
  12:   completedJobsCount
  13: }) => {
  14:   const spent = vaultData?.metrics.totalSpent ?? 1.20;
  15:   const budget = vaultData?.metrics.dailyBudget ?? 10.00;
  16:   const viewsCount = "12.4K";
  ...
  24:     Today: <strong className="text-slate-100 font-semibold">{completedJobsCount || 3} videos posted</strong>
  ...
  31:     <span className="text-slate-100 font-semibold">{viewsCount} views</span>
  ...
  38:     <strong className="text-emerald-400 font-bold">${spent.toFixed(2)}</strong> spent
  ...
  42:     Budget: <span className="text-slate-300">${budget.toFixed(2)}/day</span>
  ```
  *Verbatim Hardcoded Values*:
  1. `viewsCount = "12.4K"` (Literal string on line 16, rendered on line 31)
  2. `vaultData?.metrics.totalSpent ?? 1.20` (Mock fallback `1.20` on line 14)
  3. `vaultData?.metrics.dailyBudget ?? 10.00` (Mock fallback `10.00` on line 15)
  4. `{completedJobsCount || 3}` (Mock fallback `3` on line 24)
  5. `props.completedJobsCount` (Accepted via props instead of `vaultData.metrics.completedJobsCount`)

### 1.4 Frontend Type Definition (`src/types.ts`)
- **Lines 81–89**:
  ```typescript
  81: export interface VaultData {
  82:   metrics: {
  83:     totalSpent: number;
  84:     totalTokens: number;
  85:     totalRevenue: number;
  86:     dailyBudget: number;
  87:     activeJobsCount: number;
  88:     completedJobsCount: number;
  89:   };
  90:   styleGuides: Array<{ ... }>;
  91:   characterBibles: Array<{ ... }>;
  92:   hookFormulas: Array<{ ... }>;
  93:   logs: Array<{ ... }>;
  94: }
  ```
  *Observation*: `totalViews` is absent.

### 1.5 Dual Backend Architecture
The repository has two distinct server layers:

#### A. FastAPI Backend (`dashboard/main.py` + `run_backend.py`)
- Entry point: `run_backend.py` runs `dashboard.main:app` on port 8000.
- Database: SQLite / PostgreSQL via SQLAlchemy (`backend/vault/models.py`, `backend/vault/repository.py`).
- Existing endpoints in `dashboard/main.py`:
  - `GET /` (Jinja2 HTML)
  - `GET /health`
  - `GET /api/jobs`
  - `GET /api/jobs/{job_id}`
  - `GET /api/analytics/summary` (returns `total_jobs`, `total_spend_usd`, `total_tokens`, `total_revenue_usd`, `daily_budget_usd`, `budget_remaining`)
  - `GET /api/analytics/posts` (returns per-job analytics)
- **CRITICAL**: `GET /api/vault` does **NOT exist** in `dashboard/main.py`!

#### B. Express / Vite Dev Server (`server.ts`)
- Script: `npm run dev` executes `tsx server.ts` on port 3000.
- Serves Vite middleware for React SPA and provides mock REST endpoints backed by in-memory `jobsStore`.
- Lines 891–910 implement `GET /api/vault`:
  ```typescript
  891: app.get("/api/vault", (req, res) => {
  892:   const totalSpent = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.usd_estimate, 0), 0);
  893:   const totalTokens = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.tokens, 0), 0);
  894:   const totalRev = jobsStore.reduce((acc, j) => acc + (j.analytics?.revenue || 0), 0);
  895: 
  896:   res.json({
  897:     metrics: {
  898:       totalSpent: +totalSpent.toFixed(4),
  899:       totalTokens,
  900:       totalRevenue: +totalRev.toFixed(2),
  901:       dailyBudget: 5.0,
  902:       activeJobsCount: jobsStore.filter(j => j.status !== "COMPLETED").length,
  903:       completedJobsCount: jobsStore.filter(j => j.status === "COMPLETED").length
  904:     },
  905:     styleGuides: vaultExtras.styleGuides,
  906:     characterBibles: vaultExtras.characterBibles,
  907:     hookFormulas: vaultExtras.hookFormulas,
  908:     logs: vaultExtras.logs.slice(0, 30)
  909:   });
  910: });
  ```
  *Observation*: `server.ts` has `jobsStore[1].analytics.views = 184500`, but does not sum views into `metrics.totalViews`.

### 1.6 Database Schema & Repository Capabilities (`backend/vault/`)
- **`backend/vault/models.py`**:
  - `Job` (line 52): Columns `id`, `niche`, `status`, `current_stage`, `config`, `created_at`.
  - `Analytics` (line 85): Columns `id`, `job_id`, `views` (Integer), `likes`, `comments`, `shares`, `retention_rate`.
  - `Cost` (line 95): Columns `id`, `job_id`, `agent_name`, `tokens`, `usd_estimate`, `created_at`.
  - `RevenueStream` (line 122): Columns `id`, `job_id`, `amount`, `channel`.
  - `StyleGuide`, `CharacterBible`, `HookFormula`, `Log`.
- **`backend/vault/repository.py`**:
  - Currently has:
    - `Repository.get_total_costs() -> float` (line 151): `select(func.sum(Cost.usd_estimate))`
    - `Repository.get_total_tokens() -> int` (line 157): `select(func.sum(Cost.tokens))`
    - `Repository.get_total_revenue() -> float` (line 283): `select(func.sum(RevenueStream.amount))`
    - `Repository.get_jobs() -> List[Job]` (line 30)
    - `Repository.get_style_guides()`, `get_character_bibles()`, `get_hook_formulas()`, `get_logs(limit)`
  - Currently lacks:
    - `Repository.get_total_views() -> int` (`select(func.sum(Analytics.views))`)
    - `Repository.get_completed_jobs_count() -> int` (`select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)`)
    - `Repository.get_active_jobs_count() -> int` (`select(func.count(Job.id)).where(Job.status != JobStatus.COMPLETED)`)

### 1.7 Current Test Infrastructure
- **`package.json`**:
  - Scripts:
    - `"lint": "tsc --noEmit"` (TypeScript type check across codebase)
    - `"build": "vite build && esbuild server.ts ..."`
    - No frontend test runner (`vitest` or `jest` not present).
- **`requirements.txt`**:
  - Contains `pytest` and `pytest-asyncio`.
- **`tests/`**:
  - Contains only `tests/test_config.py` (32 lines, tests `Settings` defaults and `StageStatus`).
  - No existing integration tests for FastAPI endpoints or repository queries.

---

## 2. Logic Chain

### 2.1 End-to-End Data Flow Mapping

The data flow from storage to display is traced through 6 discrete stages:

```
[ SQLite Database / vault.db ]
         │  (SQLAlchemy async ORM: tables jobs, analytics, costs, revenue_streams)
         ▼
[ backend.vault.repository.Repository ]
         │  (Aggregations: get_total_views, get_total_costs, get_completed_jobs_count, etc.)
         ▼
[ FastAPI Router / dashboard.main: GET /api/vault ]  <─── OR ───> [ Node Express / server.ts: GET /api/vault ]
         │  (HTTP JSON Response with { metrics: { totalViews, totalSpent, ... }, styleGuides, ... })
         ▼
[ React Frontend / src/App.tsx: fetchData() ]
         │  (fetch('/api/vault') ──> setVaultData(vaultJson))
         ▼
[ Props Drilling / vaultData: VaultData ]
         │
    ┌────┴───────────────────────────┬──────────────────────────────┐
    ▼                                ▼                              ▼
[ BottomStatusBar.tsx ]      [ VaultExplorer.tsx ]            [ Header.tsx ]
• totalViews                 • totalSpent                     • dailyBudget
• completedJobsCount         • totalTokens
• totalSpent                 • totalRevenue
• dailyBudget                • activeJobsCount / completed
```

**Traceability Matrix**:
| Metric | Database Origin | Repository Method | API Payload Property | Frontend Interface (`VaultData.metrics`) | UI Consumer Element |
|---|---|---|---|---|---|
| Total Views | `analytics.views` | `get_total_views()` | `totalViews` | `totalViews: number` | `BottomStatusBar` center pill |
| Total Spent | `costs.usd_estimate` | `get_total_costs()` | `totalSpent` | `totalSpent: number` | `BottomStatusBar` right pill, `VaultExplorer` card 1 |
| Total Tokens | `costs.tokens` | `get_total_tokens()` | `totalTokens` | `totalTokens: number` | `VaultExplorer` card 2 |
| Total Revenue | `revenue_streams.amount`| `get_total_revenue()`| `totalRevenue` | `totalRevenue: number` | `VaultExplorer` card 3 |
| Daily Budget | `config.settings.daily_budget_usd` | Direct from settings | `dailyBudget` | `dailyBudget: number` | `BottomStatusBar` right pill, `Header` settings modal |
| Completed Jobs | `jobs.status == 'COMPLETED'` | `get_completed_jobs_count()` | `completedJobsCount` | `completedJobsCount: number` | `BottomStatusBar` left pill, `VaultExplorer` card 4 |
| Active Jobs | `jobs.status != 'COMPLETED'` | `get_active_jobs_count()` | `activeJobsCount` | `activeJobsCount: number` | `VaultExplorer` card 4 |

---

### 2.2 Exact Contract Specification: `vaultData.metrics`

To guarantee full interoperability between Python (FastAPI), TypeScript (`server.ts`), and React components, the contract must strictly govern:

#### Schema Definition (TypeScript & Pydantic)
```typescript
export interface VaultMetrics {
  totalViews: number;          // Total views across all platforms and jobs (integer >= 0)
  totalSpent: number;          // Total LLM API cost in USD (float >= 0.0, rounded to 4 decimals)
  totalTokens: number;         // Total tokens consumed by agents (integer >= 0)
  totalRevenue: number;        // Total creator revenue in USD (float >= 0.0, rounded to 2 decimals)
  dailyBudget: number;         // Configured daily budget in USD (float > 0.0, e.g. 5.0 or 10.0)
  activeJobsCount: number;     // Number of non-completed jobs (integer >= 0)
  completedJobsCount: number;  // Number of completed jobs (integer >= 0)
}
```

```python
class VaultMetricsSchema(BaseModel):
    totalViews: int = Field(..., ge=0, description="Total views across all platforms")
    totalSpent: float = Field(..., ge=0.0, description="Total API cost in USD")
    totalTokens: int = Field(..., ge=0.0, description="Total tokens consumed")
    totalRevenue: float = Field(..., ge=0.0, description="Total creator revenue in USD")
    dailyBudget: float = Field(..., gt=0.0, description="Daily budget limit in USD")
    activeJobsCount: int = Field(..., ge=0, description="Active pipeline jobs count")
    completedJobsCount: int = Field(..., ge=0, description="Completed pipeline jobs count")
```

#### Formatting Responsibilities
- **Rule**: All fields transmitted in JSON must be **raw numeric types** (`number` in JSON/TS, `int`/`float` in Python).
- **Rule**: String formatting (currency `$`, thousands commas `,`, compact suffixes `K`/`M`, decimals `.toFixed()`) is the **exclusive responsibility of the frontend presentation layer**.
- **Frontend Formatter Implementation**:
  ```typescript
  export const formatViews = (views: number): string => {
    if (views >= 1_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
    if (views >= 1_000) return `${(views / 1_000).toFixed(1)}K`;
    return views.toLocaleString();
  };
  ```
  - `184500` -> `"184.5K"`
  - `12400` -> `"12.4K"`
  - `350` -> `"350"`
  - `0` -> `"0"`

#### Nullability & Fallback Rules
- Backend: Guaranteed non-null numbers (defaults to `0` or `0.0`, `dailyBudget` defaults to `5.0`).
- Frontend Component Consumption: Defensive fallbacks should use `0` or `0.0`, never static mock values (e.g. `vaultData?.metrics.totalViews ?? 0`, `vaultData?.metrics.totalSpent ?? 0.0`).

---

### 2.3 Repository-Wide Mock & Hardcoded Metrics Audit

Every occurrence of hardcoded or mock metric numbers identified across the repository is cataloged below:

| File Path | Line Number(s) | Verbatim Code / String | Problem Description | Proposed Dynamic Replacement |
|---|---|---|---|---|
| `src/components/BottomStatusBar.tsx` | 16 | `const viewsCount = "12.4K";` | Hardcoded mock views string | `const views = vaultData?.metrics.totalViews ?? 0; const viewsCount = formatViews(views);` |
| `src/components/BottomStatusBar.tsx` | 14 | `vaultData?.metrics.totalSpent ?? 1.20;` | Hardcoded fallback `1.20` | `vaultData?.metrics.totalSpent ?? 0.0;` |
| `src/components/BottomStatusBar.tsx` | 15 | `vaultData?.metrics.dailyBudget ?? 10.00;` | Hardcoded fallback `10.00` | `vaultData?.metrics.dailyBudget ?? 5.00;` (or `0.00`) |
| `src/components/BottomStatusBar.tsx` | 24 | `{completedJobsCount \|\| 3} videos posted` | Hardcoded fallback `3` and prop usage | `{completedCount} videos posted` where `completedCount = vaultData?.metrics.completedJobsCount ?? 0;` |
| `src/components/BottomStatusBar.tsx` | 5–12 | `interface BottomStatusBarProps { vaultData, completedJobsCount }` | Violates AC: completed jobs must be read from `vaultData.metrics` | Remove `completedJobsCount` from `BottomStatusBarProps`; read directly from `vaultData?.metrics.completedJobsCount`. |
| `src/App.tsx` | 188–190 | `<BottomStatusBar vaultData={vaultData} completedJobsCount={...} />` | Unnecessary prop pass | `<BottomStatusBar vaultData={vaultData} />` |
| `src/components/Header.tsx` | 188 | `<span className="font-mono text-emerald-400 font-bold">$10.00 / day</span>` | Hardcoded modal budget string | `${vaultData?.metrics.dailyBudget ? `$${vaultData.metrics.dailyBudget.toFixed(2)} / day` : "$5.00 / day"}` |
| `src/components/PipelineBoard.tsx` | 158 | `<p className="text-2xl font-bold font-mono text-emerald-400">$842.10</p>` | Hardcoded Total Savings mock metric | Make dynamic or link to `vaultData.metrics.totalRevenue` / `totalSpent` savings. |
| `src/components/PipelineBoard.tsx` | 162 | `+12%` | Hardcoded percentage badge | Calculate or render dynamically. |
| `src/components/PipelineBoard.tsx` | 594 | `{selectedJob.analytics?.views.toLocaleString() \|\| "148,200"}` | Hardcoded fallback `"148,200"` | `{selectedJob.analytics?.views ? selectedJob.analytics.views.toLocaleString() : "0"}` |
| `src/components/PipelineBoard.tsx` | 600 | `{selectedJob.analytics?.retention_rate \|\| 76.4}%` | Hardcoded fallback `76.4` | `{selectedJob.analytics?.retention_rate ?? 0}%` |
| `src/components/PipelineBoard.tsx` | 606 | `{selectedJob.analytics?.shares.toLocaleString() \|\| "2,840"}` | Hardcoded fallback `"2,840"` | `{selectedJob.analytics?.shares ? selectedJob.analytics.shares.toLocaleString() : "0"}` |
| `src/components/PipelineBoard.tsx` | 612 | `${selectedJob.analytics?.revenue.toFixed(2) \|\| "64.20"}` | Hardcoded fallback `"64.20"` | `${selectedJob.analytics?.revenue ? selectedJob.analytics.revenue.toFixed(2) : "0.00"}` |
| `server.ts` | 901 | `dailyBudget: 5.0` | Fixed value in mock dev server | Sourced from `process.env.DAILY_BUDGET_USD` or keep aligned with `Settings.daily_budget_usd`. |
| `server.ts` | 891–904 | `totalViews` omitted from `res.json({ metrics: ... })` | Missing metric in dev server | Compute `totalViews = jobsStore.reduce((acc, j) => acc + (j.analytics?.views \|\| 0), 0)` and return in `metrics`. |

---

### 2.4 Test Infrastructure Assessment & Acceptance Verification Strategy

#### A. Current Infrastructure Overview
1. **Backend**:
   - Packages installed: `pytest`, `pytest-asyncio`, `httpx`, `fastapi`, `sqlalchemy`.
   - Existing suite: `tests/test_config.py` (executable with `pytest` or `python -m unittest discover tests`).
   - Missing: API route tests, repository aggregation tests.
2. **Frontend**:
   - `npm run lint` -> `tsc --noEmit` verifies strict TypeScript compilation and ensures property name mismatches fail build immediately.
   - `npm run build` -> `vite build && esbuild server.ts ...` verifies asset bundling and production build.
   - Missing: Automated component testing library (e.g. Vitest / React Testing Library).

#### B. Automated Acceptance Verification Plan
To verify the acceptance criteria with 100% automated confidence:

1. **Backend Automated Tests (`tests/test_vault_api.py`)**:
   Create an integration test using `httpx.AsyncClient` against the FastAPI app:
   ```python
   import pytest
   from httpx import AsyncClient, ASGITransport
   from dashboard.main import app
   from backend.vault.repository import Repository, init_db
   from backend.vault.models import JobStatus

   @pytest.mark.asyncio
   async def test_vault_endpoint_contract():
       await init_db()
       async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
           res = await ac.get("/api/vault")
       assert res.status_code == 200
       data = res.json()
       assert "metrics" in data
       m = data["metrics"]
       assert isinstance(m["totalViews"], int)
       assert isinstance(m["totalSpent"], (int, float))
       assert isinstance(m["totalTokens"], int)
       assert isinstance(m["totalRevenue"], (int, float))
       assert isinstance(m["dailyBudget"], (int, float))
       assert isinstance(m["activeJobsCount"], int)
       assert isinstance(m["completedJobsCount"], int)
   ```

2. **Frontend Automated Verification**:
   - **Step 1: Type Checking**:
     Run `npm run lint` (`tsc --noEmit`). If `BottomStatusBar.tsx` references a non-existent field or if `types.ts` is mismatched, `tsc` will fail.
   - **Step 2: No Hardcoded Placeholder Static Assertion**:
     Run a test script (or automated regex/AST check) verifying:
     - `BottomStatusBar.tsx` does NOT contain `"12.4K"`
     - `BottomStatusBar.tsx` does NOT contain `?? 1.20`
     - `BottomStatusBar.tsx` does NOT contain `?? 10.00`
     - `BottomStatusBar.tsx` does NOT contain `|| 3`
     - `BottomStatusBar.tsx` does NOT contain `completedJobsCount` in its props interface.
   - **Step 3: Full Build**:
     Run `npm run build` to ensure clean bundle production.

---

### 2.5 Synthesis of Explorer Surveys

#### Catalog Inputs
- **`explorer_survey_1` (Backend Specialist)**:
  - Confirmed absence of `GET /api/vault` in FastAPI (`dashboard/main.py`).
  - Identified missing aggregations in `backend/vault/repository.py` (`get_total_views`, job counts).
  - Drafted concrete implementation for `Repository` and `dashboard/main.py`.
- **`explorer_survey_2` (Frontend Specialist)**:
  - Audited `src/types.ts` and identified absence of `totalViews`.
  - Detailed the 4 hardcoded occurrences in `BottomStatusBar.tsx`.
  - Cataloged additional hardcoded UI metrics in `Header.tsx` and `PipelineBoard.tsx`.
- **`explorer_survey_3` (E2E & Integration Specialist - This Report)**:
  - Reconciled dual-server topology (`dashboard/main.py` vs `server.ts`).
  - Formalized exact contract specification for `vaultData.metrics`.
  - Audited and unified testing infrastructure for end-to-end acceptance validation.

#### Consensus
- **100% Agreement**: `GET /api/vault` must be created in FastAPI with real database aggregations.
- **100% Agreement**: `VaultData.metrics` in `src/types.ts` must include `totalViews: number`.
- **100% Agreement**: `BottomStatusBar.tsx` must drop `completedJobsCount` from its props and access `totalViews`, `completedJobsCount`, `totalSpent`, and `dailyBudget` exclusively through `vaultData.metrics`.
- **100% Agreement**: All hardcoded fallback numbers (`12.4K`, `1.20`, `10.00`, `3`) must be eliminated.

#### Resolved Conflicts / Clarifications
- **Dual Server Role Clarification**:
  - `server.ts` is the development Vite Express server (`npm run dev`).
  - `run_backend.py` / `dashboard/main.py` is the production FastAPI server (`python run_backend.py`).
  - *Resolution*: Both `dashboard/main.py` AND `server.ts` must satisfy the exact same `vaultData.metrics` contract so that both local Vite dev (`npm run dev`) and FastAPI standalone execution (`run_backend.py`) return consistent live data.

#### Dissenting Views
- None. All three surveys have converged on the identical root causes and required fixes.

#### Gaps Addressed
- Prior surveys did not evaluate how `Header.tsx` and `PipelineBoard.tsx` handle missing analytics or budget displays; this survey has inventoried them and provided dynamic replacement patterns.

---

## 3. Caveats

1. **Dual Server Environments**: The frontend in development is proxied through `server.ts` on port 3000. If an implementer updates only FastAPI (`dashboard/main.py`) without updating `server.ts`, running `npm run dev` will continue to show incomplete metrics. Both must be updated in sync.
2. **Database Seed Data**: In a fresh database with zero jobs and zero analytics rows, `select(func.sum(Analytics.views))` evaluates to `None` in SQLAlchemy. The repository method must handle `None` and safely return `0` / `0.0`.
3. **External Platform Views Synchronization**: Real-time external platform views (YouTube Data API, TikTok, Instagram) are fetched during the `ANALYZE` stage and written to the `analytics` table. Total views in `vaultData.metrics` is the aggregation of all recorded views across all jobs in the database. If no jobs have run `ANALYZE`, `totalViews` is legitimately `0`.
4. **Permissions Boundary**: This exploration was strictly read-only; no application source code was modified.

---

## 4. Conclusion & Actionable Implementation Blueprint

The findings provide a clear, low-risk, deterministic implementation blueprint for the development team:

### Step 1: Backend Database Repository (`backend/vault/repository.py`)
Add three async aggregation methods to `Repository`:
```python
@staticmethod
async def get_total_views() -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.sum(Analytics.views)))
        return res.scalar() or 0

@staticmethod
async def get_completed_jobs_count() -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED))
        return res.scalar() or 0

@staticmethod
async def get_active_jobs_count() -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.count(Job.id)).where(Job.status != JobStatus.COMPLETED))
        return res.scalar() or 0
```

### Step 2: FastAPI Endpoint (`dashboard/main.py`)
Implement `GET /api/vault`:
```python
@app.get("/api/vault")
async def api_vault():
    total_spent = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    total_rev = await Repository.get_total_revenue()
    total_views = await Repository.get_total_views()
    completed_jobs = await Repository.get_completed_jobs_count()
    active_jobs = await Repository.get_active_jobs_count()
    
    style_guides = await Repository.get_style_guides()
    character_bibles = await Repository.get_character_bibles()
    hook_formulas = await Repository.get_hook_formulas()
    logs = await Repository.get_logs(limit=30)
    
    return {
        "metrics": {
            "totalViews": total_views,
            "totalSpent": round(total_spent, 4),
            "totalTokens": total_tokens,
            "totalRevenue": round(total_rev, 2),
            "dailyBudget": settings.daily_budget_usd,
            "activeJobsCount": active_jobs,
            "completedJobsCount": completed_jobs
        },
        "styleGuides": [sg.data for sg in style_guides] if style_guides else [],
        "characterBibles": [cb.data for cb in character_bibles] if character_bibles else [],
        "hookFormulas": [{"formula": hf.formula, "score": hf.virality_score, "count": 1} for hf in hook_formulas] if hook_formulas else [],
        "logs": [{"id": l.id, "time": l.created_at.strftime("%H:%M:%S") if l.created_at else "", "message": l.message} for l in logs] if logs else []
    }
```

### Step 3: Node Dev Server (`server.ts`)
Update `GET /api/vault` (lines 891–910):
- Calculate: `const totalViews = jobsStore.reduce((acc, j) => acc + (j.analytics?.views || 0), 0);`
- Include `totalViews` in `metrics` object.

### Step 4: Frontend Types (`src/types.ts`)
Update `VaultData`:
```typescript
export interface VaultData {
  metrics: {
    totalViews: number;
    totalSpent: number;
    totalTokens: number;
    totalRevenue: number;
    dailyBudget: number;
    activeJobsCount: number;
    completedJobsCount: number;
  };
  ...
}
```

### Step 5: Frontend Status Bar (`src/components/BottomStatusBar.tsx`)
```typescript
interface BottomStatusBarProps {
  vaultData: VaultData | null;
}

export const BottomStatusBar: React.FC<BottomStatusBarProps> = ({ vaultData }) => {
  const completedJobsCount = vaultData?.metrics.completedJobsCount ?? 0;
  const totalViews = vaultData?.metrics.totalViews ?? 0;
  const spent = vaultData?.metrics.totalSpent ?? 0.0;
  const budget = vaultData?.metrics.dailyBudget ?? 0.0;

  const formatViews = (v: number): string => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
    return v.toLocaleString();
  };

  return (
    <footer className="h-9 bg-[#070b14] border-t border-[#192437] px-4 sm:px-6 flex items-center justify-between text-xs font-mono text-slate-400 select-none shrink-0 z-30">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
        <span>
          Today: <strong className="text-slate-100 font-semibold">{completedJobsCount} videos posted</strong>
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Eye className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-slate-100 font-semibold">{formatViews(totalViews)} views</span>
      </div>

      <div className="flex items-center gap-1.5 text-slate-300">
        <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
        <span>
          <strong className="text-emerald-400 font-bold">${spent.toFixed(2)}</strong> spent
        </span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-400">
          Budget: <span className="text-slate-300">${budget.toFixed(2)}/day</span>
        </span>
      </div>
    </footer>
  );
};
```

### Step 6: App Component (`src/App.tsx`)
Update line 187:
```typescript
<BottomStatusBar vaultData={vaultData} />
```

---

## 5. Verification Method

### 5.1 Independent Verification Commands

1. **Backend Integration Verification**:
   - Run tests command:
     `pytest tests/`
   - With new `tests/test_vault_api.py`, verify that `GET /api/vault` returns HTTP 200, contains valid numeric metrics matching the database, and meets the contract schema.
2. **Frontend Type-Check**:
   - Run:
     `npm run lint` (executes `tsc --noEmit`)
   - Must output zero errors.
3. **Frontend Production Build**:
   - Run:
     `npm run build`
   - Must successfully build `dist/` with zero bundle errors.
4. **Code Inspection / Anti-Regression Check**:
   - Inspect `src/components/BottomStatusBar.tsx`:
     - Must NOT match `"12.4K"`
     - Must NOT match `1.20`
     - Must NOT match `10.00`
     - Must NOT match `|| 3`
     - Must NOT accept `completedJobsCount` as a prop.

### 5.2 Invalidation Conditions
The conclusion is invalidated if:
- `FastAPI` requires authentication on `/api/vault` that the frontend does not send.
- The database schema does not allow views aggregation via `func.sum(Analytics.views)`.
- A frontend component requires pre-formatted string metric types in `VaultData.metrics` rather than numeric types.
