"""Real-store revision, context-budget and duplicate-delivery contracts."""
import asyncio
import json
import os

import pytest
from fastapi import HTTPException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session"),
              pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires actual local services")]


async def fixture():
    from collective.auth import Principal, register
    from collective.db import db, uid
    await db.open()
    user = await register(f"passport-{uid()}@example.test", "Passport-test-only-123", "Passport", "Passport fixture")
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, member["tenant_id"], "owner", "Passport")
    project = uid()
    await db.execute("INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Memory passport checks')", (project, actor.tenant_id))
    return actor, project


async def cleanup(actor):
    from collective.db import db
    await db.execute("UPDATE runs SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE tenant_id=%s", (actor.tenant_id,))


async def test_capsules_are_budgeted_auditable_and_do_not_subscribe_unrelated_tasks():
    from collective.context_passports import tokens
    from collective.db import db
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import create_run
    actor, project = await fixture()
    try:
        owner = await memory.commit(actor, project, "ORCHID approver is Maya", memory_type="semantic")
        document = await memory.commit(actor, project, "FalkorDB documentation is at docs.falkordb.com", memory_type="semantic")
        reader = await create_run(actor, project, "Use only the approval reference", "researcher", memory_ids=[owner["id"]])
        unrelated = await create_run(actor, project, "Read only the documentation reference", "researcher", memory_ids=[document["id"]])
        first = await memory.focused(actor, project, [owner["id"]], reader["id"])
        again = await memory.focused(actor, project, [owner["id"]], reader["id"])
        assert first["passport"]["event_id"] == again["passport"]["event_id"]
        await memory.focused(actor, project, [document["id"]], unrelated["id"])
        assert first["approximate_tokens"] == tokens(first["capsules"])
        assert first["approximate_tokens"] <= first["passport"]["budget_tokens"]
        changed = await memory.supersede(actor, project, owner["id"], "ORCHID approver is Priya", 1)
        assert changed["affected_runs"] == [reader["id"]]
        assert (await db.execute("SELECT status FROM runs WHERE id=%s", (unrelated["id"],), one=True))["status"] == "queued"
        paths = await graph.query(actor.tenant_id, "MATCH (t:Task {id:$t})-[:DEPENDS_ON]->(m:Memory) RETURN m.id", {"t": unrelated["id"]})
        assert paths == [[document["id"]]]
        metadata = {"kind": "workflow", "name": "check-python", "version": 1, "steps": ["python -m pytest -q"],
                    "preconditions": ["Use the bound files"], "artifact_manifest": [], "historical_notes": "old audit note " * 1000}
        procedure = await memory.commit(actor, project, json.dumps(metadata), memory_type="procedural", metadata=metadata, status="proposed")
        task = await create_run(actor, project, "Inspect this proposed procedure", "verifier", memory_ids=[procedure["id"]])
        compact = await memory.focused(actor, project, [procedure["id"]], task["id"])
        assert compact["capsules"][0]["content_is_projection"]
        assert "historical_notes" not in compact["capsules"][0]["content"]
        assert compact["passport"]["context_tokens"] < compact["passport"]["source_record_tokens"]
        assert (await memory.get(actor, project, procedure["id"]))["content"] == procedure["content"]
    finally:
        await cleanup(actor)


async def test_correction_between_snapshot_and_subscription_rejects_old_context():
    from collective.context_passports import capsule, consume
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import create_run
    actor, project = await fixture()
    try:
        old = await memory.commit(actor, project, "Current approver Maya", memory_type="semantic")
        task = await create_run(actor, project, "Read an approval snapshot", "researcher")
        await memory.supersede(actor, project, old["id"], "Current approver Priya", 1)
        with pytest.raises(HTTPException) as failure:
            await consume(actor, project, task["id"], [old], [capsule(old)], mode="race_test", budget=2000)
        assert failure.value.status_code == 409
        assert not await graph.query(actor.tenant_id, "MATCH (t:Task {id:$t})-[:DEPENDS_ON]->(m:Memory) RETURN m.id", {"t": task["id"]})
    finally:
        await cleanup(actor)


async def test_parallel_duplicate_handoffs_have_one_claimable_receiver_and_envelope():
    from collective.db import db
    from collective.memory import memory
    from collective.runtime import create_run, handoff
    actor, project = await fixture()
    try:
        fact = await memory.commit(actor, project, "The approved ORCHID owner is Priya", memory_type="semantic")
        source = await create_run(actor, project, "Share the sourced approval decision", "researcher")
        delivered = await asyncio.wait_for(asyncio.gather(*[
            handoff(actor, source, "researcher", "Approval owner recorded", [fact["id"]], [], "Review the supplied approval evidence")
            for _ in range(20)
        ]), timeout=40)
        assert len({r["id"] for r in delivered}) == 1
        assert all(r["status"] == "queued" for r in delivered)
        rows = await db.execute("SELECT * FROM handoffs WHERE tenant_id=%s", (actor.tenant_id,))
        assert len(rows) == 1
        assert rows[0]["packet"]["evidence"] == [{"id": fact["id"], "revision": 1}]
        assert delivered[0]["memory_refs"] == [fact["id"]]
        assert len(rows[0]["packet"]["digest"]) == 64
        events = await db.execute("SELECT id FROM events WHERE tenant_id=%s AND kind='task.handoff'", (actor.tenant_id,))
        assert len(events) == 1
    finally:
        await cleanup(actor)


