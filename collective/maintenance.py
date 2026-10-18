import asyncio
import math
from datetime import datetime, timezone

from .db import db
from .graph import graph
from .memory import RATES


async def maintain():
    """Archive low-retention memories while protecting active obligations."""
    await db.execute("DELETE FROM model_reservations WHERE created_at<now()-interval '1 day'")
    projects = await db.execute("SELECT id,tenant_id FROM projects")
    for project in projects:
        records = await graph.list(project["tenant_id"], project["id"], 1000)
        archived = 0
        for record in records:
            if record["status"] != "active" or record["category"] == "pinned" or record["memory_type"] == "procedural":
                continue
            age = max(
                0, (datetime.now(timezone.utc) - datetime.fromisoformat(record["created_at"])).total_seconds() / 86400
            )
            if math.exp(-RATES[record["category"]] * age) >= 0.1:
                continue
            dependencies = await graph.query(
                project["tenant_id"],
                "MATCH (t:Task)-[:DEPENDS_ON]->(m:Memory {id:$id}) RETURN t.id",
                {"id": record["id"]},
            )
            task_ids = [r[0] for r in dependencies]
            if task_ids:
                active = await db.execute(
                    "SELECT id FROM runs WHERE id=ANY(%s) AND status IN ('queued','running','waiting','awaiting_handoff','stale','blocked') LIMIT 1",
                    (task_ids,),
                )
                if active:
                    continue
            record.update(status="archived", revision=record["revision"] + 1)
            await graph.put(project["tenant_id"], record)
            archived += 1
        if archived:
            await db.event(project["tenant_id"], "memory.archived", {"project_id": project["id"], "count": archived})


async def maintenance_loop():
    while True:
        try:
            await maintain()
        except Exception as exc:
            print(f"Memory maintenance failed: {type(exc).__name__}", flush=True)
        await asyncio.sleep(3600)
