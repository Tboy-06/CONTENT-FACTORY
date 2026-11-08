# CONTENT-FACTORY — Technical Specification & Project Qualification Document

**Version:** 1.0  
**Date:** 2026-08-31  
**Location:** `D:\CONTENT-FACTORY`  
**Classification:** Internal — Build Reference

---

## 1. Executive Summary

| Attribute | Value |
|---|---|
| **Project Name** | CONTENT-FACTORY |
| **Type** | Multi-agent AI content automation pipeline |
| **Architecture** | Modular FastAPI backend + agent orchestration + Telegram bot + web dashboard |
| **Primary Goal** | Automate research → script → video → post → analyze loop for faceless social media channels |
| **Human Role** | Goal-setting, approval via Telegram, optional premium video generation via Gemini Pro plan (Flow/Veo) |
| **Cost Model** | $0 software, ~$0.01–0.50/video API (free tier), optional premium manual step |
| **Timeline** | 4 phases over ~2–4 weeks part-time |
| **Team Size** | 1 developer (you) + AI assistant (me) |

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM BOT                              │
│  (Approval UI, Commands, Notifications, Premium Prompt Delivery) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     FASTAPI BACKEND (Port 8000)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │  SCHEDULER  │ │  JOB QUEUE  │ │   VAULT     │ │  CONFIG   │  │
│  │  (APSched)  │ │  (SQLite)   │ │  (SQLite)   │ │ (Pydantic)│  │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘  │
│         │               │               │               │        │
│  ┌──────▼───────────────▼───────────────▼───────────────▼────┐  │
│  │                    AGENT ORCHESTRATOR                       │  │
│  │  Manager → Researcher → Scriptwriter → QC → Art Director  │  │
│  │  → Video Editor → QC → Poster → Analyst → (feedback loop) │  │
│  └────────────────────────────────────────────────────────────┘  │
│         │               │               │               │        │
│  ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼────┐  │
│  │   TOOLS     │ │  EXTERNAL   │ │  LOCAL      │ │  VAULT    │  │
│  │  (API/SDK)  │ │  SERVICES   │ │  BINARIES   │ │  (DB)     │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      WEB DASHBOARD (Port 8002)                   │
│  (Pipeline Board, Analytics, Cost Tracker, Agent Status)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Module Specifications

### 3.1 Core Infrastructure

#### 3.1.1 Configuration (`backend/config.py`)
| Aspect | Detail |
|---|---|
| **Framework** | Pydantic Settings v2 |
| **Env File** | `.env` (gitignored), `.env.example` (committed) |
| **Settings Groups** | LLM, Vision, Images, Video, Voice, Posting, Telegram, Database, Scheduler, Dashboard |
| **Validation** | Type coercion, required fields, default fallbacks |
| **Lines** | ~120 |
| **Dependencies** | `pydantic-settings`, `python-dotenv` |

#### 3.1.2 Vault / Database (`backend/vault/`)
| File | Responsibility | Lines | Tables |
|---|---|---|---|
| `models.py` | SQLAlchemy 2.0 declarative models | ~200 | `jobs`, `job_stages`, `agents`, `assets`, `analytics`, `style_guides`, `character_bible`, `approvals`, `costs`, `logs` |
| `database.py` | Engine, session factory, init, migrations | ~80 | — |
| `repository.py` | CRUD + query helpers per model | ~300 | — |
| `migrations/` | Alembic migrations (auto-generated) | — | 1 initial + incremental |

**Schema Highlights:**
```sql
jobs: id, niche, status, current_stage, priority, created_at, updated_at, config_json
job_stages: id, job_id, stage_name, status, started_at, completed_at, agent_id, input_json, output_json, error
assets: id, job_id, asset_type, path, metadata_json, created_at
analytics: id, job_id, platform, views, watch_time, retention_pct, ctr, revenue, fetched_at
style_guides: id, name, source_video_url, extracted_json, created_at
character_bible: id, name, prompt, reference_images_json, style_guide_id, created_at
approvals: id, job_id, stage, requested_at, resolved_at, decision, decided_by, notes
costs: id, job_id, provider, operation, tokens_in, tokens_out, usd_estimate, created_at
logs: id, level, agent, message, context_json, created_at
-- NEW from video analysis:
skill_manifests: id, name, yaml_content, version, created_at
hook_formulas: id, name, pattern, platform, retention_data_json, created_at
revenue_streams: id, job_id, source, amount, currency, date, metadata_json
retention_curves: id, job_id, platform, time_points_json, retention_values_json, created_at
```

#### 3.1.3 Agent Base Class (`backend/agents/base.py`)
| Feature | Implementation |
|---|---|
| **Interface** | `async def run(job: Job) -> Job` |
| **Memory** | Reads/writes `job.assets` + `vault` via repository |
| **Tools** | Injected tool registry (callable functions with schemas) |
| **LLM Client** | Abstracted `LLMClient` protocol (Gemini, Ollama, Claude) |
| **Error Handling** | Retry with exponential backoff, circuit breaker, dead-letter queue |
| **Logging** | Structured JSON logs to vault + stdout |
| **Metrics** | Duration, token counts, success/failure per run |
| **Lines** | ~180 |

