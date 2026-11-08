import asyncio
import os
import sys
import logging
from contextlib import asynccontextmanager
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("content_factory.main")

from dashboard.main import app as fastapi_app
from backend.telegram_bot.bot import bot_app
from backend.scheduler import scheduler
from backend.vault.repository import init_db
from backend.config import settings

@asynccontextmanager
async def lifespan(app):
    logger.info("Initializing CONTENT-FACTORY Vault Database...")
    await init_db()
    
    logger.info("Starting APScheduler (5 background cron/interval workers)...")
    try:
        scheduler.start()
    except Exception as e:
        logger.warning(f"Scheduler already started or error: {e}")
    
    # Start Telegram Bot if token configured
    bot_started = False
    if settings.telegram_bot_token and settings.telegram_bot_token != "test_token":
        try:
            logger.info("Initializing Telegram HITL Bot...")
            await bot_app.initialize()
            await bot_app.start()
            if bot_app.updater:
                await bot_app.updater.start_polling()
            bot_started = True
            logger.info("Telegram Bot successfully polling for HITL commands.")
        except Exception as e:
            logger.warning(f"Telegram Bot polling skipped or simulated: {e}")
    else:
        logger.info("Telegram Bot running in simulated HITL test mode.")
    
    yield
    
    # Graceful Shutdown
    logger.info("Shutting down CONTENT-FACTORY services...")
    if bot_started:
        try:
            if bot_app.updater:
                await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception as e:
            logger.warning(f"Error during bot shutdown: {e}")
    
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    logger.info("Shutdown complete.")

fastapi_app.router.lifespan_context = lifespan

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    logger.info(f"Starting CONTENT-FACTORY on http://{host}:{port}")
    uvicorn.run("run_backend:fastapi_app", host=host, port=port, reload=False)
