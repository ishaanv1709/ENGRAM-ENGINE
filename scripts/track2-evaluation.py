"""Measured real-store coordination lab. No model inference or fake service.

Run prepare and recover through verify-advanced.ps1 so the normal worker is
paused. Perform a real restart-app.ps1 between them. Live model trials remain
separate; this lab does not claim autonomous reasoning or agent throughput.
"""
import asyncio
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from collective.auth import Principal, register
from collective.db import db, uid
from collective.graph import graph
from collective.memory import memory
from collective.runtime import create_run, handoff, handoff_identity, acknowledge_handoffs

ROOT = Path("data/collective/track2-upgrade")
REPORT = ROOT / "reliability.json"


def save(report):
    ROOT.mkdir(parents=True, exist_ok=True)
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def processes():
    entries = json.loads(Path("data/collective/processes.json").read_text(encoding="utf-8-sig"))
    return [e for e in entries if e["Module"] in {"collective.serve", "collective.agents"}]


async def measure(items, work, concurrency=8):
    semaphore = asyncio.Semaphore(concurrency)
    timings, results = [], []
    async def one(item):
        async with semaphore:
            start = time.perf_counter()
            result = await work(item)
            timings.append((time.perf_counter() - start) * 1000)
            results.append(result)
    start = time.perf_counter()
    await asyncio.gather(*(one(item) for item in items))
    elapsed = time.perf_counter() - start
    ordered = sorted(timings)
    return results, {"operations": len(items), "concurrency": concurrency, "elapsed_seconds": elapsed,
                     "operations_per_second": len(items) / elapsed,
                     **{f"p{q}_ms": ordered[min(len(ordered)-1, math.ceil(q / 100 * len(ordered))-1)] for q in (50, 95, 99)},
                     "errors": 0, "scope": "Production memory/store operations, not autonomous agents or LLM throughput"}