#### 3.1.4 Scheduler (`backend/scheduler.py`)
| Feature | Detail |
|---|---|
| **Library** | APScheduler 3.x (async) |
| **Jobs** | `daily_research` (cron 06:00), `pipeline_tick` (every 5 min), `analytics_fetch` (cron 02:00), `cleanup_old_jobs` (cron weekly) |
| **Persistence** | Job store in SQLite (survives restarts) |
| **Concurrency** | Max 3 concurrent pipeline ticks |
| **Lines** | ~100 |

---

### 3.2 Agents (9 Total)

| Agent | File | Primary Tools Called | Est. Lines | Complexity |
|---|---|---|---|---|
| **Manager** | `manager.py` | `create_job`, `assign_stage`, `escalate`, `notify_telegram`, `spawn_meta_agent` | ~180 | Medium |
| **Researcher** | `researcher.py` | `youtube_search`, `web_search`, `reddit_search`, `score_virality`, `agent_reach_skill` | ~280 | High |
| **Style Analyst** | `style_analyst.py` | `gemini_vision_analyze_video`, `extract_style_guide`, `extract_hook_formula` | ~230 | High |
| **Scriptwriter** | `scriptwriter.py` | `llm_generate`, `format_per_platform`, `apply_hook_formula` | ~250 | Medium |
| **Art Director** | `art_director.py` | `image_gen`, `build_character_bible`, `generate_shot_list`, `flow_character_ref` | ~310 | High |
| **Video Editor** | `video_editor.py` | `fetch_images`, `edge_tts`, `ffmpeg_assemble`, `build_flow_prompt_pack`, `apply_retention_pacing` | ~380 | High |
| **Quality Control** | `quality_control.py` | `check_originality`, `check_policy`, `check_sync`, `check_brand`, `validate_structured_output` | ~280 | Medium |
| **Poster** | `poster.py` | `postiz_upload`, `postiz_schedule`, `platform_format` | ~200 | Medium |
| **Analyst** | `analyst.py` | `youtube_analytics`, `tiktok_analytics`, `compute_insights`, `write_report`, `track_revenue` | ~330 | High |

**Total Agent Code:** ~2,440 lines

---

### 3.3 Tools (External Integrations)

| Tool | File | Purpose | API/Method | Lines |
|---|---|---|---|---|
| Web Search | `web_search.py` | General web search | SerpAPI / DuckDuckGo HTML scrape | ~120 |
| YouTube API | `youtube_api.py` | Search, video details, analytics | YouTube Data API v3 | ~180 |
| Gemini Vision | `gemini_vision.py` | Analyze video frames for style | Gemini API (vision) | ~150 |
| Image Gen | `image_gen.py` | Generate images | ComfyUI local / Pexels / Nano Banana | ~180 |
| TTS | `tts.py` | Text-to-speech | Edge-TTS (Microsoft) | ~80 |
| FFmpeg Assembler | `ffmpeg_assembler.py` | Build video from images+audio | FFmpeg subprocess | ~250 |
| Postiz Client | `postiz_client.py` | Upload, schedule, status | Postiz REST API | ~150 |
| YouTube Analytics | `youtube_analytics.py` | Fetch channel/video stats | YouTube Analytics API | ~180 |
| TikTok Analytics | `tiktok_analytics.py` | Fetch video stats | TikTok Business API | ~150 |
| **NEW — Agent Reach Skill** | `agent_reach_skill.py` | Execute Agent Reach skills (YouTube, Reddit, web, stocks) | Anthropic Skills SDK | ~150 |
| **NEW — Structured Output** | `structured_output.py` | Zod/Pydantic schema enforcement for agent outputs | Pydantic + Instructor | ~120 |
| **NEW — Memory/Postgres** | `memory_postgres.py` | Window buffer memory + Postgres persistence | asyncpg + pgvector | ~180 |
| **NEW — Hook Formula Engine** | `hook_formula.py` | Apply proven hook patterns (Problem→Agitate→Solution) | Local rule engine | ~100 |
| **NEW — Retention Pacing** | `retention_pacing.py` | Adjust video timing based on retention curves | FFmpeg filter graphs | ~120 |
| **NEW — Revenue Tracker** | `revenue_tracker.py` | Track sponsorship, affiliate, ad revenue per video | Manual entry + APIs | ~100 |

**Total Tools Code:** ~2,950 lines

---

### 3.4 Telegram Bot

| File | Responsibility | Lines |
|---|---|---|
| `bot.py` | Application setup, webhook/polling, middleware | ~100 |
| `handlers.py` | Command handlers, callback queries, approval flows | ~400 |
| `keyboards.py` | Inline keyboard builders (approve/reject/variants) | ~120 |
| `formatters.py` | Message formatting (Markdown, prompt packs) | ~100 |

**Total Bot Code:** ~720 lines

---

### 3.5 Web Dashboard

| Component | Tech | Lines | Features |
|---|---|---|---|
| Backend | FastAPI + Jinja2 | ~400 | REST API for dashboard data, Server-Sent Events for live updates |
| Templates | HTML + Tailwind CDN + Alpine.js | ~800 | Pipeline board (Kanban), Analytics charts (Chart.js), Agent status, Cost tracker, Content library |
| Static | CSS/JS | ~200 | Theme, interactions |

