"""Immutable artifact-bound procedure versions and measured execution reuse."""

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .db import db
from .evidence import fresh_check_ids, execution_progress, verified_check
from .memory import memory
from .settings import settings
from .artifact_store import read as read_artifact


async def metrics(run_ids):
    events = await db.execute("SELECT kind,payload FROM events WHERE run_id=ANY(%s)", (list(run_ids),))
    return {
        "tool_executions": sum(e["kind"] == "tool.executed" for e in events),
        "file_writes": sum(e["kind"] == "sandbox.file_written" for e in events),
        "model_calls": sum(e["kind"] == "model.usage" for e in events),
        "model_tokens": sum(int(e["payload"].get("total_tokens", 0)) for e in events if e["kind"] == "model.usage"),
    }


async def bind_version(actor, run, descriptor):
    checks = await db.execute(
        """SELECT e.id,e.run_id,e.payload FROM events e JOIN runs r ON r.id=e.run_id
        WHERE e.tenant_id=%s AND r.project_id=%s AND (r.visibility='team' OR r.user_id=%s)
        AND e.kind='tool.executed' AND e.id=ANY(%s)""",
        (actor.tenant_id, run["project_id"], actor.user_id, descriptor["check_event_ids"]))
    if len(checks) != len(set(descriptor["check_event_ids"])) or any(not verified_check(c["payload"]) for c in checks):
        raise ValueError("Procedure requires accessible passing execution evidence")
    source_runs = list({c["run_id"] for c in checks})
    artifacts = await db.execute(
        """SELECT DISTINCT ON (a.name) a.id,a.name,a.sha256,a.path,a.run_id FROM artifacts a JOIN runs r ON r.id=a.run_id
        WHERE a.tenant_id=%s AND a.project_id=%s AND (r.visibility='team' OR r.user_id=%s)
        AND (a.run_id=ANY(%s) OR a.id IN (SELECT payload->>'artifact_id' FROM events
        WHERE tenant_id=%s AND kind='artifact.read' AND run_id=ANY(%s))) ORDER BY a.name,a.created_at DESC""",
        (actor.tenant_id, run["project_id"], actor.user_id, source_runs, actor.tenant_id, source_runs))
    if not artifacts:
        raise ValueError("A procedure version requires published source artifacts")
    for artifact in artifacts:
        await read_artifact(artifact)
    manifest = [{k: a[k] for k in ("id", "name", "sha256", "run_id")} for a in artifacts]
    baseline = await metrics(source_runs)
    family = descriptor["name"].strip().casefold()
    enforced = {"sandbox_image": settings.sandbox_image, "network": "none", "artifact_hashes": True,
        "declared": descriptor["preconditions"], "source_runs": source_runs}
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (f"procedure:{actor.tenant_id}:{run['project_id']}:{family}",))
            row = await (await conn.execute(
                "SELECT COALESCE(max(version),0)+1 AS next FROM procedure_versions WHERE tenant_id=%s AND project_id=%s AND family=%s",
                (actor.tenant_id, run["project_id"], family))).fetchone()
            descriptor.update(version=row["next"], artifact_manifest=manifest, enforced_preconditions=enforced,
                baseline=baseline, proposer_run=run["id"])
            import json
            record = await memory.commit(actor, run["project_id"], json.dumps(descriptor), category="critical",
                memory_type="procedural", metadata=descriptor, agent_id=run["id"], status="proposed")
            await conn.execute(
                """INSERT INTO procedure_versions(id,tenant_id,project_id,family,version,proposer_run,manifest,preconditions,baseline)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (record["id"], actor.tenant_id, run["project_id"], family, row["next"], run["id"],
                 Jsonb(manifest), Jsonb(enforced), Jsonb(baseline)))
            return record


async def begin_use(actor, run, record):
    row = await db.execute("SELECT * FROM procedure_versions WHERE id=%s AND tenant_id=%s AND project_id=%s",
        (record["id"], actor.tenant_id, run["project_id"]), one=True)
    if not row:
        return  # Explicit legacy workflow, no version/reuse claim.
    if row["preconditions"]["sandbox_image"] != settings.sandbox_image:
        raise ValueError("Procedure sandbox precondition changed; publish and verify a new version")
    if row["status"] not in {"active", "proposed"}:
        raise ValueError("Procedure version is inactive")
    for artifact in row["manifest"]:
        actual = await db.execute("SELECT * FROM artifacts WHERE id=%s AND tenant_id=%s AND project_id=%s",
            (artifact["id"], actor.tenant_id, run["project_id"]), one=True)
        if not actual or actual["sha256"] != artifact["sha256"]:
            raise ValueError("Procedure artifact version does not match its immutable manifest")
        await read_artifact(actual)
    if row["status"] == "active":
        await db.execute("INSERT INTO procedure_uses(procedure_id,run_id,tenant_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (record["id"], run["id"], actor.tenant_id))
        await db.event(actor.tenant_id, "procedure.reuse_started", {"procedure_id": record["id"],
            "version": row["version"], "manifest": row["manifest"]}, run["id"])


async def verify_version(actor, run, record, check_ids, actual_hashes):
    row = await db.execute("SELECT * FROM procedure_versions WHERE id=%s AND tenant_id=%s AND project_id=%s",
        (record["id"], actor.tenant_id, run["project_id"]), one=True)
    if not row:
        raise ValueError("Legacy procedures must be proposed again to obtain an artifact-bound version")
    if run["id"] == row["proposer_run"] or run["id"] in row["preconditions"]["source_runs"]:
        raise ValueError("A different agent run must independently verify this procedure")
    progress = await execution_progress(run["id"])
    if not check_ids or not set(check_ids) <= set(fresh_check_ids(progress)):
        raise ValueError("Independent current-file checks are required")
    # Artifact copies are hash-checked by artifact_read; bind each exact version
    # to this verifier's current tracked workspace, not a similarly named file.
    written = await db.execute("SELECT id,payload FROM events WHERE tenant_id=%s AND run_id=%s AND kind='sandbox.file_written' ORDER BY id",
        (actor.tenant_id, run["id"]))
    latest = {e["payload"]["path"]: e["payload"] for e in written}
    for artifact in row["manifest"]:
        file = latest.get(artifact["name"], latest.get("/workspace/" + artifact["name"]))
        if not file or file.get("sha256") != artifact["sha256"]:
            raise ValueError("Verifier workspace does not match the procedure artifact manifest")
        if actual_hashes.get(artifact["name"]) != artifact["sha256"]:
            raise ValueError("Actual verifier bytes changed from the bound artifact version")
    await db.execute("UPDATE procedure_versions SET status='active',verifier_run=%s WHERE id=%s AND status='proposed'",
        (run["id"], record["id"]))
    await db.event(actor.tenant_id, "procedure.version_verified", {"procedure_id": record["id"],
        "version": row["version"], "check_event_ids": check_ids, "artifact_manifest": row["manifest"]}, run["id"])


async def complete_use(actor, run, record, actual_hashes):
    if not record:
        return
    row = await db.execute("SELECT p.*,u.completed_at FROM procedure_versions p JOIN procedure_uses u ON u.procedure_id=p.id WHERE p.id=%s AND u.run_id=%s AND u.tenant_id=%s",
        (record["id"], run["id"], actor.tenant_id), one=True)
    if not row or row["completed_at"]:
        return
    await verify_reuse_files(actor, run, row)
    if any(actual_hashes.get(a["name"]) != a["sha256"] for a in row["manifest"]):
        raise ValueError("Reuse workspace differs from the verified artifact version")
    actual = await metrics([run["id"]])
    measured = {"actual": actual, "baseline": row["baseline"], "savings": {
        k: row["baseline"][k] - actual[k] for k in actual},
        "comparison": "source execution versus reuse; signed deltas, not a controlled speed benchmark"}
    await db.execute("UPDATE procedure_uses SET completed_at=now(),metrics=%s WHERE procedure_id=%s AND run_id=%s",
        (Jsonb(measured), record["id"], run["id"]))
    await db.event(actor.tenant_id, "procedure.reused", {"procedure_id": record["id"], "version": row["version"], **measured}, run["id"])


async def verify_reuse_files(actor, run, row):
    if not fresh_check_ids(await execution_progress(run["id"])):
        raise HTTPException(409, "Procedure reuse has no fresh successful execution evidence")
    return True
