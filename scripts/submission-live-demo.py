"""Real BYOK submission run. No model responses, artifacts or checks are simulated.

Reports and browser sessions stay in ignored runtime storage. Each phase is
explicit so an actual API/worker restart can occur between phases.
"""

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx

from collective.auth import Principal
from collective.byok import scope
from collective.coordination import resolve_claims, submit_claim, replan
from collective.db import db
from collective.graph import graph
from collective.memory import memory
from collective.procedures import metrics
from collective.evidence import verified_check
from collective.runtime import create_run
from collective.settings import base_settings

ROOT = Path("data/collective/submission-live-2026-10-18")
ROOT.mkdir(parents=True, exist_ok=True)
REPORT = ROOT / "report.json"
SESSION = ROOT / "session.json"


def save(report):
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


async def client():
    c = httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", timeout=180, headers={"X-Engram-Request": "1"})
    if SESSION.exists():
        for key, value in json.loads(SESSION.read_text()).items():
            c.cookies.set(key, value)
    return c


async def request(c, method, path, **kwargs):
    r = await c.request(method, path, **kwargs)
    r.raise_for_status()
    return r.json()


async def submit_team(c, actor, project, conversation, report):
    async with scope(actor):
        fact = await memory.ingest(
            actor,
            project["id"],
            "ORCHID release: Maya owns approval. Capacity is replicas multiplied by capacity per replica.",
        )
    report["ingestion"] = {"status": fact["status"], "fact_count": len(fact["facts"])}
    save(report)
    goal = (
        "Prepare the ORCHID release. Use team_dispatch to assign two parallel independent specialists: "
        "a researcher must do one web_search for FalkorDB official documentation and return a source URL; "
        "a builder must implement calculator.py with deployment_capacity(replicas,per_replica), multiply nonnegative integers, "
        "reject bools/nonintegers with TypeError and negatives with ValueError. Write test_calculator.py with pytest "
        "covering normal inputs, zero, negative, float and bool. Keep EACH source file under 450 characters; "
        "use concise parametrized tests. Run python -m pytest -q, publish both files, then team_handoff to an independent verifier. "
        "The verifier must copy and execute the real artifacts and cite check IDs. "
        "After all children complete, report actual evidence and artifacts. Do not duplicate completed work. "
        "Curate the outcome into sourced semantic memory and an independently verified reusable procedure."
    )
    run = await request(
        c, "POST", f"/projects/{project['id']}/runs", json={"objective": goal, "conversation_id": conversation["id"]}
    )
    report.update(root_run=run["id"], phase="team_running")
    save(report)
    print(json.dumps({"phase": report["phase"], "root_run": run["id"], "report": str(REPORT)}), flush=True)