**Total Dashboard:** ~1,400 lines

---

### 3.6 Project Root & Config

| File | Purpose | Lines |
|---|---|---|
| `requirements.txt` | Pinned dependencies | ~40 |
| `.env.example` | Template with all vars documented | ~60 |
| `README.md` | Setup, usage, architecture diagram | ~200 |
| `run.py` | Entry point (lock file, signal handling, uvicorn) | ~80 |
| `main.py` | FastAPI app factory, lifespan, routers | ~120 |
| `docker-compose.yml` | Postiz + optional services | ~50 |
| `.gitignore` | Standard Python + project ignores | ~30 |

---

## 4. Project Size Estimates

### 4.1 Lines of Code (LOC) by Category

| Category | Files | Est. LOC | % of Total |
|---|---|---|---|
| **Core Infrastructure** | 8 | ~980 | 11% |
| **Agents (9)** | 9 | ~2,440 | 28% |
| **Tools (17)** | 17 | ~2,950 | 34% |
| **Telegram Bot** | 4 | ~720 | 8% |
| **Web Dashboard** | ~15 | ~1,400 | 16% |
| **Project Root/Config** | 7 | ~580 | 7% |
| **Tests** | ~20 | ~1,000 | 12% |
| **TOTAL** | **~80** | **~8,970** | **100%** |

### 4.2 Disk Space Estimate

| Component | Size |
|---|---|
| Source code (`.py`, `.html`, `.css`, `.js`) | ~450 KB |
| Virtual environment (deps) | ~350–500 MB |
| SQLite database (vault.db) | ~10–50 MB (grows with jobs) |
| Generated assets (images, videos, audio) | ~50–500 MB per 100 videos |
| Logs | ~10–20 MB/month |
| **Total (empty project)** | **~500 MB** |
| **Total (100 videos produced)** | **~1–2 GB** |

### 4.3 Dependency Count

| Type | Count |
|---|---|
| **Production (requirements.txt)** | 28 packages |
| **Development (requirements-dev.txt)** | 12 packages |
| **Total unique packages** | 40 |

**Key Production Dependencies:**
```
fastapi==0.115.*
uvicorn==0.32.*
sqlalchemy==2.0.*
alembic==1.13.*
pydantic==2.9.*
pydantic-settings==2.5.*
python-telegram-bot==21.6.*
apscheduler==3.10.*
httpx==0.27.*
google-generativeai==0.8.*
edge-tts==6.1.*
ffmpeg-python==0.2.*
python-dotenv==1.0.*
jinja2==3.1.*
asyncpg==0.29.*
pgvector==0.2.*
instructor==1.5.*
anthropic==0.39.*
serpapi==0.1.* (optional)
tavily==0.3.* (optional)
firecrawl==0.1.* (optional)
tailwindcss==0.0.* (via CDN, not pip)
chart.js==4.4.* (via CDN)
alpinejs==3.14.* (via CDN)
```

---

## 5. Functional Requirements (FR)

### 5.1 Pipeline Orchestration
| ID | Requirement | Priority |
|---|---|---|
| FR-001 | System shall accept high-level goals (niche, frequency, platforms) via Telegram | Must |
| FR-002 | Manager agent shall decompose goals into discrete jobs with stages | Must |
| FR-003 | Each job shall progress through defined stages: IDEA → RESEARCH → SCRIPT → QC1 → ART → VIDEO → QC2 → POST → ANALYZE | Must |
| FR-004 | Job state shall persist in SQLite and survive process restarts | Must |
| FR-005 | Scheduler shall trigger daily research and periodic pipeline ticks | Must |
| FR-006 | Failed stages shall retry up to 3 times with exponential backoff | Must |
| FR-007 | Human approval gates shall block progression until resolved via Telegram | Must |

### 5.2 Research & Ideation
| ID | Requirement | Priority |
|---|---|---|
| FR-008 | Researcher shall query YouTube trending/search for configured niches | Must |
| FR-009 | Researcher shall scrape Reddit/X/RSS for rising topics | Should |
| FR-010 | Each idea shall be scored for virality potential (0–100) | Must |
| FR-011 | Research briefs shall include: topic, angle, reference URLs, score, rationale | Must |
| FR-012 | Idea bank shall store ≥100 ideas per niche | Should |
| **NEW — FR-013** | Researcher shall execute **Agent Reach skills** for YouTube summarization, Reddit trends, web scraping, stock data | Should |
| **NEW — FR-014** | Researcher shall support **meta-agent pattern**: spawn sub-agents for complex multi-step research | Could |

### 5.3 Style Analysis
| ID | Requirement | Priority |
|---|---|---|
| FR-013 | Style Analyst shall accept a reference video URL or local file | Must |
| FR-014 | Vision model shall extract: hook formula, pacing, scene rhythm, visual style, character design language | Must |
| FR-015 | Style guide shall be saved to vault for reuse across videos | Must |
| FR-016 | Style guide shall NOT contain copyrighted content (scripts, exact visuals) | Must |
| **NEW — FR-017** | Style Analyst shall extract **hook formulas** (Problem→Agitate→Solution→Proof→CTA) with retention correlation | Must |
| **NEW — FR-018** | Style Analyst shall extract **character reference specs** for Google Flow character consistency feature | Should |

