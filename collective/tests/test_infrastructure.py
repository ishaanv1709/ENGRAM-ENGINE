"""These tests use REAL PostgreSQL, FalkorDB and the GGUF embedding service.

No mock service is substituted. Explicitly enable with ENGRAM_INTEGRATION=1.
"""

import asyncio
import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires running local infrastructure"),
]


async def test_real_memory_concurrency_correction_handoff_and_isolation():
    from collective.auth import Principal, register
    from collective.db import db, uid
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import claim, create_run, finish, handoff

    await db.open()
    user = await register(
        f"integration-{uid()}@example.test", "Integration-only-password-123", "Integration", "Integration fixture"
    )
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, member["tenant_id"], "owner", "Integration")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Integration fixture')", (project, actor.tenant_id)
    )
    await graph.ensure(actor.tenant_id)
    from collective.graph import Graph

    await Graph().ensure(actor.tenant_id)  # A fresh process must reuse persisted indexes.
    observations = await asyncio.gather(
        *(
            memory.commit(
                actor,
                project,
                f"Integration observation {i}: service-{i} has its own owner.",
                category="critical",
                memory_type="semantic",
            )
            for i in range(8)
        )
    )
    assert len({r["id"] for r in observations}) == 8
    assert len(await memory.list(actor, project)) == 8
    private = await memory.commit(actor, project, "Private assertion owned only by integration user", visibility="user")
    other = Principal("another-user", actor.tenant_id, "member", "Other")
    assert not any(r["id"] == private["id"] for r in await memory.list(other, project))
    run = await create_run(actor, project, "Test dependency invalidation", "researcher")
    await graph.depend(actor.tenant_id, run["id"], [observations[0]["id"]])
    packet = await handoff(
        actor, run, "verifier", "Check the fact", [observations[1]["id"]], [], "Verify current ownership"
    )
    assert packet["role"] == "verifier"
    changed = await memory.supersede(actor, project, observations[0]["id"], "Corrected owner is Team B", 1)
    assert run["id"] in changed["affected_runs"]
    stale = await db.execute("SELECT status FROM runs WHERE id=%s", (run["id"],), one=True)
    assert stale["status"] == "stale"
    # Isolate lease checks from the actual worker queue by claiming by a unique
    # transaction with all other fixture tasks cancelled first.
    await db.execute("UPDATE runs SET status='cancelled' WHERE tenant_id=%s", (actor.tenant_id,))
    lease_run = await create_run(actor, project, "Lease fencing verification", "researcher")
    claimed = await claim("integration-worker", actor.tenant_id)
    assert claimed is not None
    await db.execute("UPDATE runs SET revision=revision+1,lease_token=NULL WHERE id=%s", (claimed["id"],))
    with pytest.raises(RuntimeError, match="late result rejected"):
        await finish(claimed, "completed", {"summary": "must never commit"})
    await db.execute("UPDATE runs SET status='cancelled' WHERE tenant_id=%s", (actor.tenant_id,))
    assert lease_run["id"]


async def test_real_restricted_sandbox():
    from collective.db import uid
    from collective.sandbox import Sandbox

    box = await Sandbox(uid()).start()
    try:
        await box.write("test_math.py", "def test_addition():\n    assert 2 + 2 == 4\n")
        run = await box.execute("python -m pytest -q test_math.py")
        assert run["exit_code"] == 0, run
        assert "1 passed" in run["stdout"]
        assert b"assert 2 + 2" in await box.read("test_math.py")
        denied = await box.execute("touch /forbidden-file")
        assert denied["exit_code"] != 0
        identity = await box.execute("id -u")
        assert identity["stdout"].strip() == "65534"
        secrets = await box.execute("env")
        assert "ANTHROPIC_API_KEY" not in secrets["stdout"]
    finally:
        await box.close()


