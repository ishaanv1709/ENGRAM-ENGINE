"""Real paired procedure measurements and container probes. Never invokes a model.

Run via verify-advanced.ps1 -Stage showcase so the normal worker is paused.
The baseline is a known exact artifact bundle, not simulated AI code generation.
"""
import asyncio
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collective.agents import prepare_resources
from collective.auth import Principal
from collective.db import db, uid
from collective.memory import memory
from collective.procedures import complete_use, metrics
from collective.runtime import claim, create_run, finish
from collective.sandbox import Sandbox, docker_command, safe_path
from collective.showcase import correction_witnesses
from collective.tools import RunTools
from fastapi import HTTPException


def no_groq(event, args):
    # Reject network attempts rather than returning substitute responses.
    if event == "socket.getaddrinfo" and "groq" in str(args[0]).lower():
        raise RuntimeError("Groq is forbidden in this provider-free measurement")


sys.addaudithook(no_groq)


async def container_probes():
    box = await Sandbox(uid()).start()
    try:
        code, out, _ = await docker_command("inspect", box.name)
        assert code == 0
        config = json.loads(out)[0]
        host = config["HostConfig"]
        assert config["Config"]["User"] == "65534:65534"
        assert host["ReadonlyRootfs"] and host["NetworkMode"] == "none"
        assert "ALL" in host["CapDrop"] and "no-new-privileges:true" in host["SecurityOpt"]
        assert host["Memory"] == 536870912 and host["NanoCpus"] == 1000000000 and host["PidsLimit"] == 128
        assert all(m["Type"] == "volume" and m["Destination"] == "/workspace" for m in config["Mounts"])
        environment_names = {e.partition("=")[0] for e in config["Config"]["Env"]}
        # Python base images legitimately contain a public GPG_KEY fingerprint.
        # Inspect exact provider credential variable names, never their values.
        credential_names = {"GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "JEV_API_KEY",
            "LANGSEARCH_API_KEY", "TAVILY_API_KEY", "FALKOR_PASSWORD", "DATABASE_URL"}
        assert not environment_names & credential_names
        probe = """import json,os,socket
assert os.getuid()==65534
try:
    open('/engram-root-write-probe','w').write('probe')
except OSError:
    pass
else:
    raise AssertionError('root filesystem accepted a write')
open('/workspace/probe.txt','w').write('owned run volume')
assert not os.path.exists('/var/run/docker.sock')
s=socket.socket();s.settimeout(1)
try:
    s.connect(('192.0.2.1',443))
except OSError:
    pass
else:
    raise AssertionError('external connection succeeded')
finally:
    s.close()
assert all(line.split()[1]=='lo' for line in open('/proc/net/route').read().splitlines()[1:])
print(json.dumps({'uid':os.getuid(),'root_write_denied':True,'workspace_write':True,'external_connect_failed':True,'docker_socket_absent':True}))
"""
        await box.write("probe.py", probe)
        result = await box.execute("python /workspace/probe.py")
        assert result["exit_code"] == 0, result
        paths = {}
        for path in ("../outside", "/etc/passwd", "nested/../../outside", "bad\\path"):
            try:
                safe_path(path)
            except HTTPException as exc:
                paths[path] = exc.status_code
            else:
                raise AssertionError("Unsafe path accepted")
        return {"passed": True, "container_id": config["Id"], "image_id": config["Image"],
            "configured_image": config["Config"]["Image"], "inspected_controls": {
                "uid": config["Config"]["User"], "read_only_root": host["ReadonlyRootfs"],
                "network": host["NetworkMode"], "memory_bytes": host["Memory"],
                "nano_cpus": host["NanoCpus"], "pids": host["PidsLimit"], "cap_drop": host["CapDrop"],
                "security_opt": host["SecurityOpt"], "bind_mounts": host.get("Binds"),
                "provider_credential_names_absent": True, "environment_names": sorted(environment_names)}, "behavior": json.loads(result["stdout"]),
                "path_denials": paths,
                "scope": "Actual config and bounded behavior probes; no kernel-escape test or policy-model evaluation."}
    finally:
        await box.close()


async def save_report(actor, project, event, payload):
    security = await container_probes()
    corrections = await db.execute("SELECT * FROM events WHERE tenant_id=%s AND kind='memory.corrected' AND payload->>'project_id'=%s", (actor.tenant_id, project))
    tasks = await db.execute("SELECT id FROM runs WHERE tenant_id=%s AND project_id=%s", (actor.tenant_id, project))
    witnesses = await correction_witnesses(actor.tenant_id, project, corrections, {r["id"] for r in tasks})
    assert any(w["direct_readers"] and w["supersession_present"] and w["revision_edges"] for w in witnesses.values())
    report = {"provider_calls": 0, "autonomous_team_verified": False, "benchmark_event_id": event["id"],
        "benchmark": payload, "container_security": security, "graph_witnesses": witnesses}
    path = Path(f"data/collective/showcase-measurement-{event['id']}.json")
    path.write_text(json.dumps(report, indent=2, default=str)+"\n", encoding="utf-8")
    Path("data/collective/showcase-measurement-latest.json").write_text(json.dumps(report, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "summary": payload["summary"], "container_probes_passed": security["passed"]}), flush=True)


