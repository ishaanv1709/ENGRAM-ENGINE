"""Extend the real provider workflow with competing agent claims and a restart.

Run prepare with the normal worker paused, restart the API, then run complete.
Never fabricates agent work: each claimant and the revised plan use DeepAgents.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from collective.agents import execute_run, heartbeat
from collective.auth import Principal
from collective.coordination import submit_claim, resolve_claims, replan
from collective.db import db
from collective.graph import graph
from collective.memory import memory
from collective.runtime import claim, create_run, finish

REPORT = Path("data/collective/causal-demo.json")


def save(value):
    REPORT.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
    print(json.dumps(value, default=str), flush=True)


async def drain(actor):
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()

    async def one(run):
        execution = asyncio.create_task(execute_run(run, saver))
        pulse = asyncio.create_task(heartbeat(run, execution))
        try:
            await execution
        except Exception as exc:
            await finish(run, "failed", error=type(exc).__name__)
            raise
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)

    active = set()
    for _ in range(600):
        await db.execute("""UPDATE runs r SET status='queued',attempt=0 WHERE tenant_id=%s AND status='waiting'
            AND NOT EXISTS(SELECT 1 FROM runs c WHERE c.parent_id=r.id AND c.status IN ('queued','running','waiting'))""",
            (actor.tenant_id,))
        for slot in range(2 - len(active)):
            run = await claim(f"causal-demo-{slot}", actor.tenant_id)
            if run:
                active.add(asyncio.create_task(one(run)))
        if not active:
            return
        done, active = await asyncio.wait(active, timeout=3, return_when=asyncio.FIRST_COMPLETED)
        for result in done:
            try:
                result.result()
            except Exception:
                for pending in active:
                    pending.cancel()
                await asyncio.gather(*active, return_exceptions=True)
                raise
    raise TimeoutError("Demo exceeded its bounded scheduling window")


async def main():
    await db.open()
    initial = json.loads(Path("data/collective/live-verification.json").read_text(encoding="utf-8"))
    assert initial.get("passed"), "Complete the real team workflow first"
    fixture = initial["fixture"]
    project = fixture["project"]
    member = await db.execute("SELECT user_id,role FROM memberships WHERE tenant_id=%s", (fixture["tenant"],), one=True)
    actor = Principal(member["user_id"], fixture["tenant"], member["role"], "Causal demo")
    if "prepare" in sys.argv:
        assert not REPORT.exists(), "Preserve the existing demo report; use a new explicit fixture for another run"
        times = ["2026-10-14T09:00:00+00:00", "2026-10-15T09:00:00+00:00"]
        sources = await asyncio.gather(*[
            memory.commit(actor, project, text, metadata={"kind": "demo_source", "observed_at": at})
            for text, at in zip(["ORCHID release roster: Maya owns release approval.",
                "ORCHID release roster update: Priya now owns release approval."], times)])
        await submit_claim(actor, project, "ORCHID release", "approval owner", "Maya", sources[0]["id"], times[0])
        first = await resolve_claims(actor, project, "ORCHID release", "approval owner")
        task = await create_run(actor, project,
            f"Read current release approval memory {first['memory_id']} with memory_read and summarize the ORCHID approval owner with the source ID. Do not browse the web or dispatch other tasks.", "researcher", context_scope="team")
        await drain(actor)
        old = await db.execute("SELECT status FROM runs WHERE id=%s", (task["id"],), one=True)
        assert old["status"] == "completed"
        agents = []
        for role, value, source, at in zip(["researcher", "curator"], ["Maya", "Priya"], sources, times):
            agents.append(await create_run(actor, project,
                f"Preserve your independent sourced claim. Use capability_search for claim_submit, then call claim_submit with subject='ORCHID release', predicate='approval owner', value='{value}', source_id='{source['id']}', source_time='{at}'. "
                "Do not replace, correct or resolve the other agent's claim. Report your real returned claim ID. No other work is needed.", role, context_scope="team"))
        await drain(actor)
        claims = await db.execute("SELECT * FROM knowledge_claims WHERE tenant_id=%s AND project_id=%s AND agent_id=ANY(%s)",
            (actor.tenant_id, project, [r["id"] for r in agents]))
        assert {c["value"] for c in claims} == {"Maya", "Priya"}, "Both real agents must have submitted their claims"
        resolved = await resolve_claims(actor, project, "ORCHID release", "approval owner")
        chosen = next(c for c in claims if c["id"] == resolved["winner_id"])
        assert chosen["value"] == "Priya"
        stale = await db.execute("SELECT status FROM runs WHERE id=%s", (task["id"],), one=True)
        assert stale["status"] == "stale"
        correction = await db.execute("SELECT * FROM events WHERE tenant_id=%s AND kind='memory.corrected' AND payload->>'new'=%s ORDER BY id DESC LIMIT 1",
            (actor.tenant_id, resolved["memory_id"]), one=True)
        assert correction and task["id"] in correction["payload"]["affected_runs"]
        save({"fixture": fixture, "phase": "prepared_before_restart", "claims": claims, "resolution": resolved,
            "correction": correction, "affected_task": task["id"], "source_ids": [s["id"] for s in sources],
            "conversation": initial["submitted"]["conversation"], "initial_root": initial["submitted"]["root"]})
    elif "complete" in sys.argv:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        assert report["phase"] == "prepared_before_restart"
        source = await memory.get(actor, project, report["resolution"]["memory_id"])
        assert source["status"] == "active" and "Priya" in source["content"]
        rows = await db.execute("SELECT role,content FROM messages WHERE conversation_id=%s ORDER BY created_at", (report["conversation"],))
        assert len(rows) >= 2
        plan = await replan(actor, project, report["correction"]["id"])
        assert (await replan(actor, project, report["correction"]["id"]))["new_plan_id"] == plan["new_plan_id"]
        await drain(actor)
        finished = await db.execute("SELECT status,result FROM runs WHERE id=%s", (plan["new_plan_id"],), one=True)
        assert finished["status"] == "completed", finished
        path = await graph.query(actor.tenant_id,
            "MATCH (n:Task {id:$n})-[:REPLANS]->(o:Task {id:$o}) RETURN n.id,o.id", {"n": plan["new_plan_id"], "o": report["affected_task"]})
        assert path
        report.update(phase="completed_after_restart", passed=True, plan=plan,
            revised_result=finished["result"], persisted_messages=len(rows), causal_path=path)
        save(report)
    else:
        raise ValueError("Choose prepare or complete")
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
