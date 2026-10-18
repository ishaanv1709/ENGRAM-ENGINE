"""Exact-argument human authorization for workflow MCP effects.

An uncertain external outcome is never retried automatically.
"""

import hashlib
import json

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from psycopg.types.json import Jsonb

from .db import db, uid
from .settings import DependencyUnavailable
from .workflows import access, control


async def request_action(actor, run, tool_name, server, remote_name, arguments):
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > 32000:
        raise ValueError("External action arguments exceed 32 KB")
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    row = await db.execute(
        """INSERT INTO workflow_actions(id,workflow_id,run_id,tool,server_id,server_url,remote_name,arguments,digest)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(run_id,tool,digest) DO UPDATE SET digest=EXCLUDED.digest RETURNING *""",
        (
            uid(),
            run["workflow_id"],
            run["id"],
            tool_name,
            server["id"],
            server["url"],
            remote_name,
            Jsonb(arguments),
            digest,
        ),
        one=True,
    )
    if row["status"] == "completed":
        return row["result"]
    if row["status"] == "rejected":
        raise PermissionError("The human rejected this exact external action")
    if row["status"] in {"executing", "unknown"}:
        raise DependencyUnavailable("External action outcome requires reconciliation; it will not be repeated")
    await control(actor, run["workflow_id"], "pause")
    raise DependencyUnavailable(f"Workflow paused for exact-argument human approval of action {row['id']}")


async def execute_action(actor, workflow_id, action_id, decision):
    wf = await access(actor, workflow_id, True)
    from datetime import datetime, timezone

    if wf["deadline_at"] <= datetime.now(timezone.utc):
        raise HTTPException(409, "Workflow deadline has expired")
    if wf["status"] not in {"paused", "running"}:
        raise HTTPException(409, "Action belongs to a stopped workflow")
    async with db.pool.connection() as conn:
        async with conn.transaction():
            # Serialize approval with pause/cancel so a stale browser response
            # cannot authorize a stopped workflow's pending external effect.
            current = await (
                await conn.execute("SELECT status,deadline_at FROM workflows WHERE id=%s FOR UPDATE", (workflow_id,))
            ).fetchone()
            if current["status"] not in {"paused", "running"} or current["deadline_at"] <= datetime.now(timezone.utc):
                raise HTTPException(409, "Workflow stopped or expired before action authorization")
            row = await (
                await conn.execute(
                    "SELECT * FROM workflow_actions WHERE id=%s AND workflow_id=%s FOR UPDATE", (action_id, workflow_id)
                )
            ).fetchone()
            if not row:
                raise HTTPException(404, "Action unavailable")
            if row["status"] == "completed":
                return row
            if row["status"] != "pending" or decision not in {"execute", "reject"}:
                raise HTTPException(409, "Action cannot be repeated; inspect any uncertain outcome")
            state = "executing" if decision == "execute" else "rejected"
            await conn.execute(
                "UPDATE workflow_actions SET status=%s,approved_by=%s,updated_at=now() WHERE id=%s",
                (state, actor.user_id, action_id),
            )
    if decision == "reject":
        return {"id": action_id, "status": "rejected"}
    try:
        server = await db.execute(
            "SELECT * FROM tool_servers WHERE id=%s AND tenant_id=%s AND enabled=true",
            (row["server_id"], actor.tenant_id),
            one=True,
        )
        if not server or server["url"] != row["server_url"] or row["remote_name"] not in server["allowed_tools"]:
            raise PermissionError("Connection or capability authorization changed")
        from .mcp_registry import validate_url
        from langchain_mcp_adapters.client import MultiServerMCPClient

        await validate_url(server["url"])
        client = MultiServerMCPClient({server["id"]: {"transport": "streamable_http", "url": server["url"]}})
        remote = next((t for t in await client.get_tools() if t.name == row["remote_name"]), None)
        if not remote:
            raise ValueError("Remote capability no longer exists")
        result = jsonable_encoder(await remote.ainvoke(row["arguments"]))
        if len(json.dumps(result).encode()) > 1_000_000:
            raise ValueError("External result exceeds the retained receipt limit; outcome needs reconciliation")
        await db.execute(
            "UPDATE workflow_actions SET status='completed',result=%s,updated_at=now() WHERE id=%s",
            (Jsonb(result), action_id),
        )
        await db.event(
            actor.tenant_id,
            "workflow.action_completed",
            {"workflow_id": workflow_id, "action_id": action_id},
            row["run_id"],
        )
        return {"id": action_id, "status": "completed", "result": result}
    except Exception:
        await db.execute("UPDATE workflow_actions SET status='unknown',updated_at=now() WHERE id=%s", (action_id,))
        raise HTTPException(
            503, "External outcome is uncertain. Inspect the remote system; automatic retry is disabled."
        ) from None
