"""Resume an interrupted real verifier using its durable checkpoint and artifacts."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from collective.agents import execute_run, heartbeat
from collective.db import db
from collective.runtime import claim


async def main():
    await db.open()
    previous = await db.execute("SELECT * FROM runs WHERE id=%s AND role='verifier'", (sys.argv[1],), one=True)
    assert previous
    await db.execute(
        "UPDATE runs SET status='queued',lease_token=NULL,lease_until=NULL,revision=revision+1 WHERE id=%s",
        (previous["id"],),
    )
    job = await claim("resumed-live-verifier", previous["tenant_id"])
    assert job["id"] == previous["id"]
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    task = asyncio.create_task(execute_run(job, saver))
    pulse = asyncio.create_task(heartbeat(job, task))
    try:
        await task
    finally:
        pulse.cancel()
        await asyncio.gather(pulse, return_exceptions=True)
    row = await db.execute("SELECT status,result FROM runs WHERE id=%s", (job["id"],), one=True)
    assert row["status"] == "completed" and row["result"]["check_event_ids"]
    print("PASS: independent Groq verifier resumed its durable task and executed checks:", row["result"], flush=True)
    await db.execute(
        "UPDATE runs SET status='cancelled' WHERE tenant_id=%s AND status IN ('queued','waiting')", (job["tenant_id"],)
    )
    await db.pool.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
