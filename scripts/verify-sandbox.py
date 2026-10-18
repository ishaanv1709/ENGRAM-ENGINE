"""Run the existing real isolation probes without inference or a benchmark rerun."""
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("showcase_probe", root / "scripts/measure-showcase.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


async def main():
    result = await module.container_probes()
    first, second = module.Sandbox(module.uid()), module.Sandbox(module.uid())
    try:
        await first.start()
        await second.start()
        await first.write("private.txt", "First run only")
        isolated = await second.execute("test ! -e /workspace/private.txt")
        assert isolated["exit_code"] == 0, "A separate run saw another workspace's file"
        await second.write("private.txt", "Second run only")
        assert await first.read("private.txt") == b"First run only"
        assert await second.read("private.txt") == b"Second run only"
        result["separate_run_workspaces"] = {"passed": True, "first_run": first.run_id, "second_run": second.run_id}
    finally:
        await first.close()
        await second.close()
    result["verified_at"] = datetime.now(timezone.utc).isoformat()
    destination = root / "data/collective/sandbox-verification-latest.json"
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "controls": result["inspected_controls"],
        "behavior": result["behavior"], "path_denials": result["path_denials"], "separate_workspaces": result["separate_run_workspaces"]["passed"], "report": str(destination)}))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