### 5.4 Scriptwriting
| ID | Requirement | Priority |
|---|---|---|
| FR-017 | Scriptwriter shall produce original scripts from research brief + style guide | Must |
| FR-018 | Output shall include: hook, beats, narration, captions, titles, hashtags per platform | Must |
| FR-019 | Minimum 2 variants per topic; up to 3 | Should |
| FR-020 | Scripts shall pass originality check (no verbatim copying from references) | Must |
| **NEW — FR-021** | Scriptwriter shall apply **proven hook formulas** (Problem→Agitate→Solution→Proof→CTA) from vault | Must |
| **NEW — FR-022** | Scripts shall be emitted as **structured output** (Pydantic/Zod schema) for reliable downstream parsing | Must |

### 5.5 Art Direction
| ID | Requirement | Priority |
|---|---|---|
| FR-021 | Art Director shall generate character prompts + reference images | Must |
| FR-022 | Character bible shall enforce consistency across videos | Must |
| FR-023 | Shot list shall map script beats to visual scenes | Must |
| FR-024 | Thumbnails/covers shall be generated per platform aspect ratio | Should |
| **NEW — FR-025** | Art Director shall generate **Google Flow character reference packs** (3+ angles + expressions) for consistency | Should |
| **NEW — FR-026** | Character bible shall include **style-DNA fingerprint** for cross-video visual coherence | Could |

### 5.6 Video Editing
| ID | Requirement | Priority |
|---|---|---|
| FR-025 | Free path: assemble video from images + Edge-TTS + captions + Ken Burns motion via FFmpeg | Must |
| FR-026 | Premium path: generate Flow/Veo prompt pack for manual generation | Must |
| FR-027 | Output aspect ratios: 9:16, 16:9, 1:1 | Must |
| FR-028 | Captions shall be word-level timed, animated, platform-styled | Should |
| FR-029 | Intro/outro branding shall be configurable | Could |
| **NEW — FR-030** | Video Editor shall apply **retention-driven pacing**: adjust scene duration, cut points per retention curve data | Should |
| **NEW — FR-031** | Video Editor shall support **loop-point optimization** (seamless 15s loop for Shorts) | Could |

### 5.7 Quality Control
| ID | Requirement | Priority |
|---|---|---|
| FR-030 | QC shall check script originality (similarity < 0.3 vs references) | Must |
| FR-031 | QC shall check for banned words / policy risks per platform | Must |
| FR-032 | QC shall verify audio/video sync, caption accuracy | Must |
| FR-033 | QC shall enforce brand consistency (fonts, colors, tone) | Should |
| FR-034 | Verdicts: PASS, FAIL (with notes), UNCERTAIN (escalate to human) | Must |
| **NEW — FR-035** | QC shall validate **structured output compliance** (schema match, required fields) | Must |
| **NEW — FR-036** | QC shall check **retention risk flags**: hook < 3s, drop > 20% at 10s, no CTA | Should |

### 5.8 Posting
| ID | Requirement | Priority |
|---|---|---|
| FR-035 | Poster shall publish to TikTok, Instagram, YouTube, Facebook, X, LinkedIn via Postiz | Must |
| FR-036 | Per-platform caption/hashtag optimization | Must |
| FR-037 | Optimal-time scheduling based on analytics | Should |
| FR-038 | Approval mode per platform: manual / auto-after-first / full-auto | Must |

### 5.9 Analytics & Feedback
| ID | Requirement | Priority |
|---|---|---|
| FR-039 | Analyst shall fetch daily analytics from YouTube/TikTok/IG APIs | Must |
| FR-040 | Compute: top hooks, topics, lengths, posting times, retention drivers | Must |
| FR-041 | Weekly report delivered to Telegram | Must |
| FR-042 | Insights shall feed back into Researcher's scoring weights | Must |
| **NEW — FR-043** | Analyst shall track **multi-stream revenue**: YT Partner, sponsorships, affiliate per video | Should |
| **NEW — FR-044** | Analyst shall generate **retention curve analysis** (drop points, loop effectiveness) | Should |
| **NEW — FR-045** | Analyst shall correlate **hook formula → retention → revenue** for formula ranking | Could |

### 5.10 Telegram Interface
| ID | Requirement | Priority |
|---|---|---|
| FR-043 | `/start` → welcome + config summary | Must |
| FR-044 | `/goal <niche> <freq> <platforms>` → set/create goal | Must |
| FR-045 | `/approve <job_id>` / `/reject <job_id> <reason>` / `/variants <job_id> <n>` | Must |
| FR-046 | `/preview <job_id>` → sends script/video | Must |
| FR-047 | `/premium <job_id>` → delivers Flow/Nano Banana prompt pack | Must |
| FR-048 | `/upload_premium <job_id>` → accepts MP4, continues pipeline | Must |
| FR-049 | `/status` → pipeline overview | Must |
| FR-050 | `/cost` → daily/weekly/monthly spend | Must |
| FR-051 | `/report` → latest weekly analytics report | Must |
| FR-052 | Daily digest at 08:00 with pending approvals + stats | Should |
| **NEW — FR-053** | `/hook <formula_name>` → shows hook formula with retention stats | Could |
| **NEW — FR-054** | `/revenue <job_id>` → shows revenue breakdown for video | Could |
| **NEW — FR-055** | `/retention <job_id>` → sends retention curve chart | Could |
| **NEW — FR-056** | `/skill <skill_name> <params>` → run Agent Reach skill ad-hoc | Could |

