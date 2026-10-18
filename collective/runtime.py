from datetime import datetime, timezone
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .auth import Principal
from .db import db, uid
from .evidence import is_test_command
from .graph import graph
from .settings import settings

ROLES = {"coordinator", "researcher", "builder", "verifier", "curator"}


async def create_run(
    actor,
    project,
    objective,
    role="coordinator",
    parent=None,
    dependencies=None,
    conversation=None,
    context_scope=None,
    workflow_id=None,
    workflow_step_id=None,
    profile=None,
    run_id=None,
    auto_curate=True,
    memory_ids=None,
    initial_status="queued",
    initial_visibility=None,
):
    if initial_visibility not in {None, "team", "user"}:
        raise ValueError("Unsupported initial task visibility")
    reference_visibility = initial_visibility or "team"
    if initial_status not in {"queued", "awaiting_handoff"}:
        raise ValueError("Unsupported initial task state")
    if memory_ids is not None:
        if len(memory_ids) > 32:
            raise HTTPException(422, "At most 32 explicit memory references are allowed")
        from .memory import memory
        from .context_passports import current_reference
        for memory_id in set(memory_ids):
            record = await memory.get(actor, project, memory_id)
            if not current_reference(record):
                raise HTTPException(409, "A bound memory is no longer current; bind its replacement before starting work")
            if record["visibility"] != "team":
                reference_visibility = "user"
            if context_scope == "team" and record["visibility"] != "team":
                raise HTTPException(404, "Memory unavailable in shared-only context")
    actor.write()
    if role not in ROLES:
        raise HTTPException(422, "Unknown agent role")
    parent_row = None
    depth = 0
    if parent:
        parent_row = await db.execute(
            "SELECT * FROM runs WHERE id=%s AND tenant_id=%s AND project_id=%s AND (visibility='team' OR user_id=%s)",
            (parent, actor.tenant_id, project, actor.user_id),
            one=True,
        )
        if not parent_row:
            raise HTTPException(404, "Parent task unavailable")
        if parent_row["visibility"] == "user":
            reference_visibility = "user"
        context_scope = context_scope or parent_row["context_scope"]
        workflow_id = parent_row.get("workflow_id")
        workflow_step_id = parent_row.get("workflow_step_id")
        depth = parent_row.get("depth", 0) + 1
        if parent_row["context_scope"] == "team":
            context_scope = "team"
    if profile:
        if profile["base_role"] != role:
            raise HTTPException(422, "Profile role mismatch")
        if profile["context_scope"] == "team":
            context_scope = "team"
    context_scope = context_scope or "auto"
    if context_scope not in {"auto", "team"}:
        raise HTTPException(422, "Unknown memory context scope")
    if context_scope == "team":
        for memory_id in memory_ids or []:
            record = await memory.get(actor, project, memory_id)
            if record["visibility"] != "team":
                raise HTTPException(404, "Memory unavailable in shared-only context")
    dependencies = dependencies or []
    if dependencies:
        found = await db.execute(
            "SELECT id FROM runs WHERE id=ANY(%s) AND tenant_id=%s AND project_id=%s",
            (dependencies, actor.tenant_id, project),
        )
        if len(found) != len(set(dependencies)):
            raise HTTPException(422, "Dependencies must be existing tasks in the same workspace project")
    identity = run_id or uid()
    if run_id:
        existing = await db.execute("SELECT * FROM runs WHERE id=%s", (identity,), one=True)
        if existing:
            if any(existing[k] != v for k, v in (("tenant_id", actor.tenant_id), ("project_id", project), ("user_id", actor.user_id), ("role", role), ("objective", objective))):
                raise HTTPException(409, "Task identity already belongs to another request")
            await graph.task(actor.tenant_id, existing)
            return existing
    if workflow_id:
        existing = await db.execute(
            "SELECT * FROM runs WHERE id=%s AND tenant_id=%s AND workflow_id=%s",
            (identity, actor.tenant_id, workflow_id),
            one=True,
        )
        if existing:
            await graph.task(actor.tenant_id, existing)
            return existing
    async with db.pool.connection() as conn:
        async with conn.transaction():
            if workflow_id:
                workflow = await (
                    await conn.execute(
                        "SELECT * FROM workflows WHERE id=%s AND tenant_id=%s AND project_id=%s AND user_id=%s FOR UPDATE",
                        (workflow_id, actor.tenant_id, project, actor.user_id),
                    )
                ).fetchone()
                if not workflow or workflow["status"] != "running":
                    raise HTTPException(409, "Workflow is not running")
                count = await (
                    await conn.execute("SELECT count(*) AS n FROM runs WHERE workflow_id=%s", (workflow_id,))
                ).fetchone()
                if count["n"] >= workflow["limits"]["max_tasks"] or depth > workflow["limits"]["max_depth"]:
                    raise HTTPException(409, "Workflow task/depth budget exhausted")
                if workflow["context_scope"] == "team":
                    context_scope = "team"
            elif depth > 6:
                raise HTTPException(409, "Task hierarchy depth exhausted")
            run = await (
                await conn.execute(
                    """INSERT INTO runs(id,tenant_id,project_id,user_id,conversation_id,parent_id,role,objective,depends_on,context_scope,auto_curate,memory_refs,status,visibility)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (
                        identity,
                        actor.tenant_id,
                        project,
                        actor.user_id,
                        conversation,
                        parent,
                        role,
                        objective,
                        dependencies,
                        context_scope,
                        auto_curate,
                        list(dict.fromkeys(memory_ids)) if memory_ids is not None else None,
                        initial_status,
                        reference_visibility,
                    ),
                )
            ).fetchone()
            run = await (
                await conn.execute(
                    "UPDATE runs SET workflow_id=%s,workflow_step_id=%s,agent_profile=%s,depth=%s WHERE id=%s RETURNING *",
                    (workflow_id, workflow_step_id, Jsonb(profile) if profile else None, depth, identity),
                )
            ).fetchone()
    if parent:
        await db.execute(
            "UPDATE runs SET visibility=CASE WHEN visibility='user' THEN 'user' ELSE (SELECT visibility FROM runs WHERE id=%s) END WHERE id=%s", (parent, run["id"])
        )
    await graph.task(actor.tenant_id, run)
    await db.event(
        actor.tenant_id, "task.created", {"task_id": run["id"], "role": role, "objective": objective}, run["id"]
    )
    return run


async def claim(worker, tenant=None):
    token = uid()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            # Serialise the short claim allocation so concurrent workers cannot both
            # observe a free final workflow slot. Execution remains parallel.
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('engram:claim-allocation',0))")
            return await (
                await conn.execute(
                    """WITH next AS (
      SELECT r.id FROM runs r WHERE (r.status='queued' OR (r.status='running' AND r.lease_until<now()))
      AND r.attempt<3 AND (%s::text IS NULL OR r.tenant_id=%s)
      AND (r.workflow_id IS NULL OR EXISTS (
        SELECT 1 FROM workflows w JOIN workflow_steps s ON s.workflow_id=w.id
        WHERE w.id=r.workflow_id AND s.id=r.workflow_step_id AND s.run_id IS NOT NULL
        AND w.status='running' AND w.deadline_at>now()
        AND (SELECT count(*) FROM runs active WHERE active.workflow_id=w.id AND active.status='running' AND active.lease_until>now()) < (w.limits->>'parallel')::int))
      AND NOT EXISTS(SELECT 1 FROM runs d WHERE d.id=ANY(r.depends_on) AND d.status!='completed')
      ORDER BY r.created_at FOR UPDATE SKIP LOCKED LIMIT 1)
      UPDATE runs SET status='running',lease_owner=%s,lease_token=%s,
      lease_until=now()+(%s * interval '1 second'),attempt=attempt+1,updated_at=now()
      FROM next WHERE runs.id=next.id RETURNING runs.*""",
                    (tenant, tenant, worker, token, settings.lease_seconds),
                )
            ).fetchone()


async def alive(run):
    result = await db.execute(
        """UPDATE runs SET lease_until=now()+(%s * interval '1 second') WHERE id=%s AND lease_token=%s AND revision=%s AND status='running'
        AND (workflow_id IS NULL OR EXISTS(SELECT 1 FROM workflows w WHERE w.id=runs.workflow_id AND w.status='running' AND w.deadline_at>now())) RETURNING id""",
        (settings.lease_seconds, run["id"], run["lease_token"], run["revision"]),
        one=True,
    )
    return bool(result)


async def finish(run, status, result=None, error=None):
    row = await db.execute(
        """UPDATE runs SET status=%s,result=%s,error=%s,lease_until=NULL,lease_token=NULL,updated_at=now()
      WHERE id=%s AND lease_token=%s AND revision=%s AND status='running' AND lease_until>now()
      AND (workflow_id IS NULL OR EXISTS (SELECT 1 FROM workflows w WHERE w.id=runs.workflow_id
           AND w.status='running' AND w.deadline_at>now())) RETURNING *""",
        (status, Jsonb(result) if result is not None else None, error, run["id"], run["lease_token"], run["revision"]),
        one=True,
    )
    if not row:
        raise RuntimeError("Task ownership or memory revision changed; late result rejected")
    await graph.task(run["tenant_id"], row)
    await db.event(run["tenant_id"], "task." + status, {"result": result, "error": error}, run["id"])
    return row


def handoff_identity(tenant, source_run, target_role, packet):
    digest = hashlib.sha256(json.dumps({"target": target_role, "packet": packet}, sort_keys=True).encode()).hexdigest()
    return str(uuid5(NAMESPACE_URL, f"engram-handoff:{tenant}:{source_run}:{digest}")), digest


async def acknowledge_handoffs(actor, run, packets):
    """Acknowledge only current evidence; preserve the first durable receipt."""
    from .memory import memory
    for envelope in packets:
        for evidence in envelope["packet"]["evidence"]:
            record = await memory.get(actor, run["project_id"], evidence["id"], run["id"])
            if record["revision"] != evidence["revision"] or record["status"] != "active":
                raise HTTPException(409, "Handoff evidence changed; replan before acknowledging")
        async with db.pool.connection() as conn:
            async with conn.transaction():
                updated = await (await conn.execute(
                    """UPDATE handoffs SET acknowledged_at=now() WHERE id=%s AND tenant_id=%s AND to_run=%s
                    AND acknowledged_at IS NULL AND EXISTS(SELECT 1 FROM runs WHERE id=%s AND revision=%s
                    AND status NOT IN ('stale','failed','cancelled')) RETURNING id""",
                    (envelope["id"], actor.tenant_id, run["id"], run["id"], run["revision"]),
                )).fetchone()
                if updated:
                    await conn.execute("INSERT INTO events(tenant_id,run_id,kind,payload) VALUES (%s,%s,'task.handoff_acknowledged',%s)",
                                       (actor.tenant_id, run["id"], Jsonb({"handoff_id": envelope["id"]})))


async def handoff(actor, run, target_role, checkpoint, evidence_ids, artifact_ids, remaining, check_event_ids=None):
    if target_role not in ROLES or target_role == "coordinator":
        raise HTTPException(422, "Choose a specialist role")
    from .memory import memory

    if not remaining.strip():
        raise HTTPException(
            422,
            "Describe the receiving agent's remaining work. Memory UUIDs belong in evidence_ids; integer test event IDs belong in check_event_ids.",
        )
    check_event_ids = check_event_ids or []
    if check_event_ids:
        checks = await db.execute(
            "SELECT id,payload FROM events WHERE tenant_id=%s AND run_id=%s AND kind='tool.executed' AND id=ANY(%s)",
            (actor.tenant_id, run["id"], check_event_ids),
        )
        if len(checks) != len(set(check_event_ids)) or any(
            not is_test_command(c["payload"].get("command", "")) for c in checks
        ):
            raise HTTPException(422, "Check event IDs must refer to this agent's actual execution events")
    for mid in evidence_ids:
        try:
            await memory.get(actor, run["project_id"], mid, run["id"])
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            raise HTTPException(
                422,
                "evidence_ids accepts accessible memory IDs only. Put integer test event IDs in check_event_ids and published file IDs in artifact_ids; use [] when no memory evidence is needed.",
            ) from None
    if artifact_ids:
        found = await db.execute(
            "SELECT a.id FROM artifacts a LEFT JOIN runs r ON r.id=a.run_id WHERE a.tenant_id=%s AND a.project_id=%s AND a.id=ANY(%s) AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s)",
            (actor.tenant_id, run["project_id"], artifact_ids, actor.user_id),
        )
        if len(found) != len(set(artifact_ids)):
            raise HTTPException(404, "Artifact unavailable")
    packet = {
        "objective": run["objective"],
        "checkpoint": checkpoint,
        "remaining": remaining,
        "evidence": [
            {"id": mid, "revision": (await memory.get(actor, run["project_id"], mid, run["id"]))["revision"]}
            for mid in evidence_ids
        ],
        "artifact_ids": artifact_ids,
        "check_event_ids": check_event_ids,
        "source_run": run["id"],
    }
    identity, digest = handoff_identity(actor.tenant_id, run["id"], target_role, packet)
    async with db.delivery_lock(identity) as conn:
        previous = await (await conn.execute("SELECT to_run FROM handoffs WHERE id=%s AND tenant_id=%s", (identity, actor.tenant_id))).fetchone()
        if previous:
            return await db.execute("SELECT * FROM runs WHERE id=%s", (previous["to_run"],), one=True)
        # A crash here leaves an unclaimable task. Retrying this identical
        # handoff reuses its identity and completes the same envelope.
        destination = await create_run(
            actor, run["project_id"], remaining, target_role, parent=run["parent_id"] or run["id"],
            context_scope=run["context_scope"], memory_ids=evidence_ids,
            run_id=identity, initial_status="awaiting_handoff",
            initial_visibility=(await db.execute("SELECT visibility FROM runs WHERE id=%s", (run["id"],), one=True))["visibility"],
        )
        packet.update(created_at=datetime.now(timezone.utc).isoformat(), digest=digest)
        if destination["visibility"] == "user":
            await conn.execute("UPDATE runs SET visibility='user' WHERE id=%s", (run["id"],))
        await conn.execute(
            "INSERT INTO handoffs(id,tenant_id,from_run,to_run,packet) VALUES (%s,%s,%s,%s,%s)",
            (identity, actor.tenant_id, run["id"], destination["id"], Jsonb(packet)),
        )
        await conn.execute(
            "UPDATE runs SET visibility=CASE WHEN visibility='user' THEN 'user' ELSE (SELECT visibility FROM runs WHERE id=%s) END,status='queued' WHERE id=%s AND status='awaiting_handoff'",
            (run["id"], destination["id"]),
        )
        await conn.execute(
            "INSERT INTO events(tenant_id,run_id,kind,payload) VALUES (%s,%s,'task.handoff',%s)",
            (actor.tenant_id, run["id"], Jsonb({"from": run["id"], "to": destination["id"], "packet": packet})),
        )
    destination = await db.execute("SELECT * FROM runs WHERE id=%s", (identity,), one=True)
    await graph.task(actor.tenant_id, destination)
    return destination


async def actor_for(run):
    row = await db.execute(
        "SELECT u.name,m.role FROM users u JOIN memberships m ON m.user_id=u.id WHERE u.id=%s AND m.tenant_id=%s",
        (run["user_id"], run["tenant_id"]),
        one=True,
    )
    if not row or row["role"] == "viewer":
        raise PermissionError("Task owner no longer has write access")
    return Principal(run["user_id"], run["tenant_id"], row["role"], row["name"])
