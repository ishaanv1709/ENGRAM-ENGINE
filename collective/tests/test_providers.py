"""Credential-gated end-to-end test using real models, Jev, Mem0 and tools."""

import os

import pytest

from collective.settings import configured, settings

pytestmark = [
    pytest.mark.providers,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(
        os.getenv("ENGRAM_PROVIDER_TESTS") != "1"
        or not configured(settings.groq_api_key if settings.agent_provider == "groq" else settings.anthropic_api_key)
        or (settings.decision_provider == "jev" and not configured(settings.jev_api_key)),
        reason="Requires configured real model and decision providers and explicit provider-test opt-in",
    ),
]


async def test_live_agent_and_mem0_fact_roundtrip():
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from collective.auth import Principal, register
    from collective.db import db, uid
    from collective.graph import graph
    from collective.memory import memory
    from collective.runtime import claim, create_run
    from collective.agents import execute_run

    await db.open()
    user = await register(
        f"provider-{uid()}@example.test",
        "Provider-integration-password-123",
        "Provider test",
        "Live provider verification",
    )
    row = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    actor = Principal(user, row["tenant_id"], "owner", "Provider test")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Live provider verification')",
        (project, actor.tenant_id),
    )
    await graph.ensure(actor.tenant_id)
    response = await memory.ingest(
        actor, project, "The owner of project ORCHID is Maya. The deadline is Friday at 14:00 UTC."
    )
    assert response["facts"], "Mem0 must extract actual sourced facts"
    bundle = await memory.context(actor, project, "Who owns project ORCHID?")
    assert any("Maya" in record["content"] for record in bundle["memories"])
    run = await create_run(
        actor,
        project,
        "Use memory_search to identify the owner of project ORCHID. State the owner's name explicitly and cite the actual evidence ID. Do not use web search.",
        "researcher",
    )
    leased = await claim("provider-verification", actor.tenant_id)
    assert leased["id"] == run["id"]
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    await execute_run(leased, saver)
    completed = await db.execute("SELECT status,result FROM runs WHERE id=%s", (run["id"],), one=True)
    assert completed["status"] == "completed"
    assert "Maya" in completed["result"]["summary"]
    assert completed["result"]["evidence_ids"]
