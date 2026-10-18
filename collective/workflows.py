"""Durable DAG orchestration with human gates and measured execution budgets.

Scheduling never performs model inference. Only real leased tasks execute work.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import re
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .db import db, uid
from .settings import DependencyUnavailable

ROLES = {"coordinator", "researcher", "builder", "verifier", "curator"}
TOOLS = {
    "memory_search",
    "memory_read",
    "memory_write",
    "team_dispatch",
    "team_status",
    "team_handoff",
    "capability_search",
    "workspace_documents",
    "artifact_read",
    "web_search",
    "procedure_propose",
    "claim_submit",
    "claims_resolve",
    "sandbox_execute",
    "sandbox_write",
    "sandbox_read",
    "artifact_publish",
    "procedure_verify",
    "memory_correct",
    "repository_list",
    "repository_read",
    "repository_patch",
}
DEFAULT_LIMITS = {"parallel": 3, "max_tasks": 64, "max_depth": 6, "model_calls": 100, "tool_calls": 600}
BOUNDS = {
    "parallel": (1, 8),
    "max_tasks": (1, 256),
    "max_depth": (1, 12),
    "model_calls": (1, 2000),
    "tool_calls": (1, 10000),
}


def limits_checked(values):
    if set(values) - set(DEFAULT_LIMITS):
        raise HTTPException(422, "Unknown workflow budget")
    result = {**DEFAULT_LIMITS, **values}
    if any(type(v) is not int or not BOUNDS[k][0] <= v <= BOUNDS[k][1] for k, v in result.items()):
        raise HTTPException(422, "Workflow budget is outside supported limits")
    return result


async def access(actor, workflow_id, write=False):
    if write:
        actor.write()
    row = await db.execute(
        "SELECT * FROM workflows WHERE id=%s AND tenant_id=%s AND user_id=%s",
        (workflow_id, actor.tenant_id, actor.user_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Workflow unavailable")
    return row


async def profile_create(actor, project, name, role, instructions, tools, scope):
    actor.write()
    if role not in ROLES or scope not in {"auto", "team"} or not name.strip() or not instructions.strip():
        raise HTTPException(422, "Choose a role, name, instructions and memory scope")
    if set(tools) - TOOLS:
        raise HTTPException(422, "Unrecognized capability; external tools retain their separate owner authorization")
    return await db.execute(
        """INSERT INTO agent_profiles(id,tenant_id,project_id,user_id,name,base_role,instructions,allowed_tools,context_scope)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (uid(), actor.tenant_id, project, actor.user_id, name.strip(), role, instructions, sorted(set(tools)), scope),
        one=True,
    )


