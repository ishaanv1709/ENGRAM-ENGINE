"""Real memory infrastructure evaluation. Never reports an agent-model score."""

import asyncio
import statistics
import time

from psycopg.types.json import Jsonb

from .db import db, uid
from .memory import memory


async def evaluate(actor, project):
    start = time.perf_counter()
    latencies = []

    async def insert(i):
        t = time.perf_counter()
        record = await memory.commit(
            actor,
            project,
            f"Evaluation fixture {uid()}: test-resource-{i} is owned by benchmark-team-{i}.",
            category="temporary",
            memory_type="semantic",
            visibility="user",
            metadata={"kind": "evaluation_fixture"},
        )
        latencies.append((time.perf_counter() - t) * 1000)
        return record

    records = await asyncio.gather(*(insert(i) for i in range(8)))
    recovered = await asyncio.gather(*(memory.get(actor, project, r["id"]) for r in records))
    first = await memory.context(actor, project, records[0]["content"])
    second = await memory.context(actor, project, records[0]["content"])
    report = {
        "kind": "real_memory_infrastructure",
        "concurrent_writers": 8,
        "writes": len(records),
        "unique_ids": len({r["id"] for r in records}),
        "durable_reads_match": all(a["content"] == b["content"] for a, b in zip(records, recovered)),
        "retrieved_target": records[0]["id"] in first["evidence_ids"],
        "cache_hit": second["tier"] == "recent_cache",
        "mean_write_ms": round(statistics.mean(latencies), 2),
        "max_write_ms": round(max(latencies), 2),
        "elapsed_seconds": round(time.perf_counter() - start, 2),
        "agent_model_evaluation": "not_run",
        "fixture_memory_ids": [r["id"] for r in records],
    }
    await db.execute(
        "INSERT INTO evaluations(id,tenant_id,name,result) VALUES (%s,%s,%s,%s)",
        (uid(), actor.tenant_id, "Concurrent memory and cache verification", Jsonb(report)),
    )
    return report