async def main(stage):
    await db.open()
    try:
        async with await client() as c:
            if stage in {"start", "submit"}:
                if stage == "start":
                    assert not REPORT.exists(), "Preserve previous results; choose a fresh report directory"
                    await request(c, "POST", "/auth/start")
                    SESSION.write_text(json.dumps(dict(c.cookies)), encoding="utf-8")
                    me = await request(c, "GET", "/me")
                    for model, active, label in [
                        (base_settings.agent_model, True, "Submission main model"),
                        (base_settings.safeguard_model, False, "Submission admission model"),
                    ]:
                        connection = await request(
                            c,
                            "POST",
                            "/profile/connections",
                            json={
                                "provider": "groq",
                                "protocol": "chat",
                                "model": model,
                                "label": label,
                                "api_key": base_settings.groq_api_key,
                                "activate": active,
                            },
                        )
                        if not active:
                            await request(c, "POST", "/profile/policy", json={"connection_id": connection["id"]})
                    await request(
                        c, "POST", "/profile/services/langsearch", json={"api_key": base_settings.langsearch_api_key}
                    )
                    project = await request(
                        c, "POST", "/projects", json={"name": "ORCHID: live submission across restart"}
                    )
                    conversation = await request(
                        c, "POST", f"/projects/{project['id']}/conversations", json={"name": "ORCHID release evidence"}
                    )
                    report = {
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "model": base_settings.agent_model,
                        "fixture": {"user": me["id"], "tenant": me["workspace_id"], "project": project["id"]},
                        "conversation": conversation["id"],
                        "phase": "started",
                        "live_inference": True,
                        "limitations": [
                            "Single local run; not a general benchmark",
                            "Exact long repetitive tool argument fidelity probe failed; all generated artifacts require real execution checks",
                        ],
                    }
                    save(report)
                else:
                    report = json.loads(REPORT.read_text(encoding="utf-8"))
                    assert report["phase"] == "started", "Do not duplicate submitted work"
                    project = {"id": report["fixture"]["project"]}
                    conversation = {"id": report["conversation"]}
                    me = {"id": report["fixture"]["user"], "workspace_id": report["fixture"]["tenant"]}
                actor = Principal(me["id"], me["workspace_id"], "owner", "Submission demo")
                async with scope(actor):
                    await submit_team(c, actor, project, conversation, report)
                return
            report = json.loads(REPORT.read_text(encoding="utf-8"))
            f = report["fixture"]
            actor = Principal(f["user"], f["tenant"], "owner", "Submission demo")
            if stage == "status":
                rows = await db.execute(
                    "SELECT id,parent_id,role,status,error,created_at,updated_at FROM runs WHERE tenant_id=%s ORDER BY created_at",
                    (f["tenant"],),
                )
                usage = await metrics([r["id"] for r in rows])
                artifacts = await db.execute("SELECT id,name,sha256 FROM artifacts WHERE tenant_id=%s", (f["tenant"],))
                report.update(runs=rows, usage=usage, artifacts=artifacts)
                save(report)
                print(json.dumps({"runs": rows, "usage": usage, "artifacts": artifacts}, default=str), flush=True)
            elif stage == "use-20b":
                connection = await request(
                    c,
                    "POST",
                    "/profile/connections",
                    json={
                        "provider": "groq",
                        "protocol": "chat",
                        "model": "openai/gpt-oss-20b",
                        "label": "Submission completion, user-authorized 20B",
                        "api_key": base_settings.groq_api_key,
                        "activate": True,
                    },
                )
                report.setdefault("initial_model", report["model"])
                report["model"] = "openai/gpt-oss-20b"
                report.setdefault("model_changes", []).append(
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "model": report["model"],
                        "reason": "User explicitly authorized 20B after Qwen daily quota exhaustion",
                    }
                )
                save(report)
                result = await request(c, "POST", f"/profile/connections/{connection['id']}/test")
                report["completion_model_probe"] = result
                save(report)
                print(json.dumps(result))
            elif stage == "resume-failed":
                interrupted = []
                if report.get("model_changes"):
                    old_running = await db.execute(
                        "SELECT id,role,status,error FROM runs WHERE tenant_id=%s AND status='running' AND updated_at<%s",
                        (f["tenant"], report["model_changes"][-1]["at"]),
                    )
                    for row in old_running:
                        await request(c, "POST", f"/runs/{row['id']}/cancel")
                        interrupted.append(row)
                rows = await db.execute(
                    "SELECT id,role,status,error FROM runs WHERE tenant_id=%s AND status IN ('failed','blocked') ORDER BY created_at",
                    (f["tenant"],),
                )
                rows.extend(interrupted)
                report.setdefault("recovery_attempts", []).append(
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "prior_states": rows,
                        "reason": "Resume after verifier standalone-command recovery and provider-compatible final reporting fixes; actual previous failures retained",
                    }
                )
                save(report)
                resumed = []
                for row in sorted(rows, key=lambda row: row["role"] == "coordinator"):
                    if row["role"] == "coordinator":
                        pending = await db.execute(
                            "SELECT id FROM runs WHERE parent_id=%s AND status!='completed'", (row["id"],)
                        )
                        if pending:
                            continue
                    await request(c, "POST", f"/runs/{row['id']}/resume")
                    resumed.append(row["id"])
                print(json.dumps({"resumed": resumed}))
            elif stage == "causal-before":
                assert not report.get("old_fact"), "Already prepared"
                old = await memory.commit(
                    actor,
                    f["project"],
                    "ORCHID release roster: Maya owns release approval.",
                    metadata={"observed_at": "2026-10-17T09:00:00+00:00"},
                )
                await submit_claim(
                    actor,
                    f["project"],
                    "ORCHID release",
                    "approval owner",
                    "Maya",
                    old["id"],
                    "2026-10-17T09:00:00+00:00",
                )
                resolved = await resolve_claims(actor, f["project"], "ORCHID release", "approval owner")
                run = await create_run(
                    actor,
                    f["project"],
                    f"Read memory {resolved['memory_id']} using memory_read. Prepare a release approval routing recommendation for the named person. Cite the memory ID. Do not dispatch tasks or browse.",
                    "researcher",
                    context_scope="team",
                )
                report.update(old_source=old["id"], old_fact=resolved["memory_id"], old_action_run=run["id"])
                save(report)
                print(json.dumps({"phase": stage, "run": run["id"]}))
            elif stage == "correct":
                team_before = await db.execute(
                    "SELECT status,result FROM runs WHERE id=%s", (report["root_run"],), one=True
                )
                assert team_before["status"] == "completed", (
                    "Finish the real team workflow before correcting its context"
                )
                oldrun = await db.execute(
                    "SELECT status,result FROM runs WHERE id=%s", (report["old_action_run"],), one=True
                )
                assert oldrun["status"] == "completed", oldrun
                path = await graph.query(
                    f["tenant"],
                    "MATCH (t:Task {id:$task})-[:DEPENDS_ON]->(m:Memory {id:$fact}) RETURN t.id,m.id",
                    {"task": report["old_action_run"], "fact": report["old_fact"]},
                )
                assert path, "Actual agent must have read the old memory"
                observed_at = datetime.now(timezone.utc).isoformat()
                new = await memory.commit(
                    actor,
                    f["project"],
                    "ORCHID release roster update: Priya now owns release approval.",
                    metadata={"observed_at": observed_at},
                )
                await submit_claim(
                    actor,
                    f["project"],
                    "ORCHID release",
                    "approval owner",
                    "Priya",
                    new["id"],
                    observed_at,
                )
                resolved = await resolve_claims(actor, f["project"], "ORCHID release", "approval owner")
                correction = await db.execute(
                    "SELECT id,payload FROM events WHERE tenant_id=%s AND kind='memory.corrected' AND payload->>'old'=%s ORDER BY id DESC LIMIT 1",
                    (f["tenant"], report["old_fact"]),
                    one=True,
                )
                assert correction and report["old_action_run"] in correction["payload"]["affected_runs"]
                stale = await db.execute(
                    "SELECT status,revision FROM runs WHERE id=%s", (report["old_action_run"],), one=True
                )
                assert stale["status"] == "stale"
                report.update(
                    team_before_correction=team_before,
                    original_action=oldrun,
                    direct_reader_path=path,
                    correction=correction,
                    new_fact=resolved["memory_id"],
                    stale_action=stale,
                    claims=await db.execute(
                        "SELECT id,value,source_id,source_time FROM knowledge_claims WHERE tenant_id=%s ORDER BY source_time",
                        (f["tenant"],),
                    ),
                    phase="ready_for_restart",
                )
                save(report)
                print(
                    json.dumps(
                        {
                            "phase": report["phase"],
                            "correction_event": correction["id"],
                            "old_action_status": stale["status"],
                        }
                    )
                )
            elif stage == "after-restart":
                assert report["phase"] == "ready_for_restart"
                proof = json.loads(Path("data/collective/restart-process-proof.json").read_text(encoding="utf-8-sig"))
                assert proof["actual_app_process_restart"]
                assert datetime.fromisoformat(proof["verified_at"].replace("Z", "+00:00")) > datetime.fromisoformat(
                    report["updated_at"]
                )
                fresh = await request(c, "GET", "/me")
                assert fresh["id"] == f["user"]
                fact = await memory.get(actor, f["project"], report["new_fact"])
                assert fact["status"] == "active" and "Priya" in fact["content"]
                checkpoints = await db.execute(
                    "SELECT count(*) AS count FROM checkpoints WHERE thread_id=%s",
                    (f["tenant"] + ":" + report["root_run"],),
                    one=True,
                )
                assert checkpoints["count"] > 0, "Original live agent checkpoints did not persist"
                artifacts = await db.execute(
                    "SELECT id,path,sha256 FROM artifacts WHERE tenant_id=%s AND project_id=%s",
                    (f["tenant"], f["project"]),
                )
                for artifact in artifacts:
                    assert hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
                messages = await request(c, "GET", f"/conversations/{report['conversation']}/messages")
                assert len(messages) >= 2
                report["persistence"] = {
                    "session_survived": True,
                    "checkpoint_rows": checkpoints["count"],
                    "artifact_hashes_verified": len(artifacts),
                    "messages": len(messages),
                    "corrected_fact_active": True,
                }
                plan = await replan(actor, f["project"], report["correction"]["id"])
                report.update(restart=proof, replan=plan, phase="replanning_after_restart")
                save(report)
                print(json.dumps({"phase": report["phase"], "plan": plan["new_plan_id"]}))
            elif stage == "repair-replan":
                plan = await replan(actor, f["project"], report["correction"]["id"], replace_failed=True)
                report["replan"] = plan
                save(report)
                print(json.dumps({"replacement_plan": plan["new_plan_id"]}))
            elif stage == "benchmark-baseline":
                assert not report.get("comparison"), "Preserve earlier trials"
                pending = await db.execute(
                    "SELECT id FROM runs WHERE tenant_id=%s AND status IN ('queued','running','waiting')",
                    (f["tenant"],),
                )
                assert not pending, "Let other work in this demo finish before timing the comparison"
                procedure = await db.execute(
                    "SELECT * FROM procedure_versions WHERE tenant_id=%s AND project_id=%s AND status='active' ORDER BY version DESC LIMIT 1",
                    (f["tenant"], f["project"]),
                    one=True,
                )
                assert procedure, "Real independent procedure activation must finish first"
                run = await create_run(
                    actor,
                    f["project"],
                    "Independently verify this exact known artifact bundle in a fresh sandbox. "
                    "Tools are already listed; no capability discovery is needed. First call artifact_read once for EACH exact argument object below. "
                    "The destination is required to COPY each file; omitting it only reads the file and leaves the sandbox empty. "
                    + json.dumps([{"artifact_id": a["id"], "destination": a["name"]} for a in procedure["manifest"]])
                    + " Then call sandbox_execute with command='python -m pytest -q' and report real check IDs. "
                    "Do not change files, research or propose procedures. This supplies known correct artifacts, not a code generation baseline.",
                    "verifier",
                    context_scope="auto",
                    auto_curate=False,
                )
                report["comparison"] = {
                    "procedure_id": procedure["id"],
                    "version": procedure["version"],
                    "manifest": procedure["manifest"],
                    "baseline_run": run["id"],
                    "method": "One sequential live-model comparison: known exact artifact bundle versus active verified procedure. Identical artifacts and pytest command; same provider/model. Counts include policy/Mem0 calls attributed to each direct verifier run. Automatic post-run curation is disabled for both arms to isolate verification and avoid background inference contention. Wall timing includes queue, startup, model waits and checks; queue/startup is also shown separately. No code-generation savings claim.",
                    "limitations": [
                        "One pair is observational, not a reliable speed benchmark",
                        "Fixed baseline-first order and warm shared services can affect timing; no randomized multi-pair estimate",
                        "Provider failures and internal SDK retries may have unknown billed tokens",
                        "Calls made before receipt instrumentation are excluded and disclosed",
                    ],
                }
                save(report)
                print(json.dumps({"baseline_run": run["id"]}))
            elif stage == "benchmark-reuse":
                comparison = report["comparison"]
                assert not comparison.get("reuse_run"), "Do not duplicate trials"
                baseline = await db.execute(
                    "SELECT status FROM runs WHERE id=%s", (comparison["baseline_run"],), one=True
                )
                assert baseline["status"] == "completed", baseline
                pending = await db.execute(
                    "SELECT id FROM runs WHERE tenant_id=%s AND status IN ('queued','running','waiting')",
                    (f["tenant"],),
                )
                assert not pending, "Let baseline curation finish before the reuse timing starts"
                run = await create_run(
                    actor,
                    f["project"],
                    f"Reuse the already active verified procedure {comparison['procedure_id']} in this new session. "
                    "Tools are already listed; no capability discovery is needed. Runtime has already copied the exact bound files into your sandbox. "
                    "Call memory_read once for that exact procedure, then sandbox_execute with command='python -m pytest -q'. "
                    "Report real check IDs. Do not change files, research or propose procedures. This procedure is already active; do not activate it again.",
                    "verifier",
                    context_scope="auto",
                    auto_curate=False,
                )
                comparison["reuse_run"] = run["id"]
                save(report)
                print(json.dumps({"reuse_run": run["id"]}))
            elif stage == "evidence":
                comparison = report["comparison"]
                trials = {}
                for arm in ("baseline", "reuse"):
                    run_id = comparison[arm + "_run"]
                    run = await db.execute(
                        "SELECT status,result,created_at,updated_at FROM runs WHERE id=%s", (run_id,), one=True
                    )
                    events = await db.execute(
                        "SELECT id,kind,payload,created_at FROM events WHERE run_id=%s ORDER BY id", (run_id,)
                    )
                    assert run["status"] == "completed", {"arm": arm, "status": run["status"]}
                    checks = [e for e in events if e["kind"] == "tool.executed" and verified_check(e["payload"])]
                    assert checks, "No independently passing check"
                    receipts = [e for e in events if e["kind"] == "model.provider_receipt"]
                    assert receipts, "Missing provider receipts"
                    known = [e for e in receipts if e["payload"]["status"] == "success" and e["payload"].get("usage")]
                    started = next(e["created_at"] for e in events if e["kind"] == "agent.started")
                    trials[arm] = {
                        "run_id": run_id,
                        "status": run["status"],
                        "model": report["model"],
                        "provider_calls_observed": len(receipts),
                        "successful_calls_with_usage": len(known),
                        "provider_failed_calls": sum(e["payload"]["status"] == "failed" for e in receipts),
                        "model_tokens_observed": sum(e["payload"]["usage"]["total_tokens"] for e in known),
                        "elapsed_seconds": (run["updated_at"] - run["created_at"]).total_seconds(),
                        "active_agent_seconds": (run["updated_at"] - started).total_seconds(),
                        "queue_and_prepare_seconds": (started - run["created_at"]).total_seconds(),
                        "check_event_ids": [e["id"] for e in checks],
                        "checks": [
                            {
                                "event_id": e["id"],
                                **{k: e["payload"].get(k) for k in ("command", "exit_code", "stdout", "stderr")},
                            }
                            for e in checks
                        ],
                        "agent_loop": await metrics([run_id]),
                        "provider_receipt_event_ids": [e["id"] for e in receipts],
                        "provider_receipts": [
                            {"event_id": e["id"], **e["payload"]} for e in receipts
                        ],
                    }
                comparison["trials"] = trials
                comparison["signed_savings"] = {
                    key: trials["baseline"][key] - trials["reuse"][key]
                    for key in ("provider_calls_observed", "model_tokens_observed", "elapsed_seconds")
                }
                receipt = await db.execute(
                    "SELECT * FROM procedure_uses WHERE procedure_id=%s AND run_id=%s",
                    (comparison["procedure_id"], comparison["reuse_run"]),
                    one=True,
                )
                assert receipt and receipt["completed_at"], "Missing validated reuse receipt"
                report["reuse_receipt"] = receipt
                plan = await db.execute(
                    "SELECT status,result FROM runs WHERE id=%s", (report["replan"]["new_plan_id"],), one=True
                )
                assert plan["status"] == "completed", plan
                assert "Priya" in json.dumps(plan["result"]), "Revised action must name the current owner"
                path = await graph.query(
                    f["tenant"],
                    "MATCH (n:Task {id:$n})-[:REPLANS]->(o:Task {id:$o}) RETURN n.id,o.id",
                    {"n": report["replan"]["new_plan_id"], "o": report["old_action_run"]},
                )
                assert path
                root = await db.execute("SELECT status,result FROM runs WHERE id=%s", (report["root_run"],), one=True)
                assert report["team_before_correction"]["status"] == "completed"
                assert root["status"] in {"completed", "stale"}, root
                messages = await db.execute(
                    "SELECT role,content FROM messages WHERE conversation_id=%s ORDER BY created_at",
                    (report["conversation"],),
                )
                assert len(messages) >= 2
                handoffs = await db.execute(
                    "SELECT id,from_run,to_run,acknowledged_at FROM handoffs WHERE tenant_id=%s", (f["tenant"],)
                )
                assert handoffs and all(h["acknowledged_at"] for h in handoffs)
                completion_events = await db.execute(
                    "SELECT id,run_id,created_at FROM events WHERE tenant_id=%s AND kind='task.completed' AND id<%s ORDER BY id",
                    (f["tenant"], report["correction"]["id"]),
                )
                assert set(report["correction"]["payload"]["affected_runs"]) <= {e["run_id"] for e in completion_events}
                report["workflow_completion_events"] = completion_events
                dependency_limit = f"Conservative memory retrieval dependencies invalidated {len(report['correction']['payload']['affected_runs'])} historical fixture runs. This is not minimal semantic impact analysis."
                if dependency_limit not in report["limitations"]:
                    report["limitations"].append(dependency_limit)
                for limit in (
                    "Recovered multi-attempt execution with an explicitly authorized Qwen-to-Groq-20B model change, not a first-attempt or all-Qwen pass. Stopped replans and excluded debug comparison pilots are retained.",
                    "The correction was supplied explicitly; claim timestamps select a winner under policy and do not establish source authority.",
                    "The public demo depends on its host laptop and a temporary Cloudflare tunnel. The existing film predates this live validation.",
                ):
                    if limit not in report["limitations"]:
                        report["limitations"].append(limit)
                if not report.get("benchmark_event_id"):
                    benchmark_event = await db.event(
                        f["tenant"],
                        "procedure.benchmark",
                        {
                            "project_id": f["project"],
                            "procedure_id": comparison["procedure_id"],
                            "kind": "live_model_comparison",
                            "run_ids": [comparison["baseline_run"], comparison["reuse_run"]],
                            "method": comparison["method"],
                            "comparison": comparison,
                            "limitations": "One observed live pair, not a general performance guarantee. SDK internal retries are not individually counted; failed-call tokens can be unknown. Positive signed differences favor reuse; negative values mean overhead.",
                        },
                    )
                    report["benchmark_event_id"] = benchmark_event["id"]
                report.update(
                    revised_action=plan,
                    replan_path=path,
                    root_result=root,
                    persisted_messages=len(messages),
                    handoffs=handoffs,
                    phase="completed",
                    passed=True,
                )
                save(report)
                print(json.dumps({"passed": True, "comparison": comparison}, default=str))
            else:
                raise ValueError("Unknown phase")
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(sys.argv[1]))