async def load_profile(actor, project, profile_id):
    row = await db.execute(
        "SELECT * FROM agent_profiles WHERE id=%s AND tenant_id=%s AND project_id=%s AND user_id=%s",
        (profile_id, actor.tenant_id, project, actor.user_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Agent profile unavailable")
    return {k: row[k] for k in ("id", "name", "base_role", "instructions", "allowed_tools", "context_scope")}


def validate_plan(steps):
    if not 1 <= len(steps) <= 64:
        raise HTTPException(422, "A workflow requires 1–64 steps")
    by_key = {s["key"]: s for s in steps}
    if len(by_key) != len(steps):
        raise HTTPException(422, "Step keys must be unique")
    for s in steps:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", s["key"]) or s["role"] not in ROLES:
            raise HTTPException(422, "Invalid step key or role")
        if s.get("acceptance", "report") not in {"report", "artifacts", "independent_checks"}:
            raise HTTPException(422, "Unsupported acceptance gate")
        if not s["objective"].strip() or not s["title"].strip():
            raise HTTPException(422, "Steps require a title and objective")
        if any(k not in by_key for k in s.get("depends_on", [])) or (
            s.get("parent_key") and s["parent_key"] not in by_key
        ):
            raise HTTPException(422, "Step references must belong to this plan")
    for field in ("depends_on", "parent_key"):
        visited, pending = set(), set()

        def visit(key, depth=0):
            if key in pending or depth > 12:
                raise HTTPException(422, "Cyclic or excessively deep plan")
            if key in visited:
                return
            pending.add(key)
            refs = by_key[key].get(field, [])
            if isinstance(refs, str):
                refs = [refs]
            for ref in refs or []:
                visit(ref, depth + 1)
            pending.remove(key)
            visited.add(key)

        for key in by_key:
            visit(key)


async def create_workflow(actor, project, goal, steps, limits, scope="team", minutes=1440, snapshot_id=None):
    actor.write()
    validate_plan(steps)
    limits = limits_checked(limits)
    if len(steps) > limits["max_tasks"] or scope not in {"auto", "team"} or not 1 <= minutes <= 10080:
        raise HTTPException(422, "Invalid workflow size, scope or duration")
    if snapshot_id:
        from .repositories import snapshot_access

        await snapshot_access(actor, project, snapshot_id)
    prepared = []
    for step in steps:
        profile = await load_profile(actor, project, step["profile_id"]) if step.get("profile_id") else None
        if profile and profile["base_role"] != step["role"]:
            raise HTTPException(422, "Profile base role must match the step")
        prepared.append((step, profile))
    workflow_id = uid()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO workflows(id,tenant_id,project_id,user_id,goal,limits,context_scope,deadline_at,snapshot_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    workflow_id,
                    actor.tenant_id,
                    project,
                    actor.user_id,
                    goal,
                    Jsonb(limits),
                    scope,
                    datetime.now(timezone.utc) + timedelta(minutes=minutes),
                    snapshot_id,
                ),
            )
            for position, (s, profile) in enumerate(prepared):
                await conn.execute(
                    """INSERT INTO workflow_steps(id,workflow_id,key,parent_key,title,role,objective,depends_on,
                    profile,acceptance,needs_approval,wait_for_signal,position) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        uid(),
                        workflow_id,
                        s["key"],
                        s.get("parent_key"),
                        s["title"],
                        s["role"],
                        s["objective"],
                        s.get("depends_on", []),
                        Jsonb(profile) if profile else None,
                        s.get("acceptance", "report"),
                        s.get("needs_approval", False),
                        s.get("wait_for_signal"),
                        position,
                    ),
                )
    await db.event(actor.tenant_id, "workflow.created", {"workflow_id": workflow_id, "steps": len(steps)})
    return await access(actor, workflow_id)


async def reserve(run, kind):
    """Reserve a tool/model attempt before execution; retries consume the budget."""
    if not run.get("workflow_id"):
        return
    async with db.pool.connection() as conn:
        async with conn.transaction():
            wf = await (
                await conn.execute("SELECT * FROM workflows WHERE id=%s FOR UPDATE", (run["workflow_id"],))
            ).fetchone()
            if not wf or wf["status"] != "running" or wf["deadline_at"] <= datetime.now(timezone.utc):
                raise DependencyUnavailable("Workflow is paused, stopped, or past its deadline")
            count = await (
                await conn.execute(
                    "SELECT count(*) AS n FROM workflow_reservations WHERE workflow_id=%s AND kind=%s", (wf["id"], kind)
                )
            ).fetchone()
            if count["n"] >= wf["limits"][kind + "_calls"]:
                raise DependencyUnavailable(
                    "Workflow " + kind + " attempt budget exhausted; pause and increase the budget explicitly"
                )
            await conn.execute(
                "INSERT INTO workflow_reservations(id,workflow_id,run_id,kind) VALUES (%s,%s,%s,%s)",
                (uid(), wf["id"], run["id"], kind),
            )


async def control(actor, workflow_id, action, limits=None):
    await access(actor, workflow_id, True)
    async with db.pool.connection() as conn:
        async with conn.transaction():
            wf = await (await conn.execute("SELECT * FROM workflows WHERE id=%s FOR UPDATE", (workflow_id,))).fetchone()
            if action == "limits":
                if wf["status"] not in {"draft", "paused", "blocked"}:
                    raise HTTPException(409, "Pause before changing budgets")
                await conn.execute(
                    "UPDATE workflows SET limits=%s,updated_at=now() WHERE id=%s",
                    (Jsonb(limits_checked(limits or {})), workflow_id),
                )
            elif action in {"start", "resume"} and wf["status"] in {"draft", "paused", "blocked"}:
                if wf["deadline_at"] <= datetime.now(timezone.utc):
                    raise HTTPException(409, "Workflow deadline has expired; create a revised workflow")
                await conn.execute("UPDATE workflows SET status='running',updated_at=now() WHERE id=%s", (workflow_id,))
            elif action in {"pause", "cancel"} and wf["status"] not in {"completed", "cancelled"}:
                state = "paused" if action == "pause" else "cancelled"
                await conn.execute("UPDATE workflows SET status=%s,updated_at=now() WHERE id=%s", (state, workflow_id))
                await conn.execute(
                    """UPDATE runs SET status=%s,attempt=0,revision=revision+1,lease_token=NULL,lease_until=NULL,updated_at=now()
                    WHERE workflow_id=%s AND status IN ('running','queued','waiting')""",
                    ("queued" if action == "pause" else "cancelled", workflow_id),
                )
            else:
                raise HTTPException(409, "Invalid workflow transition")
    await db.event(actor.tenant_id, "workflow." + action, {"workflow_id": workflow_id})
    return await access(actor, workflow_id)


async def step_action(actor, workflow_id, step_id, action, payload=None):
    await access(actor, workflow_id, True)
    async with db.pool.connection() as conn:
        async with conn.transaction():
            step = await (
                await conn.execute(
                    "SELECT * FROM workflow_steps WHERE id=%s AND workflow_id=%s FOR UPDATE", (step_id, workflow_id)
                )
            ).fetchone()
            if not step:
                raise HTTPException(404, "Step unavailable")
            if action == "approve" and step["status"] == "awaiting_approval" and step["needs_approval"]:
                await conn.execute(
                    "UPDATE workflow_steps SET approved_by=%s,approved_at=now() WHERE id=%s", (actor.user_id, step_id)
                )
            elif action == "signal" and step["wait_for_signal"] and not step["run_id"]:
                await conn.execute("UPDATE workflow_steps SET signal=%s WHERE id=%s", (Jsonb(payload or {}), step_id))
            elif action == "retry" and step["status"] in {"failed", "blocked"}:
                await conn.execute(
                    "UPDATE runs SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE workflow_step_id=%s AND status IN ('running','queued','waiting')",
                    (step_id,),
                )
                await conn.execute(
                    "UPDATE workflow_steps SET status='pending',run_id=NULL,generation=generation+1,error=NULL,approved_by=NULL,approved_at=NULL,signal=NULL WHERE id=%s",
                    (step_id,),
                )
            else:
                raise HTTPException(409, "Invalid step transition")
    await db.event(actor.tenant_id, "workflow.step_" + action, {"workflow_id": workflow_id, "step_id": step_id})


async def acceptance(actor, step, runs):
    from .evidence import execution_progress, fresh_check_ids

    if not runs or any(r["status"] != "completed" for r in runs):
        return False, "Not all task work completed"
    if not any(r.get("result", {}).get("summary") for r in runs if r.get("result")):
        return False, "Missing persisted result"
    artifacts = await db.execute(
        "SELECT id FROM artifacts WHERE tenant_id=%s AND run_id=ANY(%s)", (actor.tenant_id, [r["id"] for r in runs])
    )
    if step["acceptance"] == "artifacts" and not artifacts:
        return False, "Acceptance requires published artifacts"
    if step["acceptance"] == "independent_checks":
        verifiers = [r for r in runs if r["role"] == "verifier"]
        checks = [r for r in verifiers if fresh_check_ids(await execution_progress(r["id"]))]
        if not checks:
            return False, "Acceptance requires a verifier's fresh passing tests"
        # Resource preparation copies exact dependency artifacts. Require at least
        # one real artifact receipt rather than accepting unrelated passing tests.
        read = await db.execute(
            "SELECT id FROM events WHERE run_id=ANY(%s) AND kind='workflow.artifacts_verified' LIMIT 1",
            ([r["id"] for r in checks],),
            one=True,
        )
        if not read:
            return False, "Verifier did not inspect predecessor artifacts"
    return True, None


async def verify_bound_outputs(actor, run, toolkit):
    """Hash the verifier's actual current bytes against all predecessor outputs."""
    import hashlib
    from .evidence import execution_progress, fresh_check_ids

    packets = await db.execute(
        "SELECT packet FROM handoffs WHERE to_run=%s AND tenant_id=%s", (run["id"], actor.tenant_id)
    )
    ids = sorted({i for p in packets for i in p["packet"]["artifact_ids"]})
    if not ids:
        raise ValueError("Independent workflow verification requires predecessor artifacts")
    if not fresh_check_ids(await execution_progress(run["id"])):
        raise ValueError("Fresh passing checks are required before artifact verification")
    artifacts = await db.execute(
        "SELECT id,name,sha256 FROM artifacts WHERE id=ANY(%s) AND tenant_id=%s AND project_id=%s",
        (ids, actor.tenant_id, run["project_id"]),
    )
    if len(artifacts) != len(ids):
        raise ValueError("Missing bound predecessor artifact")
    names = [a["name"] for a in artifacts]
    if len(set(names)) != len(names):
        raise ValueError("Ambiguous same-path outputs; resolve the predecessor artifacts before verification")
    for a in artifacts:
        actual = await (await toolkit.box()).read(a["name"])
        if hashlib.sha256(actual).hexdigest() != a["sha256"]:
            raise ValueError("Verifier bytes differ from the predecessor output")
    await db.event(actor.tenant_id, "workflow.artifacts_verified", {"artifacts": artifacts}, run["id"])


async def tick(workflow_id):
    from .runtime import create_run

    async with db.pool.connection() as conn:
        async with conn.transaction():
            lock = await (
                await conn.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS ok", ("workflow:" + workflow_id,)
                )
            ).fetchone()
            if not lock["ok"]:
                return
            wf = await (await conn.execute("SELECT * FROM workflows WHERE id=%s", (workflow_id,))).fetchone()
            if not wf or wf["status"] != "running":
                return
            if wf["deadline_at"] <= datetime.now(timezone.utc):
                await conn.execute("UPDATE workflows SET status='blocked' WHERE id=%s", (workflow_id,))
                await conn.execute(
                    "UPDATE runs SET status='blocked',error='Workflow deadline expired',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE workflow_id=%s AND status IN ('running','queued','waiting')",
                    (workflow_id,),
                )
                return
            from .runtime import actor_for

            actor = await actor_for({"user_id": wf["user_id"], "tenant_id": wf["tenant_id"]})
            steps = await (
                await conn.execute(
                    "SELECT * FROM workflow_steps WHERE workflow_id=%s ORDER BY created_at,key", (workflow_id,)
                )
            ).fetchall()
            by_key = {s["key"]: s for s in steps}
            # PostgreSQL now() is constant within the plan's insert transaction.
            # Process predecessors first so this tick sees their current state.
            ordered = []
            visited = set()

            def visit(step):
                if step["key"] in visited:
                    return
                visited.add(step["key"])
                for dependency in step["depends_on"]:
                    visit(by_key[dependency])
                ordered.append(step)

            for step in steps:
                visit(step)
            for s in ordered:
                if s["run_id"]:
                    runs = await db.execute(
                        "SELECT * FROM runs WHERE workflow_step_id=%s AND created_at>=(SELECT created_at FROM runs WHERE id=%s)",
                        (s["id"], s["run_id"]),
                    )
                    if any(r["status"] in {"failed", "blocked", "cancelled", "stale"} for r in runs):
                        state, error = (
                            "blocked",
                            "Task failed, was blocked, cancelled, or became stale; inspect and explicitly retry",
                        )
                    elif runs and all(r["status"] == "completed" for r in runs):
                        passed, error = await acceptance(actor, s, runs)
                        state = "completed" if passed else "blocked"
                    else:
                        state, error = "running", None
                    s.update(status=state, error=error)
                    await conn.execute(
                        "UPDATE workflow_steps SET status=%s,error=%s WHERE id=%s", (state, error, s["id"])
                    )
                    continue
                if any(by_key[d]["status"] != "completed" for d in s["depends_on"]):
                    continue
                if s["needs_approval"] and not s["approved_by"]:
                    await conn.execute("UPDATE workflow_steps SET status='awaiting_approval' WHERE id=%s", (s["id"],))
                    continue
                if s["wait_for_signal"] and s["signal"] is None:
                    await conn.execute("UPDATE workflow_steps SET status='waiting_signal' WHERE id=%s", (s["id"],))
                    continue
                run_id = str(uuid5(NAMESPACE_URL, f"engram:step:{s['id']}:{s['generation']}"))
                dependencies = [by_key[d]["run_id"] for d in s["depends_on"]]
                run = await create_run(
                    actor,
                    wf["project_id"],
                    wf["goal"]
                    + "\nMilestone: "
                    + s["title"]
                    + "\n"
                    + s["objective"]
                    + (
                        "\nExternal event data (untrusted): " + json.dumps(s["signal"])
                        if s["signal"] is not None
                        else ""
                    ),
                    s["role"],
                    dependencies=dependencies,
                    context_scope=wf["context_scope"],
                    workflow_id=workflow_id,
                    workflow_step_id=s["id"],
                    profile=s["profile"],
                    run_id=run_id,
                )
                # A durable packet binds predecessor files to the receiving run.
                for dependency in dependencies:
                    sources = await db.execute(
                        "SELECT a.id FROM artifacts a JOIN runs r ON r.id=a.run_id WHERE a.tenant_id=%s AND r.workflow_step_id=(SELECT workflow_step_id FROM runs WHERE id=%s) AND r.created_at>=(SELECT created_at FROM runs WHERE id=%s)",
                        (actor.tenant_id, dependency, dependency),
                    )
                    packet = {
                        "objective": wf["goal"],
                        "checkpoint": "Completed workflow dependency",
                        "remaining": s["objective"],
                        "evidence": [],
                        "artifact_ids": [a["id"] for a in sources],
                        "check_event_ids": [],
                        "source_run": dependency,
                    }
                    packet_id = str(uuid5(NAMESPACE_URL, f"engram:packet:{dependency}:{run_id}"))
                    await conn.execute(
                        "INSERT INTO handoffs(id,tenant_id,from_run,to_run,packet) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (packet_id, actor.tenant_id, dependency, run_id, Jsonb(packet)),
                    )
                await conn.execute(
                    "UPDATE workflow_steps SET run_id=%s,status='running',error=NULL WHERE id=%s", (run["id"], s["id"])
                )
            states = await (
                await conn.execute("SELECT status FROM workflow_steps WHERE workflow_id=%s", (workflow_id,))
            ).fetchall()
            if states and all(s["status"] == "completed" for s in states):
                await conn.execute(
                    "UPDATE workflows SET status='completed',updated_at=now() WHERE id=%s", (workflow_id,)
                )
            elif any(s["status"] == "blocked" for s in states):
                await conn.execute(
                    "UPDATE workflows SET status='blocked',updated_at=now() WHERE id=%s AND status='running'",
                    (workflow_id,),
                )


async def scheduler_loop():
    while True:
        rows = await db.execute("SELECT id FROM workflows WHERE status='running' ORDER BY created_at LIMIT 100")
        for row in rows:
            try:
                await tick(row["id"])
            except Exception as exc:
                await db.execute(
                    "UPDATE workflows SET status='blocked',updated_at=now() WHERE id=%s AND status='running'",
                    (row["id"],),
                )
                wf = await db.execute("SELECT tenant_id FROM workflows WHERE id=%s", (row["id"],), one=True)
                await db.event(
                    wf["tenant_id"],
                    "workflow.scheduler_blocked",
                    {"workflow_id": row["id"], "error_type": type(exc).__name__},
                )
        await asyncio.sleep(2)
