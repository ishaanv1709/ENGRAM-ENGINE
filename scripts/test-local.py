import asyncio
import os
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
os.environ["ENGRAM_INTEGRATION"] = "1"
raise SystemExit(pytest.main([*(sys.argv[1:] or ["collective/tests"]), "-q", "--tb=short", "-p", "no:cacheprovider"]))