async def main(finish_event=None):
    await db.open()
    fixture = json.loads(Path("data/collective/film-infrastructure-evidence.json").read_text(encoding="utf-8"))
    tenant, project = fixture["fixture"]["tenant"], fixture["fixture"]["project"]
    account = await db.execute("SELECT id FROM users WHERE email=%s", (fixture["fixture"]["email"],), one=True)
    actor = Principal(account["id"], tenant, "owner", "Provider-free measurement")
    if finish_event:
        try:
            event = await db.execute("SELECT id,payload FROM events WHERE id=%s AND tenant_id=%s AND kind='procedure.benchmark' AND payload->>'project_id'=%s", (finish_event, tenant, project), one=True)
            assert event, "No matching real benchmark event"
            await save_report(actor, project, event, event["payload"])
        finally:
            await db.pool.close()
        return
    version = max(fixture["versions"], key=lambda v: v["version"])
    record = await memory.get(actor, project, version["id"])
    assert record["status"] == "active"
    trials, new_ids = [], []
    try:
        # Alternate order to avoid always assigning warm-cache advantage to reuse.
        for pair in range(5):
            for mode in (("baseline", "reuse") if pair % 2 == 0 else ("reuse", "baseline")):
                objective = (f"Reuse the already active verified procedure {record['id']}" if mode == "reuse"
                    else "Verify the exact supplied capacity artifact bundle")
                created = await create_run(actor, project, objective + " [paired infrastructure measurement; no inference]", "verifier", context_scope="team")
                new_ids.append(created["id"])
                run = await claim("provider-free-benchmark", tenant)
                assert run and run["id"] == created["id"], "Pause the worker and clear only this fixture's queued work first"
                kit = RunTools(actor, run)
                core, optional = kit.build()
                tools = {t.name: t for t in core + optional}
                try:
                    started = time.perf_counter()
                    if mode == "reuse":
                        await prepare_resources(kit, core, [])
                    else:
                        for artifact in version["manifest"]:
                            await tools["artifact_read"].ainvoke({"artifact_id": artifact["id"], "destination": artifact["name"]})
                    prepared = time.perf_counter()
                    checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
                    assert checked["verification_passed"] and "10 passed" in checked["stdout"], checked
                    executed = time.perf_counter()
                    actual = {a["name"]: hashlib.sha256(await kit.sandbox.read(a["name"])).hexdigest() for a in version["manifest"]}
                    assert all(actual[a["name"]] == a["sha256"] for a in version["manifest"])
                    if mode == "reuse":
                        await complete_use(actor, run, record, actual)
                    completed = time.perf_counter()
                    usage = await metrics([run["id"]])
                    assert usage["model_calls"] == usage["model_tokens"] == 0
                    trial = {"pair": pair + 1, "mode": mode, "run_id": run["id"],
                        "total_ms": round((completed-started)*1000, 3),
                        "prepare_ms": round((prepared-started)*1000, 3),
                        "execute_ms": round((executed-prepared)*1000, 3),
                        "validation_ms": round((completed-executed)*1000, 3),
                        "tool_calls": kit.call_count, **usage, "check_event_id": checked["check_event_id"],
                        "tests_passed": 10, "hashes": actual}
                    trials.append(trial)
                    await finish(run, "completed", {"summary": "Measured real sandbox checks; no model inference", "check_event_ids": [checked["check_event_id"]]})
                    print(json.dumps({"pair": pair+1, "mode": mode, "ms": trial["total_ms"], "tests_passed": 10}), flush=True)
                finally:
                    await kit.close()
        baseline = [t for t in trials if t["mode"] == "baseline"]
        reuse = [t for t in trials if t["mode"] == "reuse"]
        def median(rows, key):
            return statistics.median(t[key] for t in rows)
        paired = [baseline[i]["total_ms"]-reuse[i]["total_ms"] for i in range(5)]
        summary = {"baseline_median_ms": median(baseline, "total_ms"), "reuse_median_ms": median(reuse, "total_ms"),
            "time_saved_ms": statistics.median(paired), "paired_time_saved_ms": paired,
            "tool_calls_saved": median(baseline, "tool_calls")-median(reuse, "tool_calls"),
            "model_calls_saved": 0, "model_tokens_saved": 0, "provider_calls": 0,
            "baseline_range_ms": [min(t["total_ms"] for t in baseline),max(t["total_ms"] for t in baseline)],
            "reuse_range_ms": [min(t["total_ms"] for t in reuse),max(t["total_ms"] for t in reuse)]}
        payload = {"project_id": project, "procedure_id": record["id"], "version": version["version"],
            "run_ids": new_ids, "method": "Five paired fresh-container trials: exact artifact bundle versus active artifact-bound procedure; alternating order; identical v2 hashes and 10-test suite.",
            "timing_scope": "Preparation (including container startup), pytest execution and hash/receipt validation; excludes task creation, finish and container cleanup. Reuse includes its mandatory version-validation overhead.",
            "limitations": "No inference: actual model calls and tokens are zero in both arms. This measures execution overhead, not autonomous code-generation savings. Signed results may show reuse slower. Five local pairs are not a general performance guarantee.",
            "summary": summary, "trials": trials}
        event = await db.event(tenant, "procedure.benchmark", payload)
        await save_report(actor, project, event, payload)
    finally:
        if new_ids:
            await db.execute("UPDATE runs SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE id=ANY(%s) AND status IN ('queued','running')", (new_ids,))
        await db.pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--finish-event", type=int, help="Finish security/graph evidence for an already persisted benchmark; do not repeat trials")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.finish_event))
