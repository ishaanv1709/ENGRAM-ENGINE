"""Check a real unapproved workflow across an actual app restart, without inference."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.encoders import jsonable_encoder
from collective.auth import Principal, register
from collective.db import db, uid
from collective.repositories import import_zip, read_file
from collective.workflows import create_workflow, control, tick, profile_create

REPORT = Path("data/collective/workflow-restart-proof.json")


async def snapshot(identity):
    wf = await db.execute("SELECT * FROM workflows WHERE id=%s", (identity,), one=True)
    steps = await db.execute("SELECT * FROM workflow_steps WHERE workflow_id=%s ORDER BY position", (identity,))
    runs = await db.execute("SELECT * FROM runs WHERE workflow_id=%s", (identity,))
    usage = await db.execute("SELECT * FROM workflow_reservations WHERE workflow_id=%s", (identity,))
    return jsonable_encoder({"workflow": wf, "steps": steps, "runs": runs, "usage": usage})


async def main(mode):
    await db.open()
    try:
        if mode == "prepare":
            email = f"workflow-restart-{uid()}@example.test"
            user = await register(email, "Restart-check-password-123", "Restart checks", "Restart checks")
            tenant = (await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True))["tenant_id"]
            actor = Principal(user, tenant, "owner", "Restart checks")
            project = uid()
            await db.execute("INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Workflow restart check; no inference')", (project, tenant))
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as archive:
                archive.writestr("project/src/example.py", "def answer():\n    return 42\n")
            source = await import_zip(actor, project, "restart-source.zip", buf.getvalue())
            profile = await profile_create(actor, project, "Restart investigator", "researcher", "Inspect actual source only.", ["repository_list", "repository_read", "team_status"], "team")
            wf = await create_workflow(actor, project, "Preserve an actual human approval gate through restart", [{
                "key": "investigate", "title": "Approve source investigation", "role": "researcher",
                "objective": "Wait for human approval before inspecting source; no inference in this check",
                "depends_on": [], "profile_id": profile["id"], "needs_approval": True,
            }], {}, snapshot_id=source["id"])
            await control(actor, wf["id"], "start")
            await tick(wf["id"])
            before = await snapshot(wf["id"])
            assert before["steps"][0]["status"] == "awaiting_approval" and not before["runs"]
            report = {"user": user, "tenant": tenant, "project": project, "before": before,
                "source": jsonable_encoder(source), "profile": jsonable_encoder(profile),
                "actual_process_restart_verified": False, "provider_calls": 0}
        elif mode == "verify":
            report = json.loads(REPORT.read_text())
            actor = Principal(report["user"], report["tenant"], "owner", "Restart checks")
            identity = report["before"]["workflow"]["id"]
            after = await snapshot(identity)
            assert after == report["before"], "Workflow or gate changed across restart"
            source = await db.execute("SELECT * FROM repository_snapshots WHERE id=%s", (report["source"]["id"],), one=True)
            profile = await db.execute("SELECT * FROM agent_profiles WHERE id=%s", (report["profile"]["id"],), one=True)
            assert jsonable_encoder(source) == report["source"]
            assert jsonable_encoder(profile) == report["profile"]
            for entry in source["manifest"]:
                content = await read_file(actor, report["project"], source["id"], entry["path"])
                assert hashlib.sha256(content["content"].encode()).hexdigest() == entry["sha256"]
            proof = json.loads(Path("data/collective/restart-process-proof.json").read_text())
            assert proof["actual_app_process_restart"]
            created = datetime.fromisoformat(report["before"]["workflow"]["created_at"])
            assert all(datetime.fromisoformat(item["Started"].replace("Z", "+00:00")) > created for item in proof["after"])
            report.update(after=after, process_proof=proof, actual_process_restart_verified=True,
                preserved=["running workflow", "human approval gate", "profile snapshot", "source manifest and bytes", "empty task and attempt ledgers"])
            await control(actor, identity, "cancel")
            report["cleanup"] = "Only the check's workflow cancelled after verification"
        else:
            raise ValueError("Use prepare or verify")
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"stage": mode, "verified": report["actual_process_restart_verified"], "provider_calls": 0, "report": str(REPORT)}))
    finally:
        await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(sys.argv[1]))
