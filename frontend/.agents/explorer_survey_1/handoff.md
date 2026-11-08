# Backend Exploration Survey: Live Metrics & VaultData Architecture

## 1. Observation

### 1.1 Original Authoritative Request (`.agents/ORIGINAL_REQUEST.md`)
- **Lines 11, 17-25, 28-33**:
  > "Remove all hardcoded mock data (such as views, completed jobs, and budget) from the React frontend UI and update the backend to supply this live data in the VaultData payload."
  > "R1. Backend API Update: Update the FastAPI backend to calculate and return actual live metrics (such as total views across platforms, total jobs completed, real daily budget, and total spent) instead of static or missing fields. Ensure these are included in the `VaultData` payload sent to the frontend."
  > "R2. Frontend Types Update: Update the `VaultData` interface in `...src/types.ts` to include the new metric fields (e.g., `totalViews`, `completedJobsCount`, etc.) provided by the backend."
  > "R3. UI Component Updates: Scan the frontend React components (specifically `BottomStatusBar.tsx` and any other layout components) for hardcoded placeholder strings (like `'12.4K views'`, `$0.02 spent`, `3 videos posted`). Replace all hardcoded values with dynamic data from the `vaultData` props."
  > "Backend Validation: The backend API endpoint that serves VaultData correctly fetches or calculates real metrics from the database or external APIs (where applicable) and includes them in the JSON response."
  > "Frontend Validation: `BottomStatusBar.tsx` accesses views, spent, and completed jobs exclusively through `vaultData.metrics`."

### 1.2 FastAPI Backend Routing & Lifespan (`dashboard/main.py` & `run_backend.py`)
- **`run_backend.py` (lines 15-20, 67-73)**:
  - Imports `fastapi_app` from `dashboard.main`.
  - Runs database initialization (`init_db()`), APScheduler (`scheduler.start()`), and Telegram Bot (`bot_app.start()`).
  - Listens on `http://0.0.0.0:8000` via `uvicorn.run("run_backend:fastapi_app", host=host, port=port)`.
- **`dashboard/main.py` (lines 8-9, 70-134)**:
  - `app = FastAPI(title="CONTENT-FACTORY Dashboard", version="1.0.0")`
  - Routes defined:
    - `GET /` (line 11): SSR Jinja2 overview.
    - `GET /job/{job_id}` (line 24): SSR Jinja2 job detail.
    - `GET /analytics` (line 42): SSR Jinja2 analytics view.
    - `GET /style-guides` (line 54): SSR Jinja2 style guides.
    - `GET /health` (line 66): `{"status": "ok", "service": "CONTENT-FACTORY", "version": "1.0.0"}`.
    - `GET /api/jobs` (line 70): returns list of jobs.
    - `GET /api/jobs/{job_id}` (line 82): returns job detail with stages, assets, costs.
    - `GET /api/analytics/summary` (line 101):
      ```python
      @app.get("/api/analytics/summary")
      async def api_analytics_summary():
          total_costs = await Repository.get_total_costs()
          total_tokens = await Repository.get_total_tokens()
          total_rev = await Repository.get_total_revenue()
          jobs = await Repository.get_jobs()
          return {
              "total_jobs": len(jobs),
              "total_spend_usd": round(total_costs, 4),
              "total_tokens": total_tokens,
              "total_revenue_usd": round(total_rev, 2),
              "daily_budget_usd": settings.daily_budget_usd,
              "budget_remaining": max(0.0, round(settings.daily_budget_usd - total_costs, 4))
          }
      ```
    - `GET /api/analytics/posts` (line 116): returns per-job posts analytics list.
  - **Critical Absence**: There is **NO `GET /api/vault`** endpoint in FastAPI (`dashboard/main.py`). There are no Pydantic schema definitions for `VaultData` or `VaultMetrics`.

