"""Exercise real Groq builder/verifier handoffs while local Kev downloads."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from collective.agents import execute_run, heartbeat
from collective.auth import Principal, register
from collective.db import db, uid
from collective.graph import graph
from collective.memory import agent_run, memory
from collective.runtime import claim, create_run


async def main():
    await db.open()
    user = await register(
        f"artifact-{uid()}@example.test", "Artifact-probe-password-123", "Artifact probe", "Artifact probe"
    )
    row = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, row["tenant_id"], "owner", "Artifact probe")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Live Groq artifacts')", (project, actor.tenant_id)
    )
    await graph.ensure(actor.tenant_id)
    await create_run(
        actor,
        project,
        "Use capability_search to discover sandbox_write, sandbox_execute and artifact_publish. "
        "Write calculator.py with add(a,b) and test_calculator.py that tests add(2,3)==5. "
        "Run python -m pytest -q. Publish both files. Use team_handoff to a verifier, passing the two real artifact IDs, "
        "asking it to independently copy both to its sandbox and execute pytest. "
        "Report actual artifact IDs and successful check_event_ids. Do not ingest new memory in this probe.",
        "builder",
    )
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    for role in ("builder", "verifier"):
        job = await claim("artifact-probe", actor.tenant_id)
        assert job and job["role"] == role
        execution = asyncio.create_task(execute_run(job, saver))
        pulse = asyncio.create_task(heartbeat(job, execution))
        try:
            await execution
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)
        row = await db.execute("SELECT status,result FROM runs WHERE id=%s", (job["id"],), one=True)
        assert row["status"] in ({"waiting", "completed"} if role == "builder" else {"completed"}), row["status"]
        print(role + ": " + json.dumps(row, default=str), flush=True)
    packets = await db.execute("SELECT acknowledged_at FROM handoffs WHERE tenant_id=%s", (actor.tenant_id,))
    assert packets and all(r["acknowledged_at"] for r in packets)
    artifacts = await db.execute("SELECT id,name,sha256 FROM artifacts WHERE tenant_id=%s", (actor.tenant_id,))
    assert len(artifacts) >= 2
    print(
        "PASS: real Groq builder published artifacts and verifier acknowledged handoff and independently checked them",
        flush=True,
    )
    # Leave automatically queued curator work for the full Kev-backed workflow;
    # do not let the background worker execute this partial fixture later.
    await db.execute(
        "UPDATE runs SET status='cancelled' WHERE tenant_id=%s AND status IN ('queued','waiting')", (actor.tenant_id,)
    )
    agent_run.set(None)
    bundle = await memory.context(actor, project, "addition tests")
    assert bundle["memories"]
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
