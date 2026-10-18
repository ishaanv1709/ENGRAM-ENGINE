"""Real PostgreSQL/FalkorDB/embeddings tests; no substituted services."""

import asyncio
import os

import pytest
from fastapi import HTTPException

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires running local infrastructure"),
]


async def test_concurrent_claims_correction_replan_and_ambiguous_tie():
    from collective.auth import Principal, register
    from collective.coordination import submit_claim, resolve_claims, replan
    from collective.db import db, uid
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import create_run

    await db.open()
    user = await register(f"claims-{uid()}@example.test", "Integration-password-123", "Claims", "Claims test")
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, member["tenant_id"], "owner", "Claims")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Claim integration')", (project, actor.tenant_id)
    )
    old_time, new_time = "2026-01-01T09:00:00+00:00", "2026-01-02T09:00:00+00:00"
    sources = await asyncio.gather(
        *[
            memory.commit(actor, project, text, metadata={"observed_at": at})
            for text, at in [
                ("Maya owns ORCHID", old_time),
                ("Priya now owns ORCHID", new_time),
                ("Noor owns ORCHID", new_time),
            ]
        ]
    )
    private = await memory.commit(actor, project, "ORCHID private planning note", visibility="user")
    shared_run = await create_run(actor, project, "Review ORCHID shared evidence", "researcher", context_scope="team")
    shared = await memory.context(actor, project, "ORCHID", shared_run["id"], shared_run["id"])
    assert private["id"] not in shared["evidence_ids"]
    assert all(record["visibility"] == "team" for record in shared["memories"])
    with pytest.raises(HTTPException) as denied:
        await memory.get(actor, project, private["id"], shared_run["id"])
    assert denied.value.status_code == 404
    assert (await db.execute("SELECT visibility FROM runs WHERE id=%s", (shared_run["id"],), one=True))[
        "visibility"
    ] == "team"
    first = await submit_claim(actor, project, "ORCHID", "owner", "Maya", sources[0]["id"], old_time)
    initial = await resolve_claims(actor, project, "ORCHID", "owner")
    assert initial["winner_id"] == first["id"]
    task = await create_run(actor, project, "Prepare release plan for the current ORCHID owner", "researcher")
    await graph.depend(actor.tenant_id, task["id"], [initial["memory_id"]])
    try:
        claims = await asyncio.gather(
            submit_claim(actor, project, "ORCHID", "owner", "Maya", sources[0]["id"], old_time),
            submit_claim(actor, project, "ORCHID", "owner", "Priya", sources[1]["id"], new_time),
        )
        resolved = await resolve_claims(actor, project, "ORCHID", "owner")
        assert resolved["winner_id"] == claims[1]["id"]
        assert len(resolved["evidence"]["claims"]) == 3
        stale = await db.execute("SELECT status FROM runs WHERE id=%s", (task["id"],), one=True)
        assert stale["status"] == "stale"
        # Reading other source records does not make a task a reader of the old
        # selected fact. A correction must not invalidate the whole project.
        assert (await db.execute("SELECT status FROM runs WHERE id=%s", (shared_run["id"],), one=True))[
            "status"
        ] == "queued"
        correction = await db.execute(
            "SELECT id FROM events WHERE tenant_id=%s AND kind='memory.corrected' ORDER BY id DESC LIMIT 1",
            (actor.tenant_id,),
            one=True,
        )
        await db.execute("UPDATE runs SET visibility='user' WHERE id=%s", (task["id"],))
        plan = await replan(actor, project, correction["id"])
        again = await replan(actor, project, correction["id"])
        assert plan["new_plan_id"] == again["new_plan_id"]
        assert task["id"] in plan["affected_runs"]
        assert (await db.execute("SELECT visibility FROM runs WHERE id=%s", (plan["new_plan_id"],), one=True))[
            "visibility"
        ] == "user"
        path = await graph.query(
            actor.tenant_id,
            "MATCH (n:Task {id:$n})-[:REPLANS]->(o:Task {id:$o}) RETURN n.id",
            {"n": plan["new_plan_id"], "o": task["id"]},
        )
        assert path
        from collective.showcase import correction_witnesses

        correction_event = await db.execute("SELECT * FROM events WHERE id=%s", (correction["id"],), one=True)
        witnesses = await correction_witnesses(
            actor.tenant_id, project, [correction_event], {task["id"], shared_run["id"], plan["new_plan_id"]}
        )
        witness = witnesses[correction["id"]]
        assert witness["direct_readers"] == [task["id"]]
        assert witness["supersession_present"]
        assert witness["new_fact_readers"] == [plan["new_plan_id"]]
        assert witness["revision_edges"] == [{"source": plan["new_plan_id"], "type": "REPLANS", "target": task["id"]}]
        # The explanatory read path must apply the same access-filtered ID set.
        hidden = await correction_witnesses(actor.tenant_id, project, [correction_event], {shared_run["id"]})
        assert hidden[correction["id"]]["direct_readers"] == []
        assert hidden[correction["id"]]["revision_edges"] == []
        with pytest.raises(HTTPException) as active_replacement:
            await replan(actor, project, correction["id"], replace_failed=True)
        assert active_replacement.value.status_code == 409
        await db.execute(
            "UPDATE runs SET status='cancelled',lease_token=NULL,revision=revision+1 WHERE id=%s",
            (plan["new_plan_id"],),
        )
        replacement = await replan(actor, project, correction["id"], replace_failed=True)
        assert replacement["new_plan_id"] != plan["new_plan_id"]
        assert replacement["superseded_plan_id"] == plan["new_plan_id"]
        assert (await replan(actor, project, correction["id"]))["new_plan_id"] == replacement["new_plan_id"]
        assert (await db.execute("SELECT visibility FROM runs WHERE id=%s", (replacement["new_plan_id"],), one=True))[
            "visibility"
        ] == "user"
        new_reader = await create_run(actor, project, "Review the selected approval owner", "researcher")
        await graph.depend(actor.tenant_id, new_reader["id"], [resolved["memory_id"]])
        await submit_claim(actor, project, "ORCHID", "owner", "Noor", sources[2]["id"], new_time)
        ambiguous = await resolve_claims(actor, project, "ORCHID", "owner")
        assert ambiguous["winner_id"] is None and ambiguous["evidence"]["status"] == "unresolved"
        current = await memory.get(actor, project, ambiguous["memory_id"])
        assert current["status"] == "disputed"
        assert (await db.execute("SELECT status FROM runs WHERE id=%s", (new_reader["id"],), one=True))[
            "status"
        ] == "stale"
        with pytest.raises(HTTPException):
            await submit_claim(actor, project, "ORCHID", "owner", "forged", sources[0]["id"], new_time)
        foreign = Principal(actor.user_id, uid(), "owner", "Other tenant")
        with pytest.raises(HTTPException):
            await submit_claim(foreign, project, "ORCHID", "owner", "forged", sources[0]["id"], old_time)
    finally:
        await db.execute(
            "UPDATE runs SET status='cancelled',lease_token=NULL,revision=revision+1 WHERE tenant_id=%s AND status IN ('queued','running','stale')",
            (actor.tenant_id,),
        )


