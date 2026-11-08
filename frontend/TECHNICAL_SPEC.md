# CONTENT-FACTORY: Technical Specification & Implementation Guide

## 1. System Technology Stack
- **Runtime**: Python 3.11+ (FastAPI, Uvicorn, APScheduler)
- **Database**: SQLAlchemy 2.0 Async (SQLite with `aiosqlite` default, PostgreSQL with `asyncpg` optional)
- **LLM Engine**: Google Gemini API via `@google/genai` (Server-side) & `google-generativeai` with Tenacity exponential retry
- **Models**:
  - `gemini-3.7-flash` (Primary fast reasoning agent model)
  - `gemini-2.5-pro` (Complex scriptwriting & multi-part analysis)
  - `gemini-vision` (Visual DNA & frame extraction)
  - `veo-3.1` (Video generation prompts)
- **Audio & Video**: Edge-TTS (voice synthesis), FFmpeg (complex video filtergraph & ASS captions)
- **Distribution**: Postiz self-hosted API (port 3000)
- **HITL Interface**: python-telegram-bot v21 (async job-queue)
- **Web Frontend**: Tailwind CSS, Motion animations, Responsive Dashboard

---

## 2. Token & Cost Economics
- **Daily Budget Cap**: Default `$5.00 USD` (configurable via `DAILY_BUDGET_USD`).
- **Token Accounting**: Every LLM invocation records input + output tokens into the `costs` database table.
- **Circuit Breaker**: If total daily spend exceeds `DAILY_BUDGET_USD`, the scheduler automatically halts unapproved pipeline executions to prevent runaway cloud billing.

---

## 3. Resilience & Exponential Backoff
All LLM and external API calls are wrapped with Tenacity exponential backoff:
```python
@retry(
    wait=wait_exponential(multiplier=2, min=2, max=60), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((ResourceExhausted, TooManyRequests))
)
async def generate(prompt: str, model_name: str = None) -> tuple[str, int, float]: ...
```

---

## 4. API Endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Interactive Pipeline Overview & Command Center |
| `/job/{id}` | GET | Stage Timeline, Assets & Cost Breakdown |
| `/analytics` | GET | Cross-channel virality, retention & revenue |
| `/style-guides` | GET | Visual DNA, Hook Formulas & Character Bibles |
| `/api/jobs` | GET | List all active pipeline jobs |
| `/api/jobs/{id}` | GET | Get granular job stage outputs and costs |
| `/api/analytics/summary` | GET | Spend, revenue, and token totals |
| `/api/analytics/posts` | GET | Social post performance metrics |
| `/health` | GET | System health check |