### 5.11 Dashboard
| ID | Requirement | Priority |
|---|---|---|
| FR-053 | Pipeline board (Kanban) with drag-drop stage view | Must |
| FR-054 | Agent status lights (idle/running/error) with last action | Must |
| FR-055 | Content library (searchable, filterable) | Should |
| FR-056 | Analytics charts: views over time, retention, traffic sources | Must |
| FR-057 | Cost tracker: cumulative, per-video, per-provider | Must |
| FR-058 | Live updates via SSE (no polling) | Should |
| **NEW — FR-059** | **Hook Formula Library** view: searchable, with retention/revenue correlation | Could |
| **NEW — FR-060** | **Revenue Dashboard**: stacked bar by source (ads/sponsor/affiliate) per video | Could |
| **NEW — FR-061** | **Retention Curve Overlay**: compare multiple videos' retention graphs | Could |
| **NEW — FR-062** | **Skill Manifest Registry**: view/install Agent Reach skills | Could |

---

## 6. Non-Functional Requirements (NFR)

| ID | Requirement | Target |
|---|---|---|
| NFR-001 | **Availability** | 99% uptime for backend (single-node, no HA required) |
| NFR-002 | **Latency** | Pipeline tick ≤ 30s; Telegram response ≤ 2s; Dashboard load ≤ 3s |
| NFR-003 | **Throughput** | Support 50 concurrent jobs; 20 videos/day per niche |
| NFR-004 | **Cost Control** | Hard cap per video (configurable, default $2); daily budget alert |
| NFR-005 | **Security** | API keys in `.env` only; no secrets in DB; Telegram chat_id whitelist |
| NFR-006 | **Privacy** | No user PII stored except Telegram chat_id; analytics aggregated |
| NFR-007 | **Observability** | Structured JSON logs; per-job trace; cost tracking per operation |
| NFR-008 | **Maintainability** | Modular agents; <200 lines per file; type hints throughout; pytest coverage ≥80% |
| NFR-009 | **Portability** | Runs on Windows (dev) and Linux (prod); Docker-compose for Postiz |
| NFR-010 | **Extensibility** | New agents/tools via registry pattern; new platforms via Poster plugin |
| **NEW — NFR-011** | **Structured Output Reliability** | 99.9% schema compliance for agent-to-agent data passing |
| **NEW — NFR-012** | **Memory Persistence** | Conversation context survives restarts (Postgres + pgvector) |
| **NEW — NFR-013** | **Character Consistency** | Visual character ID match ≥ 0.85 across videos (embedding similarity) |

---

## 7. Qualification Requirements (Team & Environment)

### 7.1 Developer Skills Required

| Skill | Level | Notes |
|---|---|---|
| **Python 3.11+** | Advanced | Async/await, type hints, decorators, context managers |
| **FastAPI** | Intermediate | Dependency injection, lifespan, background tasks, WebSockets/SSE |
| **SQLAlchemy 2.0** | Intermediate | Async ORM, migrations (Alembic), relationship loading |
| **Pydantic v2** | Intermediate | Settings, validation, serialization |
| **LLM Integration** | Intermediate | Prompt engineering, function calling, structured output, token counting |
| **FFmpeg** | Basic | Filter graphs, subprocess handling, audio/video sync |
| **Telegram Bot API** | Basic | python-telegram-bot v21, inline keyboards, webhooks |
| **Docker** | Basic | docker-compose, volumes, networking |
| **Git** | Standard | Branching, commits, PRs |
| **SQLite** | Basic | WAL mode, vacuum, backup |
| **NEW — Postgres/pgvector** | Basic | Asyncpg, vector embeddings, connection pooling |
| **NEW — Structured Output** | Intermediate | Instructor/Pydantic validation, Zod schemas, retry on failure |
| **NEW — Anthropic Skills SDK** | Basic | Skill manifest YAML, installation, execution |

### 7.2 External Accounts Required (All Free Tier Available)

| Service | Purpose | Free Tier Limits |
|---|---|---|
| **Google AI Studio** | Gemini 1.5 Flash/Pro API | 15 RPM, 1M tokens/day (Flash) |
| **Pexels** | Stock images/video | 200 req/hr, 20k/month |
| **YouTube Data API v3** | Search, video details | 10,000 units/day |
| **YouTube Analytics API** | Channel/video stats | Standard quota |
| **TikTok Business API** | Posting + analytics | Requires approval |
| **Meta Graph API** | IG/FB posting + analytics | Requires app review |
| **X API** | Posting + analytics | Free tier: 1,500 posts/mo |
| **LinkedIn API** | Posting | Requires partner approval |
| **Postiz (self-hosted)** | Unified posting UI | Unlimited (your server) |
| **Telegram Bot** | Approval interface | Unlimited |
| **NEW — Anthropic Skills** | Agent Reach skill execution | Free (open source) |
| **NEW — Postgres** | Memory persistence + pgvector | Local (free) or Neon/Supabase free tier |
| **NEW — SerpAPI / Tavily** | Web search for Researcher | SerpAPI: 100/mo free; Tavily: 1,000/mo free |
| **NEW — Firecrawl / Jina Reader** | Web scraping for Researcher | Firecrawl: 500/mo free; Jina: unlimited free |

