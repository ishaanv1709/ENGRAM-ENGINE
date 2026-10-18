"""Budgeted model context with durable, revision-checked provenance receipts."""

import hashlib
import json

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .db import db
from .graph import graph
from .model_budget import tokenizer


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def tokens(value):
    return len(tokenizer().encode(serialized(value)))


def current_reference(record):
    return record["status"] == "active" or (record["memory_type"] == "procedural" and record["status"] == "proposed")


def capsule(record):
    """Expose actionable procedure data, not its recursively growing ledger."""
    result = {k: record[k] for k in ("id", "revision", "memory_type", "status", "content")}
    result["source_ids"] = record.get("source_ids", [])
    metadata = record.get("metadata", {})
    if metadata.get("kind") == "workflow":
        result["content"] = serialized({
            k: metadata.get(k) for k in ("name", "version", "description", "preconditions", "steps", "artifact_manifest")
        })
        result["content_is_projection"] = True
        result["full_content_tool"] = "memory_read"
    return result


def pack(records, budget, required=()):
    required = set(required)
    chosen, projections, omitted = [], [], []
    # Required references and pinned instructions have priority over recall.
    ordered = sorted(records, key=lambda r: (r["id"] not in required, r.get("category") != "pinned"))
    for record in ordered:
        projection = capsule(record)
        if tokens([*projections, projection]) > budget:
            if record["id"] in required or record.get("category") == "pinned":
                raise HTTPException(422, "Required memory exceeds the context budget; shorten or split the record")
            omitted.append(record["id"])
            continue
        chosen.append(record)
        projections.append(projection)
    return chosen, projections, omitted


async def consume(actor, project, run_id, records, projections, *, mode, budget, omitted=()):
    """Register consumption under the same memory locks used by correction.

    A correction cannot slip between validating a snapshot and attaching its
    dependency. A stale snapshot fails closed; it is never sent to the model.
    SQL and FalkorDB are still separate stores, not a distributed transaction.
    """
    receipt = {
        "project_id": project,
        "mode": mode,
        "budget_tokens": budget,
        "context_tokens": tokens(projections),
        "source_record_tokens": tokens(records),
        "omitted_count": len(omitted),
        "records": [
            {"id": r["id"], "revision": r["revision"], "status": r["status"],
             "content_sha256": hashlib.sha256(r["content"].encode()).hexdigest()}
            for r in records
        ],
        "capsule_sha256": hashlib.sha256(serialized(projections).encode()).hexdigest(),
    }
    receipt["digest"] = hashlib.sha256(serialized(receipt).encode()).hexdigest()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"context:{run_id}:{receipt['digest']}",))
            task = await (await conn.execute(
                "SELECT user_id,context_scope FROM runs WHERE id=%s AND tenant_id=%s AND project_id=%s",
                (run_id, actor.tenant_id, project),
            )).fetchone()
            if not task or task["user_id"] != actor.user_id:
                raise HTTPException(404, "Task context unavailable")
            for record in sorted(records, key=lambda r: r["id"]):
                await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (actor.tenant_id + record["id"],))
                current = await graph.get(actor.tenant_id, record["id"])
                if not current or current["revision"] != record["revision"] or current["status"] != record["status"]:
                    raise HTTPException(409, "Memory changed during context preparation; reload current evidence")
                if task["context_scope"] == "team" and record["visibility"] != "team":
                    raise HTTPException(404, "Memory unavailable in shared-only context")
            await graph.depend(actor.tenant_id, run_id, [r["id"] for r in records])
            if any(r["visibility"] != "team" for r in records):
                await conn.execute("UPDATE runs SET visibility='user' WHERE id=%s", (run_id,))
            existing = await (await conn.execute(
                "SELECT id FROM events WHERE run_id=%s AND kind='memory.context' AND payload->>'digest'=%s LIMIT 1",
                (run_id, receipt["digest"]),
            )).fetchone()
            if existing:
                receipt["event_id"] = existing["id"]
            else:
                event = await (await conn.execute(
                    "INSERT INTO events(tenant_id,run_id,kind,payload) VALUES (%s,%s,'memory.context',%s) RETURNING id",
                    (actor.tenant_id, run_id, Jsonb(receipt)),
                )).fetchone()
                receipt["event_id"] = event["id"]
    return receipt