async def main(phase):
    await db.open()
    try:
        if phase == "prepare":
            assert not REPORT.exists(), "Keep earlier evidence; do not overwrite a trial"
            user = await register(f"track2-{uid()}@example.test", "Track2-fixture-only-123", "Track2 lab", "Controlled memory lab")
            row = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
            actor = Principal(user, row["tenant_id"], "owner", "Track2 lab")
            project = uid()
            await db.execute("INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Track 2 reliability lab')", (project, actor.tenant_id))
            report = {"phase": "preparing", "passed": False, "provider_calls": 0,
                      "fixture": {"user": user, "tenant": actor.tenant_id, "project": project}, "processes_before": processes(),
                      "method": "Real production memory, graph and handoff functions invoked directly, without provider inference. Tasks are controlled infrastructure consumers, not autonomous agent completions."}
            save(report)
            async def write(i):
                return await memory.commit(actor, project, "ORCHID approval owner is Maya" if i == 0 else f"Document shard {i} records the independently versioned service-{i} reference", memory_type="semantic")
            records, report["writes"] = await measure(list(range(16)), write)
            # Preserve input identity despite intentionally concurrent completion.
            owner = next(r for r in records if "Maya" in r["content"])
            records = [owner, *[r for r in records if r["id"] != owner["id"]]]
            tasks = [await create_run(actor, project, f"Controlled reference consumer {i}", "researcher",
                                      memory_ids=[r["id"]], initial_status="awaiting_handoff") for i, r in enumerate(records)]
            async def read(i):
                index = i % len(tasks)
                bundle = await memory.focused(actor, project, [records[index]["id"]], tasks[index]["id"], mode="load_trial")
                assert bundle["evidence_ids"] == [records[index]["id"]]
                assert bundle["approximate_tokens"] <= bundle["passport"]["budget_tokens"]
                return bundle["passport"]["event_id"]
            reads, report["reads"] = await measure(list(range(128)), read)
            report["distinct_passport_receipts"] = len(set(reads))
            async def contend(i):
                try:
                    return await memory.supersede(actor, project, owner["id"], f"ORCHID approval owner is Priya; source {i}", 1)
                except HTTPException as exc:
                    assert exc.status_code == 409
                    return {"conflict": 409}
            outcomes = await asyncio.gather(*(contend(i) for i in range(8)))
            winners = [x for x in outcomes if "memory" in x]
            assert len(winners) == 1 and sum("conflict" in x for x in outcomes) == 7
            corrected = winners[0]
            assert corrected["affected_runs"] == [tasks[0]["id"]]
            statuses = await db.execute("SELECT id,status FROM runs WHERE id=ANY(%s)", ([t["id"] for t in tasks],))
            assert sum(r["status"] == "stale" for r in statuses) == 1
            report["correction"] = {"contending_writers": 8, "committed": 1, "rejected_stale_revisions": 7,
                                    "expected_consumers": [tasks[0]["id"]], "actual_affected": corrected["affected_runs"],
                                    "unrelated_preserved": 15, "old": owner["id"], "new": corrected["memory"]["id"],
                                    "states_before_fixture_cleanup": statuses}
            source = await create_run(actor, project, "Controlled delivery source", "researcher", memory_ids=[], initial_status="awaiting_handoff")
            reference = records[1]
            delivered, report["handoff_timing"] = await measure(list(range(20)), lambda _: handoff(
                actor, source, "researcher", "Source captured", [reference["id"]], [], "Inspect the supplied document reference"), concurrency=20)
            assert len({r["id"] for r in delivered}) == 1
            rows = await db.execute("SELECT id,to_run FROM handoffs WHERE tenant_id=%s", (actor.tenant_id,))
            assert len(rows) == 1
            report["duplicate_delivery"] = {"attempts": 20, "receivers": 1, "envelopes": 1, "receiver": delivered[0]["id"]}
            packet = {"objective": source["objective"], "checkpoint": "Process stopped before envelope commit", "remaining": "Recover the document handoff after restart",
                      "evidence": [{"id": reference["id"], "revision": 1}], "artifact_ids": [], "check_event_ids": [], "source_run": source["id"]}
            pending_id, _ = handoff_identity(actor.tenant_id, source["id"], "researcher", packet)
            await create_run(actor, project, packet["remaining"], "researcher", parent=source["id"], run_id=pending_id,
                             memory_ids=[reference["id"]], context_scope=source["context_scope"], initial_status="awaiting_handoff")
            # Only the deliberately interrupted source/receiver stay pending.
            # Cleanup is not represented as agent completion.
            await db.execute("UPDATE runs SET status='cancelled',revision=revision+1 WHERE tenant_id=%s AND id<>ALL(%s) AND status<>'stale'",
                             (actor.tenant_id, [source["id"], pending_id]))
            report.update(phase="awaiting_real_restart", pending_id=pending_id, source_run=source["id"], interrupted_packet=packet,
                          record_ids=[r["id"] for r in records])
            save(report)
            print(json.dumps({"phase": report["phase"], "writes": report["writes"], "reads": report["reads"], "correction": report["correction"], "duplicate_delivery": report["duplicate_delivery"]}))
        elif phase == "recover":
            report = json.loads(REPORT.read_text())
            assert report["phase"] == "awaiting_real_restart"
            before = {e["Module"]: e["Id"] for e in report["processes_before"]}
            after = processes()
            assert all(before[e["Module"]] != e["Id"] for e in after)
            f = report["fixture"]
            actor = Principal(f["user"], f["tenant"], "owner", "Track2 lab")
            pending = await db.execute("SELECT * FROM runs WHERE id=%s", (report["pending_id"],), one=True)
            assert pending["status"] == "awaiting_handoff"
            assert not await db.execute("SELECT id FROM handoffs WHERE to_run=%s", (pending["id"],))
            source = await db.execute("SELECT * FROM runs WHERE id=%s", (report["source_run"],), one=True)
            packet = report["interrupted_packet"]
            delivered = await handoff(actor, source, "researcher", packet["checkpoint"], [e["id"] for e in packet["evidence"]], [], packet["remaining"])
            assert delivered["id"] == pending["id"] and delivered["status"] == "queued"
            envelopes = await db.execute("SELECT * FROM handoffs WHERE to_run=%s", (pending["id"],))
            await memory.focused(actor, f["project"], delivered["memory_refs"], delivered["id"], mode="recovery")
            await acknowledge_handoffs(actor, delivered, envelopes)
            first = await db.execute("SELECT acknowledged_at FROM handoffs WHERE id=%s", (pending["id"],), one=True)
            assert first["acknowledged_at"]
            replayed = await handoff(actor, source, "researcher", packet["checkpoint"], [e["id"] for e in packet["evidence"]], [], packet["remaining"])
            await acknowledge_handoffs(actor, replayed, envelopes)
            latest = await db.execute("SELECT acknowledged_at FROM handoffs WHERE id=%s", (pending["id"],), one=True)
            assert first == latest
            acknowledgements = await db.execute("SELECT id FROM events WHERE run_id=%s AND kind='task.handoff_acknowledged'", (pending["id"],))
            assert len(acknowledgements) == 1
            assert (await graph.get(actor.tenant_id, report["correction"]["new"]))["status"] == "active"
            receipts = await db.execute("SELECT id FROM events WHERE tenant_id=%s AND kind='memory.context'", (actor.tenant_id,))
            assert len(receipts) >= 17
            try:
                await memory.get(Principal("outsider", uid(), "member", "Outsider"), f["project"], report["record_ids"][0])
                raise AssertionError("Cross-tenant memory leaked")
            except HTTPException as exc:
                assert exc.status_code == 404
            calls = await db.execute("SELECT count(*) AS n FROM events WHERE tenant_id=%s AND kind='model.provider_receipt'", (actor.tenant_id,), one=True)
            assert calls["n"] == 0
            await db.execute("UPDATE runs SET status='cancelled',revision=revision+1 WHERE id=ANY(%s)", ([source["id"], pending["id"]],))
            report.update(phase="completed", passed=True, processes_after=after,
                          recovery={"same_receiver": True, "envelope_committed_before_claimable": True, "acknowledgements": 1,
                                    "first_acknowledgement_preserved": True, "cross_tenant_denial": 404,
                                    "persisted_context_receipts": len(receipts), "provider_calls": 0})
            save(report)
            print(json.dumps({"passed": True, "recovery": report["recovery"]}))
        else:
            raise ValueError("Use prepare or recover")
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(sys.argv[1]))