async def test_real_artifact_bound_procedure_independent_checks_and_reuse():
    from collective.auth import Principal, register
    from collective.agents import prepare_resources
    from collective.db import db, uid
    from collective.memory import memory
    from collective.procedures import complete_use
    from collective.runtime import create_run, claim, finish
    from collective.tools import RunTools
    import hashlib

    await db.open()
    user = await register(f"procedure-{uid()}@example.test", "Integration-password-123", "Procedure", "Procedure test")
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, member["tenant_id"], "owner", "Procedure")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Procedure integration')", (project, actor.tenant_id)
    )
    await create_run(actor, project, "Build real arithmetic fixture", "builder")
    builder = await claim("procedure-integration", actor.tenant_id)
    toolkit = RunTools(actor, builder)
    core, optional = toolkit.build()
    tools = {t.name: t for t in core + optional}
    try:
        await tools["sandbox_write"].ainvoke(
            {"path": "capacity.py", "content": "def capacity(n):\n    return n * 25\n"}
        )
        await tools["sandbox_write"].ainvoke(
            {
                "path": "test_capacity.py",
                "content": "from capacity import capacity\ndef test_capacity():\n    assert capacity(3) == 75\n",
            }
        )
        check = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
        assert check["verification_passed"]
        for name in ("capacity.py", "test_capacity.py"):
            await tools["artifact_publish"].ainvoke({"path": name})
        proposed = await tools["procedure_propose"].ainvoke(
            {
                "name": "Capacity check",
                "purpose": "Check capacity arithmetic",
                "preconditions": ["Published capacity.py and test_capacity.py must match their hashes"],
                "steps": ["Copy bound artifacts", "Run python -m pytest -q"],
                "tool_names": ["artifact_read", "sandbox_execute"],
                "check_event_ids": [check["check_event_id"]],
            }
        )
        await finish(builder, "completed")
        verifier = await claim("procedure-integration", actor.tenant_id)
        assert verifier["id"] == proposed["verification_task"]
        verify_tools = RunTools(actor, verifier)
        vc, vo = verify_tools.build()
        vt = {t.name: t for t in vc + vo}
        try:
            await prepare_resources(verify_tools, vc, [])
            checked = await vt["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            activated = await vt["procedure_verify"].ainvoke(
                {"procedure_id": proposed["procedure_id"], "check_event_ids": [checked["check_event_id"]]}
            )
            assert activated["status"] == "active" and activated["metadata"]["version"] == 1
            assert len(activated["metadata"]["artifact_manifest"]) == 2
            await finish(verifier, "completed")
        finally:
            await verify_tools.close()
        await create_run(
            actor, project, f"Reuse the already active verified procedure {proposed['procedure_id']}", "verifier"
        )
        reuse = await claim("procedure-integration", actor.tenant_id)
        reuse_tools = RunTools(actor, reuse)
        rc, ro = reuse_tools.build()
        rt = {t.name: t for t in rc + ro}
        try:
            await prepare_resources(reuse_tools, rc, [])
            checked = await rt["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            record = await memory.get(actor, project, proposed["procedure_id"])
            hashes = {
                a["name"]: hashlib.sha256(await reuse_tools.sandbox.read(a["name"])).hexdigest()
                for a in record["metadata"]["artifact_manifest"]
            }
            await complete_use(actor, reuse, record, hashes)
            usage = await db.execute(
                "SELECT metrics FROM procedure_uses WHERE procedure_id=%s AND run_id=%s",
                (record["id"], reuse["id"]),
                one=True,
            )
            assert usage["metrics"]["actual"]["tool_executions"] == 1
            assert usage["metrics"]["savings"]["tool_executions"] == 0
            await finish(reuse, "completed")
        finally:
            await reuse_tools.close()
    finally:
        await toolkit.close()
        await db.execute(
            "UPDATE runs SET status='cancelled',lease_token=NULL,revision=revision+1 WHERE tenant_id=%s AND status IN ('queued','running','stale')",
            (actor.tenant_id,),
        )


async def test_model_budget_queue_preserves_fifo_even_when_smaller_call_fits():
    from collective.db import uid
    from collective.model_budget import try_reserve
    from collective.settings import settings
    import psycopg

    key = "fifo-integration:" + uid()
    head, tail = uid(), uid()
    try:
        occupied, _ = try_reserve(key, 500, 1000)
        assert occupied
        first, _ = try_reserve(key, 900, 1000, head)
        second, _ = try_reserve(key, 100, 1000, tail)
        assert first is None and second is None
        with psycopg.connect(settings.database_url) as conn:
            conn.execute("DELETE FROM model_reservations WHERE key=%s", (key,))
        first, _ = try_reserve(key, 900, 1000, head)
        second, _ = try_reserve(key, 100, 1000, tail)
        assert first and second
    finally:
        with psycopg.connect(settings.database_url) as conn:
            conn.execute("DELETE FROM model_reservations WHERE key=%s", (key,))
            conn.execute("DELETE FROM model_waiters WHERE key=%s", (key,))
