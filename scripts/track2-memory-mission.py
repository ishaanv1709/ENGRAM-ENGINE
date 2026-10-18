"""Fresh-session persistent-memory team mission using explicitly authorized models.

Startup input is a supplied release observation, not a model-discovered fact.
The team must actually coordinate, reuse checked artifacts, hand off and curate.
Perform restart-app.ps1 after ready, before revise. No automatic model fallback.
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
from collective.byok import scope, decrypt
from collective.coordination import replan
from collective.db import db, uid
from collective.graph import graph
from collective.memory import memory
from collective.runtime import create_run

ROOT = Path("data/collective/track2-upgrade")
FILE = ROOT / "memory-mission.json"


def save(r):
    r["updated_at"] = datetime.now(timezone.utc).isoformat()
    FILE.write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")


def processes():
    return [p for p in json.loads(Path("data/collective/processes.json").read_text(encoding="utf-8-sig")) if p["Module"] in {"collective.serve", "collective.agents"}]


async def tree(run_id):
    return await db.execute("WITH RECURSIVE t AS (SELECT * FROM runs WHERE id=%s UNION ALL SELECT r.* FROM runs r JOIN t ON r.parent_id=t.id) SELECT id,role,status,result,error FROM t", (run_id,))


async def main(phase):
    await db.open()
    try:
        old = json.loads(Path("data/collective/submission-live-2026-10-18/report.json").read_text())
        f = old["fixture"]
        actor = Principal(f["user"], f["tenant"], "owner", "Memory mission")
        if phase == "start":
            assert not FILE.exists(), "Preserve previous attempts"
            connection = await db.execute("SELECT provider,model FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active", (actor.user_id, actor.tenant_id), one=True)
            assert connection == {"provider": "groq", "model": "openai/gpt-oss-20b"}
            source = await memory.commit(actor, f["project"], "ASTER release approval owner is Maya.", memory_type="semantic", category="critical", visibility="user",
                                         metadata={"kind": "supplied_release_record", "release": "ASTER"})
            conversation = uid()
            await db.execute("INSERT INTO conversations(id,tenant_id,project_id,user_id,title) VALUES (%s,%s,%s,%s,'ASTER: new session, remembered procedure')", (conversation, actor.tenant_id, f["project"], actor.user_id))
            procedure = old["comparison"]["procedure_id"]
            goal = (
                f"Prepare ASTER release evidence using saved team knowledge. The approval source is memory {source['id']}. "
                "Use team_dispatch to create exactly two independent specialists, with dependencies=[], so their work can overlap. "
                f"First dispatch role verifier with memory_ids=[\"{procedure}\"], auto_curate=false, and an objective starting exactly "
                f"'Reuse the already active verified procedure {procedure}'. That verifier must execute the bound calculator tests and report real check IDs, not rebuild files. "
                f"Then dispatch role researcher with memory_ids=[\"{source['id']}\"], auto_curate=false. Its objective: read the supplied approval memory, "
                "state the current ASTER approval route, and hand off to curator using team_handoff, evidence_ids containing that exact approval memory, "
                "artifact_ids=[] and check_event_ids=[]. The receiving curator's remaining objective must start 'Consolidate the outcome of task ' followed by the researcher's own task ID. "
                "It must save one concise ASTER approval observation through memory_write with source_ids containing that approval memory. No procedure proposal is needed. "
                "After the handoff, the researcher should report once and stop. The curator should report its committed write-back and stop. "
                "Do not dispatch a builder or repeat completed work. Wait for all descendants and report the actual current approver, passing test evidence, reused procedure and acknowledged handoff."
            )
            run = await create_run(actor, f["project"], goal, conversation=conversation, auto_curate=False, memory_ids=[source["id"]])
            await db.execute("INSERT INTO messages(id,conversation_id,tenant_id,role,content) VALUES (%s,%s,%s,'user',%s)", (uid(), conversation, actor.tenant_id, goal))
            r = {"phase": "team_running", "passed": False, "model": connection["model"], "root_run": run["id"],
                 "project_id": f["project"], "conversation": conversation, "owner_source": source["id"], "procedure_id": procedure,
                 "limitations": ["The ownership observation is supplied explicitly; the model does not discover or authenticate the source.", "Existing procedure and artifacts were learned and independently checked in the earlier recovered session."]}
            save(r)
            print(json.dumps({"phase": r["phase"], "root_run": run["id"]}))
        else:
            r = json.loads(FILE.read_text())
            if phase == "cancel-for-retry":
                prior_tree = await tree(r["root_run"])
                cancelled_children = []
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", timeout=30, headers={"X-Engram-Request": "1"}) as client:
                    for key, value in json.loads(Path("data/collective/submission-live-2026-10-18/session.json").read_text()).items():
                        client.cookies.set(key, value)
                    response = await client.post(f"/runs/{r['root_run']}/cancel")
                    response.raise_for_status()
                    for task in prior_tree:
                        if task["id"] != r["root_run"] and task["status"] in {"queued", "running", "waiting", "awaiting_handoff"}:
                            response = await client.post(f"/runs/{task['id']}/cancel")
                            response.raise_for_status()
                            cancelled_children.append(task["id"])
                r.setdefault("previous_attempts", []).append({"root_run": r["root_run"], "conversation": r["conversation"], "tree": await tree(r["root_run"]),
                    "cancelled_pending_children": cancelled_children,
                    "reason": "Preserved unsuccessful scope/budget recovery; start a clean 120B task after clarifying private-reference scope"})
                r["phase"] = "cancelled_for_explicit_scope_retry"
                save(r)
                print(json.dumps({"cancelled": r["root_run"], "history_preserved": True}))
            elif phase == "restart-team":
                assert r["phase"] == "cancelled_for_explicit_scope_retry"
                selected = await db.execute("SELECT provider,model FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active", (actor.user_id, actor.tenant_id), one=True)
                assert selected == {"provider": "groq", "model": "openai/gpt-oss-120b"}
                source, procedure = r["owner_source"], r["procedure_id"]
                goal = (
                    f"Prepare ASTER release evidence. Your private approval memory is {source}; private verified procedure is {procedure}. "
                    "Use team_dispatch to create exactly two independent specialists with dependencies=[], context_scope='auto' and auto_curate=false. "
                    "'team' scope means shared-memory-only and cannot read these private records. Do not remove bindings. "
                    f"First create verifier with memory_ids=['{procedure}'] and objective starting 'Reuse the already active verified procedure {procedure}'. "
                    "It must run the existing calculator's real tests and report check IDs; do not rebuild files. "
                    f"Then create researcher with memory_ids=['{source}']. It must state the ASTER approver from that supplied memory, "
                    f"then use team_handoff to curator with evidence_ids=['{source}'], artifact_ids=[] and check_event_ids=[]. "
                    "The curator's remaining objective must start 'Consolidate the outcome of task ' followed by the researcher's actual task ID. "
                    "Ask it to save one concise sourced ASTER approval observation using memory_write, then report and stop. "
                    "Researcher reports once after handoff. Do not create builders or duplicate finished tasks. Wait for all descendants and report "
                    "the actual approver, passing checks, reused procedure and acknowledged handoff."
                )
                conversation = uid()
                await db.execute("INSERT INTO conversations(id,tenant_id,project_id,user_id,title) VALUES (%s,%s,%s,%s,'ASTER: explicit private scope, Groq120B')", (conversation, actor.tenant_id, f["project"], actor.user_id))
                run = await create_run(actor, f["project"], goal, conversation=conversation, auto_curate=False, memory_ids=[source])
                await db.execute("INSERT INTO messages(id,conversation_id,tenant_id,role,content) VALUES (%s,%s,%s,'user',%s)", (uid(), conversation, actor.tenant_id, goal))
                r.update(root_run=run["id"], conversation=conversation, phase="team_running", model=selected["model"])
                r.pop("blocker", None)
                save(r)
                print(json.dumps({"root_run": run["id"], "model": selected["model"], "prior_attempts_preserved": len(r["previous_attempts"])}))
            elif phase == "use-120b":
                assert r["phase"] == "blocked_provider_quota", "Do not restart or overwrite a running experiment"
                selected = await db.execute("SELECT * FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active", (actor.user_id, actor.tenant_id), one=True)
                assert selected and selected["provider"] == "groq"
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", timeout=180, headers={"X-Engram-Request": "1"}) as client:
                    for key, value in json.loads(Path("data/collective/submission-live-2026-10-18/session.json").read_text()).items():
                        client.cookies.set(key, value)
                    response = await client.post("/profile/connections", json={
                        "provider": "groq", "protocol": "chat", "model": "openai/gpt-oss-120b",
                        "label": "User-authorized 120B mission recovery", "api_key": decrypt(selected["encrypted_key"]), "activate": True,
                    })
                    response.raise_for_status()
                    identity = response.json()["id"]
                    r.setdefault("initial_model", r["model"])
                    r["model"] = "openai/gpt-oss-120b"
                    r.setdefault("model_changes", []).append({"at": datetime.now(timezone.utc).isoformat(), "model": r["model"], "reason": "User explicitly authorized 120B after Groq20B daily quota exhaustion"})
                    save(r)
                    response = await client.post(f"/profile/connections/{identity}/test")
                    r["recovery_model_probe"] = {"status_code": response.status_code, "response": response.json()}
                    save(r)
                    response.raise_for_status()
                    assert response.json()["passed"]
                    response = await client.post(f"/runs/{r['root_run']}/resume")
                    response.raise_for_status()
                    r["phase"] = "team_running"
                    save(r)
                    print(json.dumps({"model": r["model"], "probe": r["recovery_model_probe"], "resumed": r["root_run"]}))
            elif phase == "resume":
                current = await db.execute("SELECT status,error FROM runs WHERE id=%s", (r["root_run"],), one=True)
                assert current["status"] in {"blocked", "failed"}
                r.setdefault("recovery_attempts", []).append({"at": datetime.now(timezone.utc).isoformat(), **current})
                save(r)
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", timeout=30, headers={"X-Engram-Request": "1"}) as client:
                    for key, value in json.loads(Path("data/collective/submission-live-2026-10-18/session.json").read_text()).items():
                        client.cookies.set(key, value)
                    response = await client.post(f"/runs/{r['root_run']}/resume")
                    response.raise_for_status()
                r["phase"] = "team_running"
                r.pop("blocker", None)
                save(r)
                print(json.dumps({"resumed": r["root_run"], "previous_state": current}))
            elif phase in {"status", "watch", "watch-plan"}:
                previous = None
                while True:
                    rows = await tree(r["revised_plan"]["new_plan_id"] if phase == "watch-plan" else r["root_run"])
                    running = [x["id"] for x in rows if x["status"] == "running" and x["id"] != r["root_run"]]
                    if phase != "watch-plan" and len(running) >= 2 and not r.get("parallel_snapshot"):
                        r["parallel_snapshot"] = {"at": datetime.now(timezone.utc).isoformat(), "run_ids": running,
                                                   "scope": "Simultaneously running worker tasks, including preparation; not a claim of simultaneous provider inference"}
                        save(r)
                    summary = [{k: x[k] for k in ("id", "role", "status", "error")} for x in rows]
                    if summary != previous:
                        print(json.dumps(summary), flush=True)
                        previous = summary
                    if phase == "status" or all(x["status"] == "completed" for x in rows) or any(x["status"] in {"failed", "blocked", "cancelled", "stale"} for x in rows):
                        break
                    await asyncio.sleep(5)
            elif phase == "ready":
                rows = await tree(r["root_run"])
                assert rows and all(x["status"] == "completed" for x in rows), [{"role": x["role"], "status": x["status"]} for x in rows]
                assert {"coordinator", "researcher", "verifier", "curator"} <= {x["role"] for x in rows}
                assert "Maya" in next(x for x in rows if x["id"] == r["root_run"])["result"]["summary"]
                ids = [x["id"] for x in rows]
                writebacks = await db.execute("SELECT id,run_id,payload FROM events WHERE run_id=ANY(%s) AND kind='memory.write_back' AND payload->>'status'='committed'", (ids,))
                assert writebacks and any(e["payload"].get("source_ids") and e["payload"].get("fact_ids") for e in writebacks)
                handoffs = await db.execute("SELECT id,from_run,to_run,acknowledged_at FROM handoffs WHERE from_run=ANY(%s)", (ids,))
                assert handoffs and all(h["acknowledged_at"] for h in handoffs)
                uses = await db.execute("SELECT run_id,completed_at FROM procedure_uses WHERE procedure_id=%s AND run_id=ANY(%s)", (r["procedure_id"], ids))
                assert uses and all(u["completed_at"] for u in uses)
                assert all(x["role"] != "builder" for x in rows)
                checkpoints = await db.execute("SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s", (f"{actor.tenant_id}:{r['root_run']}",), one=True)
                assert checkpoints["n"] > 0
                r.update(phase="ready_for_restart", completed_team=rows, writebacks=writebacks, handoffs=handoffs, uses=uses,
                         processes_before=processes(), root_checkpoint_rows=checkpoints["n"])
                save(r)
                print(json.dumps({"phase": r["phase"], "tasks": len(rows), "writebacks": len(writebacks), "handoffs": len(handoffs), "checkpoint_rows": checkpoints["n"]}))
            elif phase == "revise":
                assert r["phase"] in {"ready_for_restart", "source_corrected", "mem0_corrected"}
                before = {p["Module"]: p["Id"] for p in r["processes_before"]}
                after = processes()
                assert all(before[p["Module"]] != p["Id"] for p in after)
                async with httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", timeout=30) as c:
                    for k, v in json.loads(Path("data/collective/submission-live-2026-10-18/session.json").read_text()).items():
                        c.cookies.set(k, v)
                    response = await c.get(f"/conversations/{r['conversation']}/messages")
                    response.raise_for_status()
                    assert len(response.json()) >= 2
                for artifact in old["artifacts"]:
                    a = await db.execute("SELECT path,sha256 FROM artifacts WHERE id=%s", (artifact["id"],), one=True)
                    assert hashlib.sha256(Path(a["path"]).read_bytes()).hexdigest() == a["sha256"] == artifact["sha256"]
                if r["phase"] == "ready_for_restart":
                    changed = await memory.supersede(actor, f["project"], r["owner_source"], "ASTER release approval owner is Priya.", 1)
                    correction = await db.execute("SELECT id FROM events WHERE kind='memory.corrected' AND tenant_id=%s AND payload->>'old'=%s ORDER BY id DESC LIMIT 1", (actor.tenant_id, r["owner_source"]), one=True)
                    r.update(phase="source_corrected", processes_after=after, corrected_source=changed["memory"]["id"], affected_runs=changed["affected_runs"], correction_event=correction["id"])
                    save(r)
                # Exercise real Mem0 correction of the curator's derived fact too.
                if r["phase"] == "source_corrected":
                    async with scope(actor):
                        updated = await memory.ingest(actor, f["project"], "ASTER release approval owner changed from Maya to Priya. Priya replaces Maya as approver for ASTER only.", visibility="user")
                    assert updated["status"] == "committed" and updated["facts"]
                    r.update(phase="mem0_corrected", mem0_correction={"status": updated["status"], "fact_ids": [m["id"] for m in updated["facts"]]})
                    save(r)
                active_old = [m for m in await memory.list(actor, f["project"]) if m["memory_type"] == "semantic" and m["status"] == "active" and "aster" in m["content"].lower() and "maya" in m["content"].lower() and "priya" not in m["content"].lower()]
                assert not active_old, "Active old ASTER semantic ownership remains; correction is not complete"
                plan = await replan(actor, f["project"], r["correction_event"])
                r.update(phase="replanning", revised_plan=plan)
                save(r)
                print(json.dumps({"phase": r["phase"], "plan": plan["new_plan_id"], "affected": r["affected_runs"]}))
            elif phase == "evidence":
                assert r["phase"] == "replanning"
                plan = await db.execute("SELECT status,result FROM runs WHERE id=%s", (r["revised_plan"]["new_plan_id"],), one=True)
                assert plan["status"] == "completed" and "Priya" in plan["result"]["summary"]
                verifier_ids = [x["id"] for x in r["completed_team"] if x["role"] == "verifier"]
                current = await db.execute("SELECT id,status FROM runs WHERE id=ANY(%s)", (verifier_ids,))
                assert all(x["status"] == "completed" for x in current), "Unrelated calculator verification was invalidated"
                assert not set(verifier_ids) & set(r["affected_runs"])
                edges = await graph.query(actor.tenant_id, "MATCH (n:Task {id:$n})-[:REPLANS]->(o:Task) RETURN n.id,o.id", {"n": r["revised_plan"]["new_plan_id"]})
                assert edges
                checkpoint_after = await db.execute("SELECT count(*) AS n FROM checkpoints WHERE thread_id=%s", (f"{actor.tenant_id}:{r['root_run']}",), one=True)
                assert checkpoint_after["n"] >= r["root_checkpoint_rows"]
                messages_after = await db.execute("SELECT count(*) AS n FROM messages WHERE conversation_id=%s AND tenant_id=%s", (r["conversation"], actor.tenant_id), one=True)
                assert messages_after["n"] >= 2
                old_fact = await memory.get(actor, f["project"], r["owner_source"])
                new_fact = await memory.get(actor, f["project"], r["corrected_source"])
                assert old_fact["status"] == "superseded" and new_fact["status"] == "active" and "Priya" in new_fact["content"]
                ids = [x["id"] for x in r["completed_team"]] + [r["revised_plan"]["new_plan_id"]]
                receipts = await db.execute("SELECT id,run_id,kind,payload FROM events WHERE run_id=ANY(%s) AND kind=ANY(%s) ORDER BY id", (ids, ["model.provider_receipt", "agent.context_compacted", "tool.executed", "memory.context", "memory.write_back", "handoff.created", "handoff.acknowledged"]))
                correction_receipts = await db.execute("SELECT id,run_id,kind,payload FROM events WHERE tenant_id=%s AND id>%s AND kind='model.provider_receipt' ORDER BY id", (actor.tenant_id, r["correction_event"]))
                affected_states = await db.execute("SELECT id,role,status FROM runs WHERE id=ANY(%s)", (r["affected_runs"],))
                for attempt in r.get("previous_attempts", []):
                    attempt["failure_events"] = await db.execute("SELECT id,kind,payload FROM events WHERE run_id=%s AND kind=ANY(%s) ORDER BY id", (attempt["root_run"], ["task.blocked", "task.failed", "agent.tool_rejected"]))
                code = [Path("collective") / name for name in ("agents.py", "memory.py", "context_passports.py", "runtime.py", "tools.py", "model_budget.py")]
                r.update(phase="completed", passed=True, revised_action=plan, preserved_verifier_runs=current, replan_edges=edges,
                         execution_receipts=receipts, affected_states=affected_states,
                         correction_provider_receipts=correction_receipts,
                         root_checkpoint_rows_after=checkpoint_after["n"], conversation_messages_after=messages_after["n"],
                         final_runtime_digest=hashlib.sha256(b"".join(p.read_bytes() for p in code)).hexdigest())
                save(r)
                print(json.dumps({"passed": True, "preserved_verifiers": current, "revised_action": plan}))
            else:
                raise ValueError("Use start, status, ready, revise or evidence")
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(sys.argv[1]))