async def test_real_graph_paths_hybrid_retrieval_cache_and_private_run_scope():
    from collective.auth import Principal, register
    from collective.db import db, uid
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import create_run

    await db.open()
    user = await register(
        f"retrieval-{uid()}@example.test", "Retrieval-test-password-123", "Retrieval", "Retrieval fixture"
    )
    row = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, row["tenant_id"], "owner", "Retrieval")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Retrieval fixture')", (project, actor.tenant_id)
    )
    source = await memory.commit(
        actor, project, "Ownership meeting: ORCHID belongs to Maya, who leads the Platform team."
    )
    fact = await memory.commit(
        actor,
        project,
        "Project ORCHID is owned by Maya",
        category="critical",
        memory_type="semantic",
        source_ids=[source["id"]],
        entities=["ORCHID", "Maya"],
        triples=[("ORCHID", "OWNED_BY", "Maya")],
    )
    related = await memory.commit(
        actor,
        project,
        "Maya leads the Platform team",
        category="relational",
        memory_type="semantic",
        source_ids=[source["id"]],
        entities=["Maya", "Platform"],
        triples=[("Maya", "LEADS", "Platform")],
    )
    neighbors = await graph.neighbors(actor.tenant_id, fact["id"])
    assert related["id"] in {r["id"] for r in neighbors}
    path = await graph.query(
        actor.tenant_id,
        "MATCH (s:Entity)-[:SUBJECT_OF]->(r:Relation)-[:OBJECT]->(o:Entity) WHERE r.predicate='OWNED_BY' RETURN s.name,o.name",
    )
    assert ["ORCHID", "Maya"] in path
    bundle = await memory.context(actor, project, "Which team does the owner of ORCHID lead?")
    assert fact["id"] in bundle["evidence_ids"] and related["id"] in bundle["evidence_ids"]
    cached = await memory.context(actor, project, "Which team does the owner of ORCHID lead?")
    assert cached["tier"] == "recent_cache"
    secret = await memory.commit(
        actor, project, "Only my account should see this planning preference", visibility="user"
    )
    run = await create_run(actor, project, "Check my planning preference", "researcher")
    private_context = await memory.context(actor, project, secret["content"], run["id"], run["id"])
    assert secret["id"] in private_context["evidence_ids"]
    scoped = await db.execute("SELECT visibility FROM runs WHERE id=%s", (run["id"],), one=True)
    assert scoped["visibility"] == "user"
    for name in ("sandbox_execute", "web_search"):
        await memory.commit(
            actor,
            project,
            name + " registered capability",
            category="critical",
            memory_type="procedural",
            metadata={"kind": "tool", "tool_name": name},
        )
    # Higher-ranked tools from another role must not consume the role's limit;
    # a cached request for another permission set must not leak into this one.
    for allowed in ({"web_search"}, {"sandbox_execute"}):
        capabilities = await memory.context(
            actor,
            project,
            "sandbox_execute registered capability",
            kind="procedural",
            limit=1,
            allowed_tool_names=allowed,
        )
        assert len(capabilities["memories"]) == 1
        assert capabilities["memories"][0]["metadata"]["tool_name"] in allowed
    await db.execute("UPDATE runs SET status='cancelled' WHERE tenant_id=%s", (actor.tenant_id,))


async def test_shared_provider_budget_is_atomic_across_connections():
    from collective.db import db, uid
    from collective.model_budget import try_reserve
    from collective.settings import DependencyUnavailable

    await db.open()
    key = "verification-budget:" + uid()
    reservations = await asyncio.gather(*(asyncio.to_thread(try_reserve, key, 1, 5) for _ in range(8)))
    assert sum(ticket is not None for ticket, delay in reservations) == 5
    assert all(0 < delay <= 2 for ticket, delay in reservations if ticket is None)
    with pytest.raises(DependencyUnavailable):
        await asyncio.to_thread(try_reserve, key, 6, 5)
    await db.execute("DELETE FROM model_reservations WHERE key=%s", (key,))
