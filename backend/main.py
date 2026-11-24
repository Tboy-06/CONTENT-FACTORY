from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from typing import AsyncGenerator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.config import get_settings
from backend.scheduler import init_scheduler, shutdown_scheduler
from backend.telegram_bot import start_bot, stop_bot
from backend.api.copilot import router as copilot_router
from backend.api.jobs import router as jobs_router, get_cache_status, clear_cache
from backend.api.workflow import router as workflow_router
from backend.api.settings import router as settings_router

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting CONTENT-FACTORY backend...")

    # Initialize scheduler
    await init_scheduler()

    # Start Telegram bot
    if settings.telegram_bot_token:
        try:
            await start_bot()
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")

    logger.info("CONTENT-FACTORY backend started successfully")
    yield

    logger.info("Shutting down CONTENT-FACTORY backend...")
    await shutdown_scheduler()
    if settings.telegram_bot_token:
        try:
            await stop_bot()
        except Exception as e:
            logger.error(f"Failed to stop bot: {e}")
    try:
        from backend.engine.brain import shutdown_local_brain
        shutdown_local_brain()
    except Exception as e:
        logger.error(f"Failed to stop local brain subprocess: {e}")
    logger.info("CONTENT-FACTORY backend stopped")


app = FastAPI(
    title="CONTENT-FACTORY",
    description="Multi-agent AI content automation pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(copilot_router, prefix="/api/copilot", tags=["copilot"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(workflow_router, prefix="/api/workflow", tags=["workflow"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])

app.add_api_route("/api/system/cache", get_cache_status, methods=["GET"], tags=["system"])
app.add_api_route("/api/system/cache/clear", clear_cache, methods=["POST"], tags=["system"])

import shutil

JOBS_SCRATCH_ROOT = r"C:\cf_training\jobs"
os.makedirs("output", exist_ok=True)
os.makedirs("temp", exist_ok=True)
os.makedirs(JOBS_SCRATCH_ROOT, exist_ok=True)

# Migrate any existing D:\CONTENT-FACTORY\jobs\<id> folders to C:\cf_training\jobs\<id> to keep D: free
if os.path.exists("jobs"):
    try:
        for entry in os.listdir("jobs"):
            src_j = os.path.join("jobs", entry)
            dst_j = os.path.join(JOBS_SCRATCH_ROOT, entry)
            if os.path.isdir(src_j):
                if not os.path.exists(dst_j):
                    shutil.move(src_j, dst_j)
                else:
                    shutil.copytree(src_j, dst_j, dirs_exist_ok=True)
                    shutil.rmtree(src_j, ignore_errors=True)
    except Exception as _mig_err:
        logger.warning(f"Could not migrate legacy D:\\jobs folder: {_mig_err}")

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/temp", StaticFiles(directory="temp"), name="temp")
app.mount("/jobs", StaticFiles(directory=JOBS_SCRATCH_ROOT), name="jobs")

@app.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "content-factory"})

@app.get("/v1/models")
async def list_models() -> JSONResponse:
    return JSONResponse({
        "object": "list",
        "data": [
            {"id": "models/gemini-3.8-flash", "object": "model", "owned_by": "google"},
            {"id": "models/gemini-3.6-flash", "object": "model", "owned_by": "google"},
            {"id": "models/gemini-3.5-flash-lite", "object": "model", "owned_by": "google"},
            {"id": "spark-x2.5-4b", "object": "model", "owned_by": "local"}
        ]
    })

@app.get("/api/health")
async def api_health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"})

@app.get("/api/capabilities")
async def get_capabilities() -> JSONResponse:
    return JSONResponse([
        {"stage": "Research", "offline": "Cached", "free": "Web", "premium": "Web"},
        {"stage": "Script", "offline": "Local Llama3", "free": "Gemini Flash", "premium": "GPT-4o"},
        {"stage": "Visuals", "offline": "Local stock", "free": "Pexels", "premium": "DALL-E 3"},
        {"stage": "Voice", "offline": "Local TTS", "free": "Free TTS", "premium": "ElevenLabs"},
        {"stage": "Render", "offline": "FFmpeg", "free": "FFmpeg", "premium": "Cloud render"}
    ])


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "CONTENT-FACTORY",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)