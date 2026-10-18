"""Build a meaningful new artifact version with real agents and independent checks.

The user-requested version proposal is explicit, not represented as an autonomous
curator decision. All source code, tests and verification are agent executions.
Run with the normal worker paused, as with the other live demo drivers.
"""
import asyncio
import json
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal
from collective.db import db
from collective.evidence import verified_check
from collective.memory import memory
from collective.procedures import bind_version
from collective.runtime import create_run

REPORT = Path("data/collective/versioned-demo.json")
drain = runpy.run_path(str(Path(__file__).with_name("verify-causal-demo.py")))["drain"]


def save(report):
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


async def main():
    await db.open()
    initial = json.loads(Path("data/collective/live-verification.json").read_text(encoding="utf-8"))
    assert initial.get("passed"), "Complete the team workflow first"
    fixture = initial["fixture"]
    member = await db.execute("SELECT user_id,role FROM memberships WHERE tenant_id=%s", (fixture["tenant"],), one=True)
    actor = Principal(member["user_id"], fixture["tenant"], member["role"], "Versioned release-capacity demo")
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {"fixture": fixture}
    if not report.get("builder_id"):
        builder = await create_run(actor, fixture["project"],
            "Implement a release planning capacity helper in calculator.py. Preserve add(a,b)=a+b for compatibility, "
            "and extend deployment_capacity(replicas, per_replica, reserved=0): require all three arguments to be non-negative "
            "integers, reject bools/non-integers with TypeError and negatives with ValueError. Return max(0, replicas * per_replica - reserved). "
            "The optional reserved parameter adds release headroom while preserving the old two-argument behavior. "
            "Write test_calculator.py with pytest tests covering add, normal capacity, zero, negatives, floats, bools, "
            "reserved capacity and reservations above total capacity. "
            "Use real sandbox tools to write both files, execute python -m pytest -q, publish both actual files, "
            "then team_handoff to an independent verifier to inspect the input validation and run those tests. "
            "Report actual artifact and check IDs. Do not browse or duplicate existing tasks.", "builder")
        report["builder_id"] = builder["id"]
        save(report)
    await drain(actor)
    builder = await db.execute("SELECT * FROM runs WHERE id=%s", (report["builder_id"],), one=True)
    assert builder["status"] == "completed", builder["status"]
    if not report.get("procedure_id"):
        previous = await db.execute("SELECT * FROM procedure_versions WHERE tenant_id=%s AND project_id=%s AND status='active' ORDER BY version DESC LIMIT 1",
            (actor.tenant_id, fixture["project"]), one=True)
        assert previous, "An independently verified first version must exist"
        checks = await db.execute("SELECT id,payload FROM events WHERE run_id=%s AND kind='tool.executed'", (builder["id"],))
        descriptor = {"kind": "workflow", "name": previous["family"],
            "purpose": "Validate release deployment capacity with reserved headroom and reject invalid numeric inputs before planning.",
            "preconditions": ["Python and pytest installed in the isolated sandbox", "Bound calculator.py and test_calculator.py artifacts available"],
            "steps": ["Read the exact bound artifact IDs", "Copy both files into the verifier's private workspace", "Execute python -m pytest -q", "Report real passing check event IDs"],
            "tools": ["artifact_read", "sandbox_execute"], "check_event_ids": [c["id"] for c in checks if verified_check(c["payload"])],
            "successes": 1, "proposal_origin": "explicit user-requested version upgrade"}
        record = await bind_version(actor, builder, descriptor)
        verifier = await create_run(actor, fixture["project"],
            f"Independently execute the proposed procedure {record['id']}. Inspect the exact bound capacity artifacts "
            "and preconditions, run the tests yourself in your own sandbox, then call procedure_verify with your own passing check IDs. "
            "Do not rewrite the bound files or propose another procedure.", "verifier")
        report.update(procedure_id=record["id"], version=record["metadata"]["version"], verifier_id=verifier["id"], manifest=record["metadata"]["artifact_manifest"])
        save(report)
    await drain(actor)
    record = await memory.get(actor, fixture["project"], report["procedure_id"])
    verifier = await db.execute("SELECT status,result FROM runs WHERE id=%s", (report["verifier_id"],), one=True)
    assert record["status"] == "active" and verifier["status"] == "completed"
    versions = await db.execute("SELECT version,manifest,status,verifier_run,baseline FROM procedure_versions WHERE tenant_id=%s AND project_id=%s AND family=%s ORDER BY version",
        (actor.tenant_id, fixture["project"], record["metadata"]["name"].casefold()))
    assert len(versions) >= 2 and versions[-1]["manifest"] != versions[0]["manifest"]
    report.update(passed=True, versions=versions, independent_result=verifier["result"])
    save(report)
    print(json.dumps({"passed": True, "version": report["version"], "procedure_id": report["procedure_id"], "version_count": len(versions)}), flush=True)
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
