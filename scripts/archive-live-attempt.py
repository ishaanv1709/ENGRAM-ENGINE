"""Preserve a debug fixture and fence only its unfinished test tasks."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.db import db
from collective.graph import graph


async def main():
    report = json.loads(Path("data/collective/live-verification.json").read_text(encoding="utf-8"))
    fixture = report["fixture"]
    assert fixture["email"].startswith("live-") and fixture["email"].endswith("@example.test")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = Path(f"data/collective/live-debug-{stamp}.json")
    await db.open()
    rows = await db.execute("SELECT * FROM runs WHERE tenant_id=%s", (fixture["tenant"],))
    target.write_text(json.dumps({"report": report, "runs": rows, "reason": "Preserve debug fixture before a clean demo with corrected completion controls"}, indent=2, default=str), encoding="utf-8")
    cancelled = await db.execute("UPDATE runs SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE tenant_id=%s AND status IN ('queued','running','waiting','blocked','failed') RETURNING *", (fixture["tenant"],))
    for run in cancelled:
        await graph.task(fixture["tenant"], run)
        await db.event(fixture["tenant"], "task.cancelled", {"reason": "Debug fixture archived before clean demo", "archive": str(target)}, run["id"])
    print(json.dumps({"archive": str(target), "fenced_test_tasks": len(cancelled)}))
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
