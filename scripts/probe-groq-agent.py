"""Small real DeepAgents compatibility probe; no decision-model substitute."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collective.agents import execute_run
from collective.auth import Principal, register
from collective.db import db, uid
from collective.graph import graph
from collective.memory import memory
from collective.runtime import claim, create_run
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def main():
    await db.open()
    user = await register(f"groq-{uid()}@example.test", "Real-provider-probe-password-123", "Groq probe", "Live probe")
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, member["tenant_id"], "owner", "Groq probe")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Real Groq probe')", (project, actor.tenant_id)
    )
    await graph.ensure(actor.tenant_id)
    fact = await memory.commit(actor, project, "Maya owns project ORCHID.", memory_type="semantic")
    await create_run(
        actor,
        project,
        "Use memory_search to identify the owner of project ORCHID. State the owner's name explicitly and cite the actual memory evidence ID. "
        "Do not write memory or search the web; this probe checks existing memory retrieval.",
        "researcher",
    )
    run = await claim("groq-probe", actor.tenant_id)
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    try:
        await execute_run(run, saver)
        result = await db.execute("SELECT status,result FROM runs WHERE id=%s", (run["id"],), one=True)
        assert result["status"] == "completed"
        assert "Maya" in result["result"]["summary"]
        assert fact["id"] in result["result"]["evidence_ids"]
        print(
            "PASS: actual DeepAgent used Groq tools, retrieved sourced memory, and persisted its completion", flush=True
        )
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
