"""Retain a debug comparison, cancel only its live runs and permit a fresh pair."""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from collective.db import db

ROOT = Path("data/collective/submission-live-2026-10-18")


async def main(reason):
    await db.open()
    try:
        path = ROOT / "report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        comparison = report["comparison"]
        ids = [comparison[k] for k in ("baseline_run", "reuse_run") if k in comparison]
        runs = await db.execute("SELECT id,status,role,error FROM runs WHERE id=ANY(%s)", (ids,))
        events = await db.execute(
            "SELECT id,run_id,kind,payload,created_at FROM events WHERE run_id=ANY(%s) ORDER BY id", (ids,)
        )
        report.setdefault("excluded_comparison_pilots", []).append(
            {"comparison": comparison, "reason": reason, "runs": runs, "events": events}
        )
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8088/api",
            headers={"X-Engram-Request": "1"},
            cookies=json.loads((ROOT / "session.json").read_text()),
        ) as client:
            for run in runs:
                if run["status"] in {"queued", "running", "waiting"}:
                    (await client.post(f"/runs/{run['id']}/cancel")).raise_for_status()
        report.pop("comparison")
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"archived_runs": ids, "events_retained": len(events)}))
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(sys.argv[1]))
