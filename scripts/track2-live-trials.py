"""Four predeclared alternating live Groq20B pairs. Stop on a real failure.

Uses the existing private demo owner's connection and active procedure. No
secrets are printed. Does not replay stored checkpoints or synthesize results.
"""
import asyncio
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal
from collective.db import db
from collective.evidence import verified_check
from collective.runtime import create_run

ROOT = Path("data/collective/track2-upgrade")
CONFIRMATION = len(sys.argv) > 1 and sys.argv[1] == "confirmation"
FILE = ROOT / ("live-confirmation.json" if CONFIRMATION else "live-series.json")
CODE = ["agents.py", "memory.py", "context_passports.py", "runtime.py", "tools.py", "model_budget.py"]


def code_digest():
    return hashlib.sha256(b"".join((Path("collective") / name).read_bytes() for name in CODE)).hexdigest()


def save(report):
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


async def observe(run_id, manifest):
    row = await db.execute("SELECT status,result,error,created_at,updated_at FROM runs WHERE id=%s", (run_id,), one=True)
    events = await db.execute("SELECT id,kind,payload FROM events WHERE run_id=%s ORDER BY id", (run_id,))
    receipts = [e for e in events if e["kind"] == "model.provider_receipt"]
    checks = [e for e in events if e["kind"] == "tool.executed" and verified_check(e["payload"])]
    writes = {e["payload"]["path"].removeprefix("/workspace/"): e["payload"]["sha256"] for e in events if e["kind"] == "sandbox.file_written"}
    passed = row["status"] == "completed" and bool(checks) and bool(receipts)
    if passed:
        assert all(writes.get(a["name"]) == a["sha256"] for a in manifest)
        assert all(e["payload"]["model"] == "openai/gpt-oss-20b" for e in receipts)
    known = [e for e in receipts if e["payload"].get("usage")]
    return {"run_id": run_id, "status": row["status"], "passed": passed, "error": row["error"],
            "provider_calls": len(receipts), "failed_provider_calls": sum(e["payload"]["status"] == "failed" for e in receipts),
            "known_tokens": sum(e["payload"]["usage"]["total_tokens"] for e in known),
            "elapsed_seconds": (row["updated_at"] - row["created_at"]).total_seconds(),
            "checks": checks, "receipts": receipts,
            "passport_events": [e for e in events if e["kind"] == "memory.context"],
            "startup_read_events": [e for e in events if e["kind"] == "memory.read"]}


