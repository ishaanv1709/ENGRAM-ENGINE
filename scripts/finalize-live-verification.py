"""Preserve a truthful quota-blocked report and stop only verification fixtures."""

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal
from collective.db import db
from collective.graph import graph
from collective.memory import memory
from collective.sandbox import docker_command


async def main():
    path = Path("data/collective/live-verification.json")
    report = json.loads(path.read_text())
    if report.get("passed"):
        raise RuntimeError("A passing workflow must not be replaced with a quota-blocked report")
    model = report["agent_model"]
    observed = [
        v.get("detail", "")
        for k, v in report.items()
        if k.startswith("task_failure_")
        and isinstance(v, dict)
        and model in v.get("detail", "")
        and ("per day" in v.get("detail", "").lower() or "daily quota" in v.get("detail", "").lower())
    ]
    if not observed:
        raise RuntimeError("No observed daily-quota error exists for the selected model")
    numbers = re.search(r"Limit (\d+), Used (\d+), Requested (\d+)", observed[-1])
    backup = path.with_name("live-verification-before-quota-finalization.json")
    if not backup.exists():
        backup.write_text(json.dumps(report, indent=2))
    await db.open()
    tenant, project = report["fixture"]["tenant"], report["fixture"]["project"]
    reason = f"Groq {model} daily token quota reached; remaining live verification is blocked."
    blocked = await db.execute(
        "UPDATE runs SET status='blocked',error=%s,revision=revision+1,lease_token=NULL,lease_until=NULL,updated_at=now() WHERE tenant_id=%s AND (status IN ('queued','running','waiting') OR (status='failed' AND error IN ('RateLimitError','DependencyUnavailable'))) RETURNING *",
        (reason, tenant),
    )
    for row in blocked:
        await graph.task(tenant, row)
    cancelled = await db.execute(
        "UPDATE runs r SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE r.tenant_id!=%s AND r.status IN ('queued','running','waiting') AND EXISTS(SELECT 1 FROM users u JOIN projects p ON p.id=r.project_id WHERE u.id=r.user_id AND u.email ~ '^(browser-|live-|provider-|artifact-|smoke-|restart-|integration-|retrieval-|memory-live-)' AND u.email LIKE '%%@example.test' AND p.name=ANY(%s)) RETURNING r.*",
        (
            tenant,
            [
                "Browser verification project",
                "Live provider workflow",
                "Live Groq artifacts",
                "HTTP verification fixture",
                "Integration fixture",
                "Retrieval fixture",
                "Live provider verification",
                "Restart continuity",
                "Live memory correction",
            ],
        ),
    )
    for row in cancelled:
        await graph.task(row["tenant_id"], row)
    rows = await db.execute(
        "SELECT id,role,status,result,error FROM runs WHERE tenant_id=%s ORDER BY created_at", (tenant,)
    )
    removed = []
    for run in rows:
        name = "engram-sandbox-" + run["id"]
        code, output, _ = await docker_command("inspect", "--format", '{{index .Config.Labels "engram.run"}}', name)
        if code == 0 and output.decode().strip() == run["id"]:
            code, _, _ = await docker_command("rm", "--force", name)
            if code == 0:
                removed.append(run["id"])
    member = await db.execute("SELECT user_id,role FROM memberships WHERE tenant_id=%s", (tenant,), one=True)
    actor = Principal(member["user_id"], tenant, member["role"], "Verification report")
    records = await memory.list(actor, project)
    artifacts = await db.execute("SELECT id,name,sha256 FROM artifacts WHERE tenant_id=%s", (tenant,))
    handoffs = await db.execute("SELECT id,acknowledged_at FROM handoffs WHERE tenant_id=%s", (tenant,))
    report.update(
        passed=False,
        failure={
            "type": "ProviderQuota",
            "message": reason,
            "observed_daily_limit": int(numbers[1]) if numbers else None,
            "observed_used_tokens": int(numbers[2]) if numbers else None,
            "observed_rejected_request_tokens": int(numbers[3]) if numbers else None,
        },
        workflow={
            "runs": rows,
            "artifacts": artifacts,
            "handoffs": handoffs,
            "procedures": [
                {"id": r["id"], "status": r["status"]}
                for r in records
                if r.get("metadata", {}).get("kind") == "workflow"
            ],
        },
        write_backs=await db.execute(
            "SELECT run_id,payload FROM events WHERE tenant_id=%s AND kind='memory.write_back'", (tenant,)
        ),
        prepared_resources=await db.execute(
            "SELECT run_id,payload FROM events WHERE tenant_id=%s AND kind='agent.resources_prepared'", (tenant,)
        ),
        cleanup={
            "blocked_fixture_tasks": len(blocked),
            "cancelled_other_fixture_tasks": len(cancelled),
            "stopped_fixture_containers": len(removed),
            "volumes_and_artifacts_preserved": True,
        },
    )
    path.write_text(json.dumps(report, indent=2, default=str))
    print(
        json.dumps(
            {
                "passed": False,
                "reason": reason,
                "runs": [{"role": r["role"], "status": r["status"]} for r in rows],
                "artifacts": len(artifacts),
                "handoffs": len(handoffs),
                "write_backs": len(report["write_backs"]),
                "procedures": report["workflow"]["procedures"],
                "cleanup": report["cleanup"],
            },
            default=str,
        )
    )
    await db.pool.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