### 1.3 Database Models & ORM (`backend/vault/models.py`)
- **`backend/vault/models.py`**:
  - `Job` (lines 52-59): Table `jobs`. Columns `id` (int PK), `niche` (String 255), `status` (Enum JobStatus: `PENDING`, `IN_PROGRESS`, `AWAITING_APPROVAL`, `AWAITING_PREMIUM`, `COMPLETED`, `FAILED`), `current_stage` (Enum StageStatus: `IDEA` through `ANALYZE`), `config` (JSON), `created_at` (DateTime).
  - `Analytics` (lines 85-94): Table `analytics`. Columns:
    - `id`: int PK
    - `job_id`: int FK (`jobs.id`)
    - `views`: int (default 0)
    - `likes`: int (default 0)
    - `comments`: int (default 0)
    - `shares`: int (default 0)
    - `retention_rate`: float (default 0.0)
  - `Cost` (lines 95-103): Table `costs`. Columns `id` (PK), `job_id` (FK), `agent_name` (String 100), `tokens` (int), `usd_estimate` (float), `created_at` (DateTime).
  - `RevenueStream` (lines 122-128): Table `revenue_streams`. Columns `id` (PK), `job_id` (FK nullable), `amount` (float), `channel` (String 100, default "TikTok Creator Rewards").
  - `StyleGuide` (lines 104-109): Table `style_guides`. Columns `id` (PK), `niche` (String 255), `data` (JSON).
  - `CharacterBible` (lines 110-115): Table `character_bibles`. Columns `id` (PK), `niche` (String 255), `data` (JSON).
  - `HookFormula` (lines 116-121): Table `hook_formulas`. Columns `id` (PK), `formula` (String 512), `virality_score` (float).
  - `Log` (lines 141-147): Table `logs`. Columns `id` (PK), `job_id` (FK nullable), `message` (Text), `created_at` (DateTime).

### 1.4 Database Repository Layer (`backend/vault/repository.py`)
- Existing methods in `Repository`:
  - `get_jobs()` (line 30): Returns all jobs ordered by `id.desc()`.
  - `get_total_costs() -> float` (lines 150-155): Executes `select(func.sum(Cost.usd_estimate))`. Returns float or `0.0`.
  - `get_total_tokens() -> int` (lines 156-161): Executes `select(func.sum(Cost.tokens))`. Returns int or `0`.
  - `get_total_revenue() -> float` (lines 282-287): Executes `select(func.sum(RevenueStream.amount))`. Returns float or `0.0`.
  - `record_analytics(...)` (lines 175-183): Inserts `Analytics` row with `views`, `likes`, `comments`, `shares`, `retention_rate`.
  - `get_analytics_by_job(job_id)` (lines 184-189): Returns analytics rows for a specific job.
  - `get_style_guides()` (lines 216-220), `get_character_bibles()` (lines 244-249), `get_hook_formulas()` (lines 266-271), `get_logs(limit)` (lines 329-334).
- **Missing Repository Methods**:
  - No method to query total views: e.g. `get_total_views() -> int`.
  - No method to query completed jobs count: e.g. `get_completed_jobs_count() -> int`.
  - No method to query active jobs count: e.g. `get_active_jobs_count() -> int`.

### 1.5 Configuration & Budget Settings (`backend/config.py`)
- `Settings` class (lines 14-68):
  - `daily_budget_usd: float = 5.0` (read from `os.getenv("DAILY_BUDGET_USD", 5.0)`).
  - `database_url: str = "sqlite+aiosqlite:///./vault.db"` (read from `DATABASE_URL`).
  - `postiz_url: str = "http://localhost:3000"`.
  - `postiz_api_key: str = ""`.
  - `youtube_api_key: str = ""`.