### 7.3 Local Environment Requirements

| Requirement | Spec |
|---|---|
| **OS** | Windows 10/11 (dev), Ubuntu 22.04+ (prod) |
| **Python** | 3.11 or 3.12 |
| **RAM** | 8 GB minimum (16 GB recommended for local ComfyUI) |
| **GPU** | Optional: NVIDIA 8GB+ VRAM for local FLUX/SD |
| **Disk** | 5 GB free for venv + DB + assets |
| **FFmpeg** | 6.0+ in PATH |
| **Docker** | 24+ for Postiz |

---

## 8. Testing Strategy

| Level | Tool | Coverage Target | Notes |
|---|---|---|---|
| **Unit** | pytest + pytest-asyncio | ≥80% | Agents, tools, vault, config |
| **Integration** | pytest + testcontainers | Key flows | Pipeline tick, Telegram handlers, Postiz |
| **Contract** | schemathesis | API schemas | FastAPI OpenAPI spec |
| **E2E** | Manual / scripted | Critical path | Goal → video → post → analytics |
| **Load** | locust | 10 concurrent users | Dashboard + API |
| **Security** | bandit, safety | No high findings | Dependencies, secrets |

**Test Structure:**
```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_vault_models.py
│   ├── test_vault_repository.py
│   ├── test_agent_base.py
│   ├── test_manager.py
│   ├── test_researcher.py
│   ├── test_scriptwriter.py
│   ├── test_video_editor.py
│   └── test_tools/
├── integration/
│   ├── test_pipeline_tick.py
│   ├── test_telegram_handlers.py
│   └── test_postiz_client.py
├── e2e/
│   └── test_full_pipeline.py
├── fixtures/
└── conftest.py
```

---

## 9. Deployment & Operations

### 9.1 Development (Windows)
```bash
cd D:\CONTENT-FACTORY
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python backend/run.py
# Backend: http://localhost:8000
# Dashboard: http://localhost:8002
# Telegram bot: polling mode
```

### 9.2 Production (Linux Server)
```bash
# Systemd service for backend
# Nginx reverse proxy + SSL for dashboard
# Docker-compose for Postiz
# SQLite WAL mode + periodic vacuum
# Daily DB backup to S3/local
```

### 9.3 Monitoring
- **Health endpoint:** `GET /health` → {status, db, scheduler, agents}
- **Metrics:** Prometheus `/metrics` (optional) or custom `/metrics` JSON
- **Alerts:** Telegram on pipeline stall, cost overrun, API quota near limit

---

## 10. Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Platform API approval delays (TikTok/Meta) | High | Medium | Start Phase 3 Day 1; manual upload fallback |
| Gemini free tier quota exhaustion | Medium | High | Monitor usage; fallback to Ollama local; batch requests |
| FFmpeg video quality insufficient for monetization | Medium | Medium | Premium path via Flow; improve FFmpeg filters |
| Copyright strike from style extraction | Low | High | Strict QC: similarity checks, originality enforcement |
| Telegram bot token leak | Low | Critical | `.env` only; rotate quarterly; chat_id whitelist |
| Postiz self-hosted maintenance burden | Medium | Low | Documented runbook; auto-updates via watchtower |
| Local LLM quality too low for scripts | Low | Medium | Default to Gemini free tier; local optional |
| Database corruption / lock contention | Low | High | WAL mode; connection pooling; retry logic |

---

## 11. Phase Acceptance Criteria

### Phase 1 — Brain ✅
- [ ] `python backend/run.py` starts FastAPI + scheduler + Telegram bot
- [ ] `/goal finance 3 tiktok,youtube` creates recurring job
- [ ] Researcher finds 10+ ideas/day, scores them, saves briefs
- [ ] **NEW:** Researcher executes Agent Reach skills (YouTube summarize, Reddit trends)
- [ ] Scriptwriter produces 2–3 script variants per brief
- [ ] **NEW:** Scripts emitted as structured output (Pydantic schema)
- [ ] **NEW:** Scripts apply hook formulas from vault
- [ ] Telegram shows scripts with Approve/Reject/Variants buttons
- [ ] Vault persists all jobs, stages, assets, costs
- [ ] **NEW:** Postgres + pgvector running for memory persistence
- [ ] Unit tests pass ≥80%

