"""Verify actual selected-provider extraction, correction and graph write-back."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal, register
from collective.db import db, uid
from collective.graph import graph
from collective.memory import memory
from collective.runtime import create_run
from collective.settings import settings

report = {"model": settings.agent_model, "decision_provider": settings.decision_provider}
path = Path("data/collective/live-memory-verification.json")


def record(name, value):
    report[name] = value
    path.write_text(json.dumps(report, indent=2, default=str))
    print(name + ": " + json.dumps(value, default=str), flush=True)


async def main():
    await db.open()
    user = await register(
        f"memory-live-{uid()}@example.test", "Memory-test-password-123", "Memory test", "Live memory test"
    )
    membership = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, membership["tenant_id"], "owner", "Memory test")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Live memory correction')", (project, actor.tenant_id)
    )
    await graph.ensure(actor.tenant_id)
    record("fixture", {"tenant": actor.tenant_id, "project": project})
    first = await memory.ingest(actor, project, "Noor owns project ATLAS.")
    record(
        "initial",
        {"status": first["status"], "facts": [{"id": r["id"], "content": r["content"]} for r in first["facts"]]},
    )
    assert first["facts"], "The selected model produced no initial facts"
    ownership = next(r for r in first["facts"] if "Noor" in r["content"])
    dependent = await create_run(actor, project, "Memory correction dependency fixture", "researcher")
    await graph.depend(actor.tenant_id, dependent["id"], [ownership["id"]])
    corrected = await memory.ingest(
        actor, project, "Correction: Priya now owns project ATLAS, replacing Noor as owner."
    )
    record(
        "correction",
        {
            "status": corrected["status"],
            "facts": [{"id": r["id"], "content": r["content"]} for r in corrected["facts"]],
        },
    )
    records = await memory.list(actor, project)
    active = [r for r in records if r["memory_type"] == "semantic" and r["status"] == "active"]
    old = await memory.get(actor, project, ownership["id"])
    task = await db.execute("SELECT status FROM runs WHERE id=%s", (dependent["id"],), one=True)
    record(
        "write_back",
        {
            "old_status": old["status"],
            "dependent_task_status": task["status"],
            "active_facts": [r["content"] for r in active],
        },
    )
    assert any("Priya" in r["content"] for r in active), "Corrected ownership is not active"
    assert old["status"] in {"superseded", "retracted"}, "Previous ownership remains active"
    assert task["status"] == "stale", "Dependent work was not invalidated"
    record("passed", True)
    await db.pool.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except Exception as exc:
        record(
            "failure",
            {
                "type": type(exc).__name__,
                "detail": str(exc)
                if isinstance(exc, AssertionError)
                else "Provider or pipeline failed; inspect local diagnostics",
            },
        )
        raise