async def test_private_references_are_private_before_start_and_stale_packets_cannot_acknowledge():
    from collective.db import db
    from collective.memory import memory
    from collective.runtime import create_run, handoff, acknowledge_handoffs
    actor, project = await fixture()
    try:
        fact = await memory.commit(actor, project, "Private release approver is Maya", visibility="user", memory_type="semantic")
        parent = await create_run(actor, project, "Shared source task", "researcher")
        child = await create_run(actor, project, "Read a private reference", "researcher", parent=parent["id"], memory_ids=[fact["id"]], initial_status="awaiting_handoff")
        assert child["visibility"] == "user"
        assert (await db.execute("SELECT visibility FROM runs WHERE id=%s", (child["id"],), one=True))["visibility"] == "user"
        receiver = await handoff(actor, parent, "researcher", "Private evidence supplied", [fact["id"]], [], "Review this private approval reference")
        assert receiver["visibility"] == "user"
        assert (await db.execute("SELECT visibility FROM runs WHERE id=%s", (parent["id"],), one=True))["visibility"] == "user"
        descendant = await create_run(actor, project, "Keep a private parent private before queueing", "researcher", parent=parent["id"], memory_ids=[])
        assert descendant["visibility"] == "user"
        packets = await db.execute("SELECT * FROM handoffs WHERE to_run=%s", (receiver["id"],))
        await memory.supersede(actor, project, fact["id"], "Private release approver is Priya", 1)
        with pytest.raises(HTTPException) as conflict:
            await acknowledge_handoffs(actor, receiver, packets)
        assert conflict.value.status_code == 409
        assert (await db.execute("SELECT acknowledged_at FROM handoffs WHERE to_run=%s", (receiver["id"],), one=True))["acknowledged_at"] is None
    finally:
        await cleanup(actor)


async def test_private_correction_events_are_hidden_from_other_workspace_members():
    import httpx
    from collective.app import app
    from collective.auth import register
    from collective.db import db, uid
    from collective.memory import memory
    actor, project = await fixture()
    outsider_email = f"event-member-{uid()}@example.test"
    other = await register(outsider_email, "Event-member-only-123", "Member", "Other workspace")
    await db.execute("INSERT INTO memberships(tenant_id,user_id,role) VALUES (%s,%s,'member')", (actor.tenant_id, other))
    private = await memory.commit(actor, project, "Private launch codename LANTERN", visibility="user")
    await memory.supersede(actor, project, private["id"], "Private launch codename SOLSTICE", 1)
    shared = await memory.commit(actor, project, "Shared release checklist is available", visibility="team")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        logged_in = await client.post("/api/auth/login", headers={"X-Engram-Request": "1"}, json={"email": outsider_email, "password": "Event-member-only-123"})
        assert logged_in.status_code == 200
        response = await client.get("/api/events", headers={"X-Workspace": actor.tenant_id})
        assert response.status_code == 200
        assert "LANTERN" not in response.text and "SOLSTICE" not in response.text
        assert private["id"] not in response.text
        assert shared["id"] in response.text
        assert int(response.headers["X-Engram-Next-Event"]) >= max(e["id"] for e in response.json())
    await cleanup(actor)


async def test_reference_superseded_before_start_requires_explicit_rebinding():
    from collective.memory import memory
    from collective.runtime import create_run
    actor, project = await fixture()
    try:
        old = await memory.commit(actor, project, "Approval owner Maya", memory_type="semantic")
        task = await create_run(actor, project, "Act on this bound memory", "researcher", memory_ids=[old["id"]], initial_status="awaiting_handoff")
        changed = await memory.supersede(actor, project, old["id"], "Approval owner Priya", 1)
        with pytest.raises(HTTPException) as late:
            await memory.focused(actor, project, [old["id"]], task["id"])
        assert late.value.status_code == 409
        with pytest.raises(HTTPException) as creation:
            await create_run(actor, project, "Do not silently use old ownership", "researcher", memory_ids=[old["id"]])
        assert creation.value.status_code == 409
        replacement = await create_run(actor, project, "Use the current approval record", "researcher", memory_ids=[changed["memory"]["id"]], initial_status="awaiting_handoff")
        context = await memory.focused(actor, project, replacement["memory_refs"], replacement["id"])
        assert context["evidence_ids"] == [changed["memory"]["id"]]
        # Full historical inspection remains possible, with its superseded status.
        assert (await memory.get(actor, project, old["id"]))["status"] == "superseded"
    finally:
        await cleanup(actor)