### Phase 2 — Studio ✅
- [ ] Style Analyst extracts style guide from reference video URL
- [ ] **NEW:** Style Analyst extracts hook formulas with retention correlation
- [ ] **NEW:** Style Analyst extracts character reference specs for Flow
- [ ] Art Director generates character bible + shot list
- [ ] **NEW:** Art Director generates Google Flow character reference packs (3+ angles)
- [ ] Video Editor (FFmpeg path) outputs 9:16 MP4 with TTS + captions
- [ ] **NEW:** Video Editor applies retention-driven pacing from curve data
- [ ] QC passes/fails with notes; Telegram preview works
- [ ] **NEW:** QC validates structured output compliance
- [ ] **NEW:** QC checks retention risk flags (hook < 3s, drop > 20% at 10s)
- [ ] Premium path generates Flow prompt pack (Markdown)
- [ ] Integration tests pass

### Phase 3 — Distribution ✅
- [ ] Postiz running locally, authenticated
- [ ] Poster uploads + schedules to at least 2 platforms
- [ ] Platform developer apps submitted (TikTok, Meta, YouTube)
- [ ] Approval modes work per platform
- [ ] Manual upload fallback documented
- [ ] **NEW:** Skill Manifest Registry in dashboard for Agent Reach skills

### Phase 4 — Flywheel ✅
- [ ] Analyst fetches analytics daily, computes insights
- [ ] **NEW:** Analyst tracks multi-stream revenue (ads/sponsor/affiliate) per video
- [ ] **NEW:** Analyst generates retention curve analysis with drop-point detection
- [ ] **NEW:** Analyst correlates hook formula → retention → revenue for formula ranking
- [ ] Weekly report delivered to Telegram + dashboard
- [ ] Insights adjust Researcher weights
- [ ] Dashboard shows pipeline board, analytics, costs
- [ ] **NEW:** Dashboard shows Hook Formula Library with retention/revenue correlation
- [ ] **NEW:** Dashboard shows Revenue Dashboard (stacked by source)
- [ ] **NEW:** Dashboard shows Retention Curve Overlay comparison
- [ ] **NEW:** Dashboard shows Skill Manifest Registry
- [ ] Full-auto mode toggle works
- [ ] Load test: 20 videos/day sustained
- [ ] Documentation complete

---

## 12. Maintenance & Evolution

| Activity | Frequency | Owner |
|---|---|---|
| Dependency updates | Monthly | Dev |
| API quota review | Weekly | Dev |
| Cost review | Weekly | Dev |
| Database vacuum | Weekly (auto) | Scheduler |
| Log rotation | Daily (auto) | Scheduler |
| Asset cleanup (>90 days) | Monthly | Scheduler |
| Model version pin review | Quarterly | Dev |
| Platform API changelog watch | Ongoing | Dev |
| Backup verification | Monthly | Dev |

---

## 13. Future Extensions (Post-MVP)

| Extension | Effort | Value |
|---|---|---|
| Multi-niche parallel pipelines | Medium | Scale to multiple channels |
| A/B testing framework for hooks/thumbnails | Medium | Optimize CTR |
| Voice cloning (ElevenLabs/OpenVoice) | Low | Brand voice consistency |
| Live streaming clip extraction | High | Shorts from streams |
| Collaboration mode (team approvals) | Medium | Agency use |
| Plugin marketplace for agents/tools | High | Extensibility |
| **NEW — Meta-Agent Framework** | High | Agents that build/deploy other agents (v11 pattern) |
| **NEW — Multi-Modal Style Transfer** | High | Extract style from any media (image, audio, video) → apply to new content |
| **NEW — Autonomous Revenue Optimization** | High | Auto-negotiate sponsorships, optimize affiliate links, pitch brands |

---

## 14. Sign-Off

| Role | Name | Date | Signature |
|---|---|---|---|
| **Product Owner** | (You) | | |
| **Lead Developer** | (You + AI) | | |
| **QA** | (You) | | |

---

*This document is the single source of truth for CONTENT-FACTORY build scope. All code, tests, and reviews must trace back to requirements herein.*

---

## 15. Source Material — Video Analysis Reference (2026-08-31)

### Batch 1 (Previously Analyzed)
| ID | File | Duration | Creator | Key Contribution |
|---|---|---|---|---|
| v1 | Download (2).mp4 | 42.4s | @jakedavidsai | ATLAS promo: AI agent org-chart, Telegram chief-of-staff, vault graph, metrics dashboard |
| v5 | Download (5).mp4 | 42.4s | @ajthompson.ai | n8n beginner: Webhook → AI Agent (Anthropic) → Email |
| v6 | Download (6).mp4 | 84.2s | @nikothetech | Agent Reach: free Claude skill for YouTube/Reddit/web scrape |
| v7 | Download (7).mp4 | 118.9s | @dawoodzahidd | **Core pipeline**: reference video → style DNA → original script → character → Google Flow video |
| v8 | Download (8).mp4 | 93.4s | @dawoodzahidd | Same pipeline on Cars 3: character extraction → Nano Banana → Flow |
| v9 | Download (9).mp4 | 1821.8s | @stephenpope | n8n AI Agent deep-dive: memory, tools, testing |
| v10 | Download (10).mp4 | 3600.8s | @devenseenath | YouTube Studio analytics: retention, traffic sources, monetization |

