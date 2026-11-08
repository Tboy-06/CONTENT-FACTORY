#!/usr/bin/env python3
"""
CONTENT-FACTORY Backend Runner
Usage: python backend/run.py
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

import uvicorn

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import get_settings
from backend.main import app

settings = get_settings()


def main() -> None:
    """Run the backend server."""
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    CONTENT-FACTORY v1.0.0                       ║
║         Multi-agent AI content automation pipeline             ║
╠══════════════════════════════════════════════════════════════╣
║  Backend: http://{host}:{port}                                       ║
║  Health:  http://{host}:{port}/health                                  ║
║  Docs:    http://{host}:{port}/docs                                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print("\nShutdown signal received...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=settings.log_level == "DEBUG",
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()