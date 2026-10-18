"""Create explicitly labeled infrastructure evidence, with no model calls.

Uses production graph/runtime/tool/sandbox code, never substitutes an LLM or
claims this deterministic fixture is autonomous agent-team verification.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal, register
from collective.coordination import submit_claim, resolve_claims, replan
from collective.db import db, uid
from collective.memory import memory
from collective.runtime import create_run, claim, finish
from collective.tools import RunTools
from collective.agents import prepare_resources
from collective.procedures import complete_use

REPORT = Path("data/collective/film-infrastructure-evidence.json")


async def main():
    assert not REPORT.exists(), "Preserve existing evidence rather than silently replacing it"
    await db.open()
    email = f"film-infrastructure-{uid()}@example.test"
    user = await register(email, "Integration-password-123", "Infrastructure validation", "Real service validation")
    tenant = (await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True))["tenant_id"]
    actor = Principal(user, tenant, "owner", "Infrastructure validation")
    project = uid()
    await db.execute("INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Infrastructure validation · no model inference')", (project, tenant))
    report = {"fixture": {"tenant": tenant, "project": project, "email": email},
        "execution_mode": "Production services and tools invoked by an integration driver; no LLM calls or mocked services",
        "model_tokens": 0, "autonomous_team_verified": False}

    async def task(role, objective):
        row = await create_run(actor, project, objective + " [Infrastructure fixture; no model inference]", role, context_scope="team")
        leased = await claim("film-infrastructure", tenant)
        assert leased["id"] == row["id"]
        kit = RunTools(actor, leased)
        core, optional = kit.build()
        return leased, kit, {tool.name: tool for tool in core + optional}, core

    versions = []
    for version in (1, 2):
        source = ("def deployment_capacity(replicas, per_replica):\n    return replicas * per_replica\n" if version == 1 else
            "def deployment_capacity(replicas, per_replica, reserved=0):\n    values = (replicas, per_replica, reserved)\n    if any(type(value) is not int for value in values):\n        raise TypeError('capacity inputs must be integers')\n    if any(value < 0 for value in values):\n        raise ValueError('capacity inputs must be non-negative')\n    return max(0, replicas * per_replica - reserved)\n")
        tests = ("from capacity import deployment_capacity\ndef test_capacity():\n    assert deployment_capacity(3, 25) == 75\n" if version == 1 else
            "import pytest\nfrom capacity import deployment_capacity\n@pytest.mark.parametrize('args,expected', [((3,25),75),((0,25),0),((3,25,10),65),((3,25,100),0)])\ndef test_capacity(args,expected):\n    assert deployment_capacity(*args) == expected\n@pytest.mark.parametrize('args', [(True,25),(3,2.5),(3,25,False)])\ndef test_types(args):\n    with pytest.raises(TypeError): deployment_capacity(*args)\n@pytest.mark.parametrize('args', [(-1,25),(3,-1),(3,25,-1)])\ndef test_negatives(args):\n    with pytest.raises(ValueError): deployment_capacity(*args)\n")
        builder, kit, tools, _ = await task("builder", f"Validate release-capacity artifact version {version}")
        try:
            for name, content in [("capacity.py", source), ("test_capacity.py", tests)]:
                await tools["sandbox_write"].ainvoke({"path": name, "content": content})
            checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            for name in ("capacity.py", "test_capacity.py"):
                await tools["artifact_publish"].ainvoke({"path": name})
            proposal = await tools["procedure_propose"].ainvoke({"name": "Release capacity validation", "purpose": "Validate deployment capacity and reserved headroom", "preconditions": ["Exact bound artifacts", "Python and pytest in the isolated sandbox"], "steps": ["Copy the bound capacity.py and test_capacity.py files", "Execute python -m pytest -q", "Retain actual check event IDs"], "tool_names": ["artifact_read", "sandbox_execute"], "check_event_ids": [checked["check_event_id"]]})
            await finish(builder, "completed", {"summary": "Infrastructure driver executed real source tests and published artifacts; no model inference", "check_event_ids": [checked["check_event_id"]]})
        finally:
            await kit.close()
        verifier = await claim("film-infrastructure", tenant)
        assert verifier["id"] == proposal["verification_task"]
        verification = RunTools(actor, verifier)
        core, optional = verification.build()
        vt = {tool.name: tool for tool in core + optional}
        try:
            await prepare_resources(verification, core, [])
            checked = await vt["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            record = await vt["procedure_verify"].ainvoke({"procedure_id": proposal["procedure_id"], "check_event_ids": [checked["check_event_id"]]})
            await finish(verifier, "completed", {"summary": "Independent sandbox checks executed by infrastructure driver; no model inference", "check_event_ids": [checked["check_event_id"]]})
            versions.append({"id": record["id"], "version": record["metadata"]["version"], "manifest": record["metadata"]["artifact_manifest"], "check": checked})
        finally:
            await verification.close()
    reuse, kit, tools, core = await task("verifier", f"Reuse the already active verified procedure {versions[-1]['id']}")
    try:
        await prepare_resources(kit, core, [])
        checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
        assert checked["verification_passed"]
        record = await memory.get(actor, project, versions[-1]["id"])
        actual = {item["name"]: hashlib.sha256(await kit.sandbox.read(item["name"])).hexdigest() for item in record["metadata"]["artifact_manifest"]}
        await complete_use(actor, reuse, record, actual)
        await finish(reuse, "completed", {"summary": "Infrastructure procedure reuse verified with actual tests and hashes; no model inference", "check_event_ids": [checked["check_event_id"]]})
    finally:
        await kit.close()
    sources = []
    for owner, timestamp in [("Maya", "2026-10-14T09:00:00+00:00"), ("Priya", "2026-10-15T09:00:00+00:00")]:
        sources.append(await memory.commit(actor, project, f"Controlled sample release roster: {owner} owns ORCHID release approval.", metadata={"kind": "infrastructure_sample", "observed_at": timestamp, "sample_data": True}))
    await submit_claim(actor, project, "ORCHID release", "approval owner", "Maya", sources[0]["id"], "2026-10-14T09:00:00+00:00")
    old = await resolve_claims(actor, project, "ORCHID release", "approval owner")
    reader, kit, tools, _ = await task("researcher", "Read the currently selected release approver")
    fact = await tools["memory_read"].ainvoke({"memory_id": old["memory_id"]})
    await finish(reader, "completed", {"summary": "Infrastructure memory_read returned: " + fact["content"] + ". No model inference.", "evidence_ids": [fact["id"]]})
    await kit.close()
    claimants = []
    for role in ("researcher", "curator"):
        claimants.append(await task(role, "Preserve a sourced release approval claim"))
    async def publish(item, owner, source, timestamp):
        run, toolkit, tools, _ = item
        value = await tools["claim_submit"].ainvoke({"subject": "ORCHID release", "predicate": "approval owner", "value": owner, "source_id": source["id"], "source_time": timestamp})
        await finish(run, "completed", {"summary": "Infrastructure driver submitted the real claim; no model inference", "claim_id": value["id"]})
        await toolkit.close()
        return value
    claims = await asyncio.gather(publish(claimants[0], "Maya", sources[0], "2026-10-14T09:00:00+00:00"), publish(claimants[1], "Priya", sources[1], "2026-10-15T09:00:00+00:00"))
    resolved = await resolve_claims(actor, project, "ORCHID release", "approval owner")
    assert next(c for c in claims if c["id"] == resolved["winner_id"])["value"] == "Priya"
    assert (await db.execute("SELECT status FROM runs WHERE id=%s", (reader["id"],), one=True))["status"] == "stale"
    correction = await db.execute("SELECT id FROM events WHERE tenant_id=%s AND kind='memory.corrected' ORDER BY id DESC LIMIT 1", (tenant,), one=True)
    plan = await replan(actor, project, correction["id"])
    pending = await claim("film-infrastructure", tenant)
    assert pending["id"] == plan["new_plan_id"]
    await finish(pending, "blocked", {"summary": "Revised plan created from Priya approval evidence. Autonomous execution is not verified: Groq daily token quota exhausted."}, "Provider quota exhausted; no model call attempted")
    report.update(versions=versions, claims=claims, resolution=resolved, plan=plan,
        reuse=await db.execute("SELECT * FROM procedure_uses WHERE run_id=%s", (reuse["id"],), one=True),
        infrastructure_passed=True, revised_plan_executed=False)
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"infrastructure_passed": True, "autonomous_team_verified": False, "versions": len(versions), "concurrent_claims": len(claims), "revised_plan_status": "blocked", "fixture": report["fixture"]}), flush=True)
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