### 1.6 Node Development Server & Existing Endpoint (`server.ts`)
- **`server.ts` (lines 79-204, 891-910)**:
  - Serves frontend on port 3000 with Vite middleware (`app.use(vite.middlewares)`).
  - Preloaded `jobsStore`: Job 101 (`AWAITING_APPROVAL`) and Job 102 (`COMPLETED`, with `analytics: { views: 184500, likes: 21800, ... }`).
  - Lines 891-910 implement `app.get("/api/vault")`:
    ```typescript
    app.get("/api/vault", (req, res) => {
      const totalSpent = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.usd_estimate, 0), 0);
      const totalTokens = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.tokens, 0), 0);
      const totalRev = jobsStore.reduce((acc, j) => acc + (j.analytics?.revenue || 0), 0);

      res.json({
        metrics: {
          totalSpent: +totalSpent.toFixed(4),
          totalTokens,
          totalRevenue: +totalRev.toFixed(2),
          dailyBudget: 5.0,
          activeJobsCount: jobsStore.filter(j => j.status !== "COMPLETED").length,
          completedJobsCount: jobsStore.filter(j => j.status === "COMPLETED").length
        },
        styleGuides: vaultExtras.styleGuides,
        characterBibles: vaultExtras.characterBibles,
        hookFormulas: vaultExtras.hookFormulas,
        logs: vaultExtras.logs.slice(0, 30)
      });
    });
    ```
  - **Critical Omission in `server.ts`**: `totalViews` is NOT calculated and NOT included in the `metrics` object!

### 1.7 Frontend Types & UI Components (`src/types.ts` & `src/components/BottomStatusBar.tsx`)
- **`src/types.ts` (lines 81-115)**:
  ```typescript
  export interface VaultData {
    metrics: {
      totalSpent: number;
      totalTokens: number;
      totalRevenue: number;
      dailyBudget: number;
      activeJobsCount: number;
      completedJobsCount: number;
      // NOTE: totalViews is completely missing!
    };
    styleGuides: Array<{ ... }>;
    characterBibles: Array<{ ... }>;
    hookFormulas: Array<{ ... }>;
    logs: Array<{ ... }>;
  }
  ```
- **`src/components/BottomStatusBar.tsx` (lines 10-47)**:
  - Line 14: `const spent = vaultData?.metrics.totalSpent ?? 1.20;` (hardcoded mock fallback `1.20`)
  - Line 15: `const budget = vaultData?.metrics.dailyBudget ?? 10.00;` (hardcoded mock fallback `10.00`)
  - Line 16: `const viewsCount = "12.4K";` (HARDCODED MOCK STRING)
  - Line 24: `{completedJobsCount || 3} videos posted` (hardcoded mock fallback `3`)
  - Line 31: `<span className="text-slate-100 font-semibold">{viewsCount} views</span>`
  - Line 38: `<strong className="text-emerald-400 font-bold">${spent.toFixed(2)}</strong> spent`
  - Line 42: `<span className="text-slate-300">${budget.toFixed(2)}/day</span>`

### 1.8 Testing Configuration & Existing Tests
- **`requirements.txt` (lines 16-17)**: Includes `pytest` and `pytest-asyncio`.
- **`tests/test_config.py` (lines 1-32)**:
  - Standard `unittest.TestCase` suite testing `Settings` attributes (`telegram_allowed_users_raw`, `daily_budget_usd`, `database_url`, `gemini_model`) and `StageStatus` count.
  - No tests currently exist for:
    - FastAPI endpoints (`GET /api/vault`, `GET /api/analytics/summary`).
    - Database queries in `Repository`.
    - Live metrics calculation logic.

---

## 2. Logic Chain

1. **Requirement Mapping**:
   - The user request and `ORIGINAL_REQUEST.md` (R1) require updating the FastAPI backend to calculate and return actual live metrics (total views across platforms, completed jobs count, active jobs count, real daily budget, and total spent) in the `VaultData` payload sent to the frontend.
   - Frontend `App.tsx` (line 24) issues `fetch("/api/vault")`.
   - In `server.ts` (the Node server running `npm run dev`), `app.get("/api/vault")` returns `{ metrics, styleGuides, characterBibles, hookFormulas, logs }`.
   - However, in the Python FastAPI backend (`dashboard/main.py`), the endpoint `/api/vault` is entirely absent; only `/api/analytics/summary` exists.

2. **Metrics Gap Identification**:
   - Neither backend (FastAPI nor `server.ts`) currently calculates `totalViews` for the `VaultData.metrics` payload.
   - Because `totalViews` was omitted from the API response and the `VaultData.metrics` type definition in `src/types.ts`, `BottomStatusBar.tsx` (line 16) used `const viewsCount = "12.4K"` and hardcoded fallbacks (`1.20`, `10.00`, `3`).

