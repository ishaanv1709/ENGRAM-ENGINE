"""Execute an already verified workflow from a new durable agent session."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from collective.agents import execute_run, heartbeat
from collective.auth import Principal
from collective.db import db
from collective.graph import graph
from collective.memory import memory
from collective.runtime import claim, create_run
from collective.settings import settings
from collective.evidence import verified_check


async def main():
    initial = json.loads(Path("data/collective/live-verification.json").read_text())
    assert initial.get("passed"), "Finish the actual team workflow before testing reuse"
    await db.open()
    fixture = initial["fixture"]
    member = await db.execute("SELECT user_id,role FROM memberships WHERE tenant_id=%s", (fixture["tenant"],), one=True)
    actor = Principal(member["user_id"], fixture["tenant"], member["role"], "Procedure reuse")
    procedures = [
        r
        for r in await memory.list(actor, fixture["project"])
        if r["status"] == "active" and r.get("metadata", {}).get("kind") == "workflow"
    ]
    assert procedures, "There is no independently verified workflow to reuse"
    procedure = max(procedures, key=lambda item: item.get("metadata", {}).get("version", 0))
    artifacts = procedure.get("metadata", {}).get("artifact_manifest") or initial["workflow"]["artifacts"]
    run = await create_run(
        actor,
        fixture["project"],
        f"Reuse the already active verified procedure {procedure['id']} in this NEW session. "
        "Retrieve procedural memory and read this exact procedure with memory_read. Follow its preconditions and steps. "
        f"The existing published source files are {json.dumps(artifacts)}. Copy calculator.py and test_calculator.py "
        "into your own sandbox using artifact_read, execute pytest independently, and report real check_event_ids. "
        "Do not propose or activate a procedure; this task tests reuse of the existing verified one.",
        "verifier",
    )
    leased = await claim("procedure-reuse-verification", actor.tenant_id)
    assert leased and leased["id"] == run["id"], "Unexpected queued fixture work; finish or cancel earlier tests first"
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    execution = asyncio.create_task(execute_run(leased, saver))
    pulse = asyncio.create_task(heartbeat(leased, execution))
    try:
        await execution
    finally:
        pulse.cancel()
        await asyncio.gather(pulse, return_exceptions=True)
    completed = await db.execute("SELECT status,result FROM runs WHERE id=%s", (run["id"],), one=True)
    dependencies = await graph.query(
        actor.tenant_id, "MATCH (t:Task {id:$id})-[:DEPENDS_ON]->(m:Memory) RETURN m.id", {"id": run["id"]}
    )
    checks = await db.execute("SELECT id,payload FROM events WHERE run_id=%s AND kind='tool.executed'", (run["id"],))
    report = {
        "model": settings.agent_model,
        "run_id": run["id"],
        "procedure_id": procedure["id"],
        "status": completed["status"],
        "checks": checks,
        "retrieved_procedure": [procedure["id"]] in dependencies,
        "reuse_metrics": await db.execute("SELECT metrics,completed_at FROM procedure_uses WHERE procedure_id=%s AND run_id=%s", (procedure["id"], run["id"]), one=True),
    }
    report["passed"] = (
        completed["status"] == "completed"
        and report["retrieved_procedure"]
        and any(verified_check(c["payload"]) for c in checks)
        and bool(report["reuse_metrics"] and report["reuse_metrics"]["completed_at"])
    )
    Path("data/collective/reuse-verification.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, default=str), flush=True)
    await db.execute(
        "UPDATE runs SET status='cancelled',revision=revision+1 WHERE tenant_id=%s AND role='curator' AND status='queued' AND objective LIKE %s",
        (actor.tenant_id, f"Consolidate the outcome of task {run['id']}%"),
    )
    assert report["passed"], "A later session did not actually retrieve and successfully execute the verified procedure"
    await db.pool.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
