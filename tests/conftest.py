import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# pytest-asyncio configuration
pytest_plugins = ["pytest_asyncio"]