3. **Authentic Metric Derivation from the Database**:
   - **Total Views**: In `backend/vault/models.py`, `Analytics.views` stores view counts recorded by `AnalystAgent` or post-distribution ingestion (`PostizClient.get_post_analytics`). The authentic total views metric is the SQL aggregate:
     `SELECT COALESCE(SUM(views), 0) FROM analytics;`
   - **Completed Jobs Count**: In `Job.status`, completed jobs are flagged with `JobStatus.COMPLETED`. The authentic count is:
     `SELECT COUNT(id) FROM jobs WHERE status = 'COMPLETED';`
   - **Active Jobs Count**:
     `SELECT COUNT(id) FROM jobs WHERE status != 'COMPLETED';`
   - **Total Spent (USD)**: In `Cost.usd_estimate`, all agent LLM and rendering invocations are tracked. `Repository.get_total_costs()` computes `SUM(usd_estimate)`.
   - **Total Tokens**: `Repository.get_total_tokens()` computes `SUM(tokens)`.
   - **Total Revenue (USD)**: `Repository.get_total_revenue()` computes `SUM(amount)` from `RevenueStream`.
   - **Daily Budget**: `settings.daily_budget_usd` from `backend.config` (default `$5.00`, configurable via `DAILY_BUDGET_USD`).

4. **Synchronous Contract Parity**:
   - To ensure complete end-to-end functionality regardless of whether the system runs via `run_backend.py` (FastAPI) or `server.ts` (Node development server):
     1. FastAPI (`dashboard/main.py`) must implement `GET /api/vault` returning the full `VaultData` contract with Pydantic schemas.
     2. `backend/vault/repository.py` must provide `get_total_views()`, `get_completed_jobs_count()`, and `get_active_jobs_count()`.
     3. `server.ts` (lines 891-910) must calculate `totalViews` from `jobsStore` and include it in `res.json({ metrics: { ..., totalViews } })`.
     4. `src/types.ts` must update `VaultData.metrics` to include `totalViews: number`.
     5. `BottomStatusBar.tsx` must consume `vaultData.metrics.totalViews`, `vaultData.metrics.completedJobsCount`, `vaultData.metrics.totalSpent`, and `vaultData.metrics.dailyBudget` without any hardcoded strings.

---

## 3. Caveats

1. **Dual Server Environments**: The project contains two server implementations:
   - Python FastAPI (`dashboard/main.py` executed by `run_backend.py` on port 8000).
   - Node/TypeScript Express (`server.ts` executed by `npm run dev` on port 3000).
   Both must adhere to the exact same JSON schema for `/api/vault` so neither environment produces regressions.
2. **Social Channel Views Attribution**: Views in the `analytics` table currently reflect aggregated impressions across platforms (TikTok, YouTube Shorts, IG Reels) associated with each job ID. Platform-specific breakdown (`platforms: ["TikTok", "YouTube Shorts"]`) is stored inside `Job.config`. If per-platform views breakdown is desired in the future, a `platform` column can be added to `Analytics`. For the current requirement, `totalViews` as the aggregate across platforms satisfies R1 and Acceptance Criteria.
3. **Empty Database State**: When the SQLite database (`vault.db`) is freshly created and no jobs have finished the `ANALYZE` stage, `totalViews` evaluates to `0`. The frontend must cleanly handle `0` without falling back to mock numbers like `12.4K`.

---

## 4. Conclusion & Proposed Implementation Details

### 4.1 Changes to `backend/vault/repository.py`
Add three new static aggregation methods to `Repository`:
```python
@staticmethod
async def get_total_views() -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.coalesce(func.sum(Analytics.views), 0)))
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

### 4.2 Changes to `dashboard/main.py` (FastAPI)
1. Define Pydantic response models for `/api/vault`:
```python
from pydantic import BaseModel
from typing import List, Dict, Any

class VaultMetrics(BaseModel):
    totalSpent: float
    totalTokens: int
    totalRevenue: float
    dailyBudget: float
    activeJobsCount: int
    completedJobsCount: int
    totalViews: int

class StyleGuideSchema(BaseModel):
    niche: str
    archetype: str
    primaryColor: str
    accentColor: str
    typography: str
    cutFrequency: str
    music: str