async def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    assert not FILE.exists(), "Preserve earlier attempts; do not overwrite live trial evidence"
    old = json.loads(Path("data/collective/submission-live-2026-10-18/report.json").read_text())
    assert old["passed"]
    f = old["fixture"]
    actor = Principal(f["user"], f["tenant"], "owner", "Submission evaluation")
    manifest = old["comparison"]["manifest"]
    report = {"passed": False, "status": "running", "model": "openai/gpt-oss-20b", "code_sha256": code_digest(),
              "procedure_id": old["comparison"]["procedure_id"], "project_id": f["project"], "manifest": manifest,
              "protocol": "Four sequential live pairs; alternating reuse-first / baseline-first, no discarded warmup, same model, files and ten-test acceptance. Known-correct artifact baseline, not code-generation avoidance. Memory capsules and preflight preparation are production behavior. Both arms disable automatic post-run curation. Timing includes queue/startup, provider waits and execution until completion; not container cleanup. Stop on failure, keep its receipts and unknown billed usage. No general cost/latency guarantee.",
              "orders": [["reuse", "baseline"], ["baseline", "reuse"], ["reuse", "baseline"], ["baseline", "reuse"]],
              "pairs": [], "limitations": ["One workstation and provider account; small sample with shared warm services.", "SDK-internal retries are not separately counted. Failed-call billed tokens may be unknown."]}
    if CONFIRMATION:
        report["orders"] = [["baseline", "reuse"]]
        report["protocol"] = "One post-hardening confirmation pair, baseline first, otherwise the same files, model and acceptance rules as the four-pair series. This confirms the final privacy/tool-binding changes; it is not pooled into the earlier performance medians."
    save(report)
    await db.open()
    try:
        connection = await db.execute("SELECT id,provider,model FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active", (actor.user_id, actor.tenant_id), one=True)
        assert connection and connection["provider"] == "groq" and connection["model"] == report["model"]
        report["connection_id"] = connection["id"]
        for index, order in enumerate(report["orders"]):
            pair = {"pair": index + 1, "order": order, "trials": {}}
            report["pairs"].append(pair)
            for arm in order:
                assert code_digest() == report["code_sha256"], "Runtime changed during measurement"
                current = await db.execute("SELECT id FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active", (actor.user_id, actor.tenant_id), one=True)
                assert current["id"] == connection["id"], "Connection changed during measurement"
                if arm == "reuse":
                    objective = f"Reuse the already active verified procedure {report['procedure_id']}. Its authorized compact capsule and exact bound files are prepared at startup. Execute the real acceptance tests and report their actual check IDs. Do not repeat the memory read or file copies."
                    references = [report["procedure_id"]]
                else:
                    args = [{"artifact_id": a["id"], "destination": a["name"]} for a in manifest]
                    objective = "Independently verify the known exact files. Copy each artifact with its exact argument object: " + json.dumps(args) + ". Run python -m pytest -q and report real check IDs. Do not edit files, research or propose procedures."
                    references = []
                run = await create_run(actor, f["project"], objective, "verifier", auto_curate=False, memory_ids=references)
                pair["trials"][arm] = {"run_id": run["id"], "status": "running"}
                save(report)
                print(json.dumps({"pair": index+1, "arm": arm, "started": run["id"]}), flush=True)
                while True:
                    state = await db.execute("SELECT status FROM runs WHERE id=%s", (run["id"],), one=True)
                    if state["status"] not in {"queued", "running", "waiting"}:
                        break
                    await asyncio.sleep(5)
                trial = await observe(run["id"], manifest)
                pair["trials"][arm] = trial
                if arm == "reuse" and trial["passed"]:
                    use = await db.execute("SELECT completed_at FROM procedure_uses WHERE procedure_id=%s AND run_id=%s", (report["procedure_id"], run["id"]), one=True)
                    assert use and use["completed_at"]
                save(report)
                print(json.dumps({"pair": index+1, "arm": arm, **{k: trial[k] for k in ("passed", "status", "provider_calls", "known_tokens", "elapsed_seconds")}}), flush=True)
                if not trial["passed"]:
                    report.update(status="blocked_by_trial_failure", failed_trial={"pair": index+1, "arm": arm})
                    save(report)
                    return
            pair["signed_savings"] = {k: pair["trials"]["baseline"][k] - pair["trials"]["reuse"][k]
                                      for k in ("provider_calls", "known_tokens", "elapsed_seconds")}
            save(report)
        report["summary"] = {arm: {k: statistics.median(p["trials"][arm][k] for p in report["pairs"])
                                   for k in ("provider_calls", "known_tokens", "elapsed_seconds")}
                             for arm in ("baseline", "reuse")}
        report["median_paired_savings"] = {k: statistics.median(p["signed_savings"][k] for p in report["pairs"])
                                            for k in ("provider_calls", "known_tokens", "elapsed_seconds")}
        report.update(passed=True, status="completed")
        save(report)
        await db.event(actor.tenant_id, "procedure.benchmark", {"project_id": f["project"], "procedure_id": report["procedure_id"],
                       "kind": "live_model_series", "method": report["protocol"], "summary": report["summary"],
                       "median_paired_savings": report["median_paired_savings"], "pairs": len(report["pairs"]),
                       "run_ids": [t["run_id"] for p in report["pairs"] for t in p["trials"].values()]})
        print(json.dumps({"passed": True, "summary": report["summary"], "median_paired_savings": report["median_paired_savings"]}), flush=True)
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