### Batch 2 (Newly Analyzed — 13 Videos)
| ID | File | Duration | Creator | Key Contribution |
|---|---|---|---|---|
| v11 | Download (11).mp4 | 79.7s | @nikothetech | **Meta-Agent**: builds agents from goal (LangGraph + Claude Code loop) |
| v12 | Download (12).mp4 | 32.3s | @nikothetech | Agent Reach quick demo: Reddit trend finder JSON output |
| v13 | Download (13).mp4 | 154.1s | @dawoodzahidd | **Extended tutorial**: full pipeline with exact prompts for each step |
| v14 | Download (14).mp4 | 58.5s | @dawoodzahidd | **Character consistency**: Flow character reference (3 angles → new scenes) |
| v15 | Download (15).mp4 | 42.4s | @ajthompson.ai | n8n: AI Agent + Window Buffer Memory + Postgres persistence |
| v16 | Download (16).mp4 | 84.2s | @nikothetech | Agent Reach deep-dive: skill manifest YAML, install, all tools demo |
| v17 | Download (17).mp4 | 71.8s | @nikothetech | Research agent in 5 min: n8n Webhook → SerpAPI → AI Agent → Sheets |
| v18 | Download (18).mp4 | 55.8s | @stephenpope | When NOT to use AI Agent node: simple transforms = Set/Function nodes |
| v19 | Download (19).mp4 | 65.2s | @stephenpope | Tool taxonomy: Search, Scrape, Code, Browser, API — n8n config |
| v20 | Download (20).mp4 | 59.3s | @stephenpope | **Structured Output Parser** (Zod) → forced JSON → no parsing errors |
| v21 | Download (21).mp4 | 65.9s | @devenseenath | Shorts hook formula: Problem→Agitate→Solution→Proof→CTA; loop at 15s |
| v22 | Download (22).mp4 | 38.7s | @devenseenath | Retention graph analysis: flat=good, drop@2s=hook, drop@10s=pacing |
| v23 | Download (23).mp4 | 75.5s | @devenseenath | Monetization breakdown: YT Partner ($2K), Sponsors ($2K), Affiliate ($1K) |

### Consolidated Mapping: Video → Spec Component

| Spec Component | Primary Video Sources | Implementation Insight |
|---|---|---|
| **Manager** | v11 (meta-agent), v17 (n8n deployment) | Meta-agent spawns sub-agents; n8n for visual orchestration |
| **Researcher** | v6, v12, v16, v17 (Agent Reach, SerpAPI, Reddit, YouTube) | Agent Reach skill = unified interface; SerpAPI for search |
| **Style Analyst** | v7, v8, v13, v14 (style DNA extraction, character ref) | Vision model extracts formula NOT content; character ref for Flow |
| **Scriptwriter** | v13, v21 (hook formulas, script structures) | Apply proven hooks; structured output (Zod/Pydantic) |
| **Art Director** | v7, v8, v13, v14 (character bible, consistency, Flow ref) | Character bible + Flow character reference packs |
| **Video Editor** | v13 (Veo/FFmpeg/CapCut), v14 (character ref), v22 (retention pacing) | FFmpeg free path; retention-driven cuts; loop-point at 15s |
| **QC** | v18, v19, v20 (when NOT to use AI, tools, structured output) | Don't over-use AI; structured output for reliability |
| **Poster** | — | Postiz self-hosted (gap filled in spec) |
| **Analyst** | v10, v20, v21, v22, v23 (retention, hooks, monetization) | Track revenue streams; retention curves; hook→retention→revenue |
| **Memory/Persistence** | v15 (Window Buffer Memory + Postgres) | pgvector for embeddings; conversation survives restarts |
| **Agent Framework** | v11 (LangGraph meta-agent), v16 (skill manifests) | LangGraph for complex graphs; YAML skill manifests |
| **Structured Output** | v20 (Zod/Pydantic parser) | Critical for agent-to-agent data passing |

### Key Patterns Validated by Video Evidence

1. **Style Extraction → Original Generation** (v7, v8, v13, v14): The core loop works — extract *formula*, write *original* script, generate *original* visuals. Copyright-safe path confirmed.

2. **Structured Output is Non-Negotiable** (v20): Every agent-to-agent handoff must use schema-enforced JSON. Eliminates parsing errors, enables reliable pipelines.

3. **Character Consistency via Flow References** (v14): Upload 3 angles → Flow maintains character across scenes. Must integrate into Art Director.

4. **Hook Formulas Are Quantifiable** (v21, v22): Problem→Agitate→Solution→Proof→CTA with measurable retention impact. Store in vault, apply in Scriptwriter, rank in Analyst.

5. **Retention-Driven Pacing** (v22): Drop at 2s = hook problem; drop at 10s = pacing. Video Editor must adjust timing per curve data.

6. **Multi-Stream Revenue Tracking** (v23): YT Partner + Sponsorships + Affiliate. Analyst must track all three per video.

7. **Meta-Agent Pattern** (v11): High-level goal → agent writes code → tests → deploys. Manager can spawn specialized sub-agents.

8. **Skill Manifests** (v16): YAML-defined skills (Agent Reach) = portable, versioned, installable. Registry pattern for tools.

9. **Memory Persistence** (v15): Postgres + pgvector for window buffer memory + embeddings. Survives restarts.

10. **Don't Over-Use AI** (v18): Simple transforms (JSON, dates) = deterministic code nodes. AI Agent only for reasoning.