class CharacterBibleSchema(BaseModel):
    niche: str
    characterName: str
    persona: str
    visualDescription: str

class HookFormulaSchema(BaseModel):
    formula: str
    score: float
    count: int

class LogSchema(BaseModel):
    id: int
    time: str
    message: str

class VaultDataResponse(BaseModel):
    metrics: VaultMetrics
    styleGuides: List[StyleGuideSchema]
    characterBibles: List[CharacterBibleSchema]
    hookFormulas: List[HookFormulaSchema]
    logs: List[LogSchema]
```

2. Implement `GET /api/vault` in `dashboard/main.py`:
```python
@app.get("/api/vault", response_model=VaultDataResponse)
async def api_vault():
    total_spent = await Repository.get_total_costs()
    total_tokens = await Repository.get_total_tokens()
    total_revenue = await Repository.get_total_revenue()
    total_views = await Repository.get_total_views()
    completed_jobs = await Repository.get_completed_jobs_count()
    active_jobs = await Repository.get_active_jobs_count()

    style_guides_raw = await Repository.get_style_guides()
    character_bibles_raw = await Repository.get_character_bibles()
    hook_formulas_raw = await Repository.get_hook_formulas()
    logs_raw = await Repository.get_logs(limit=30)

    # Format models according to schema
    formatted_styles = [
        StyleGuideSchema(
            niche=sg.niche,
            archetype=sg.data.get("visual_archetype", "Cinematic Tech Noir"),
            primaryColor=sg.data.get("primary_color", "#0F172A"),
            accentColor=sg.data.get("accent_neon", "#38BDF8"),
            typography=sg.data.get("font_family", "Syne / Montserrat Bold"),
            cutFrequency=sg.data.get("cut_frequency", "Every 1.8s"),
            music=sg.data.get("bg_music_genre", "Tension Synth")
        ) for sg in style_guides_raw
    ]

    formatted_bibles = [
        CharacterBibleSchema(
            niche=cb.niche,
            characterName=cb.data.get("narrator_persona", cb.data.get("characterName", "The Architect")),
            persona=cb.data.get("tone", cb.data.get("persona", "High-signal authoritative")),
            visualDescription=cb.data.get("costume_style", cb.data.get("visualDescription", "Dark techwear"))
        ) for cb in character_bibles_raw
    ]

    formatted_hooks = [
        HookFormulaSchema(
            formula=hf.formula,
            score=round(hf.virality_score, 1),
            count=1
        ) for hf in hook_formulas_raw
    ]

    formatted_logs = [
        LogSchema(
            id=log.id,
            time=log.created_at.strftime("%H:%M:%S") if hasattr(log, "created_at") and log.created_at else "Now",
            message=log.message
        ) for log in logs_raw
    ]

    return VaultDataResponse(
        metrics=VaultMetrics(
            totalSpent=round(total_spent, 4),
            totalTokens=total_tokens,
            totalRevenue=round(total_revenue, 2),
            dailyBudget=settings.daily_budget_usd,
            activeJobsCount=active_jobs,
            completedJobsCount=completed_jobs,
            totalViews=total_views
        ),
        styleGuides=formatted_styles,
        characterBibles=formatted_bibles,
        hookFormulas=formatted_hooks,
        logs=formatted_logs
    )
```

3. Update `GET /api/analytics/summary` in `dashboard/main.py` (lines 101-114) to also include `total_views`, `completed_jobs`, and `active_jobs`.

### 4.3 Changes to `server.ts` (Node Dev Server)
In `server.ts` lines 891-910:
```typescript
  // Vault data endpoint
  app.get("/api/vault", (req, res) => {
    const totalSpent = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.usd_estimate, 0), 0);
    const totalTokens = jobsStore.reduce((acc, j) => acc + j.costs.reduce((cAcc, c) => cAcc + c.tokens, 0), 0);
    const totalRev = jobsStore.reduce((acc, j) => acc + (j.analytics?.revenue || 0), 0);
    const totalViews = jobsStore.reduce((acc, j) => acc + (j.analytics?.views || 0), 0);

    res.json({
      metrics: {
        totalSpent: +totalSpent.toFixed(4),
        totalTokens,
        totalRevenue: +totalRev.toFixed(2),
        dailyBudget: 5.0,
        activeJobsCount: jobsStore.filter(j => j.status !== "COMPLETED").length,
        completedJobsCount: jobsStore.filter(j => j.status === "COMPLETED").length,
        totalViews
      },
      styleGuides: vaultExtras.styleGuides,
      characterBibles: vaultExtras.characterBibles,
      hookFormulas: vaultExtras.hookFormulas,
      logs: vaultExtras.logs.slice(0, 30)
    });
  });
```

### 4.4 Changes to `src/types.ts`
Add `totalViews: number;` to `VaultData.metrics` (lines 82-89):
```typescript
export interface VaultData {
  metrics: {
    totalSpent: number;
    totalTokens: number;
    totalRevenue: number;
    dailyBudget: number;
    activeJobsCount: number;
    completedJobsCount: number;
    totalViews: number;
  };
  ...
```

### 4.5 Changes to `src/components/BottomStatusBar.tsx`
Update `BottomStatusBar.tsx` (lines 10-47):
```tsx
export const BottomStatusBar: React.FC<BottomStatusBarProps> = ({
  vaultData,
  completedJobsCount
}) => {
  const spent = vaultData?.metrics.totalSpent ?? 0;
  const budget = vaultData?.metrics.dailyBudget ?? 5.00;
  const completedJobs = vaultData?.metrics.completedJobsCount ?? completedJobsCount ?? 0;
  const rawViews = vaultData?.metrics.totalViews ?? 0;

  // Format view count dynamically (e.g. 184500 -> "184.5K")
  const formatViews = (count: number): string => {
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
    return count.toString();
  };

  return (
    <footer className="h-9 bg-[#070b14] border-t border-[#192437] px-4 sm:px-6 flex items-center justify-between text-xs font-mono text-slate-400 select-none shrink-0 z-30">
      {/* Left: Today videos posted */}
      <div className="flex items-center gap-2">
        <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
        <span>
          Today: <strong className="text-slate-100 font-semibold">{completedJobs} videos posted</strong>
        </span>
      </div>

      {/* Center: Total views */}
      <div className="flex items-center gap-2">
        <Eye className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-slate-100 font-semibold">{formatViews(rawViews)} views</span>
      </div>

      {/* Right: Daily Budget & Spent */}
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

---

## 5. Verification Method

### 5.1 Test Suite Verification
1. **Create Backend Unit & Integration Tests (`tests/test_vault.py`)**:
   Test the new repository methods and the FastAPI `/api/vault` endpoint using `pytest` / `pytest-asyncio` / `httpx.AsyncClient`:
   ```bash
   pytest tests/test_vault.py -v
   pytest tests/test_config.py -v
   ```
2. **Execute Full Test Suite**:
   ```bash
   pytest
   ```

### 5.2 Endpoint JSON Verification
Run the FastAPI backend:
```bash
python run_backend.py
```
Send HTTP request:
```bash
curl -X GET http://localhost:8000/api/vault
```
Verify the JSON response has:
- `metrics.totalViews` (int >= 0)
- `metrics.completedJobsCount` (int >= 0)
- `metrics.activeJobsCount` (int >= 0)
- `metrics.totalSpent` (float)
- `metrics.dailyBudget` (float, matching `DAILY_BUDGET_USD` or 5.0)

### 5.3 Frontend Typecheck & Build Verification
Run TypeScript compiler check:
```bash
npm run lint
```
Run frontend build:
```bash
npm run build
```
Verify that `BottomStatusBar.tsx` compiles with zero errors and renders live dynamic metrics without fallback placeholders.

### 5.4 Invalidation Conditions
- If `vaultData.metrics` does not contain `totalViews`, `BottomStatusBar` will have a TypeScript compilation error.
- If `GET /api/vault` returns HTTP 404 on the FastAPI backend, the endpoint has not been registered properly in `dashboard/main.py`.
- If `totalViews` is hardcoded to a static number rather than querying `Repository.get_total_views()`, the acceptance criteria is violated.
