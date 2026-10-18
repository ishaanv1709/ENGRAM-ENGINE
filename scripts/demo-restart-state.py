"""Save/verify actual demo state around an API + agent-process restart."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal
from collective.db import db
from collective.memory import memory

def option(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


STATE = Path(option("--state", "data/collective/demo-restart-state.json"))
PROOF = Path(option("--proof", "data/collective/demo-restart-proof.json"))


async def main():
    await db.open()
    report = json.loads(Path(option("--report", "data/collective/live-verification.json")).read_text(encoding="utf-8"))
    report = report.get("report", report)
    fixture = report["fixture"]
    member = await db.execute("SELECT user_id,role FROM memberships WHERE tenant_id=%s", (fixture["tenant"],), one=True)
    actor = Principal(member["user_id"], fixture["tenant"], member["role"], "Restart demo")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8088/api", headers={"X-Engram-Request": "1"}) as client:
        if "prepare" in sys.argv:
            password = "Integration-password-123" if report.get("execution_mode") else "Live-verification-password-123"
            (await client.post("/auth/login", json={"email": fixture["email"], "password": password})).raise_for_status()
            records = await memory.list(actor, fixture["project"])
            artifacts = await db.execute("SELECT id,sha256,path FROM artifacts WHERE tenant_id=%s AND project_id=%s", (actor.tenant_id, fixture["project"]))
            checkpoints = await db.execute("SELECT thread_id,count(*) AS count FROM checkpoints WHERE thread_id LIKE %s GROUP BY thread_id", (actor.tenant_id + ":%",))
            state = {"fixture": fixture, "cookies": dict(client.cookies), "memory_ids": [r["id"] for r in records],
                "artifacts": artifacts, "checkpoints": checkpoints, "conversation": report.get("submitted", {}).get("conversation"),
                "fixture_scope": report.get("execution_mode", "Live provider fixture")}
            STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
            print(json.dumps({"phase": "before_restart", "memories": len(records), "artifacts": len(artifacts), "checkpoint_threads": len(checkpoints)}))
        else:
            state = json.loads(STATE.read_text(encoding="utf-8"))
            client.cookies.update(state["cookies"])
            (await client.get("/me")).raise_for_status()
            message_count = 0
            if state.get("conversation"):
                messages = await client.get(f"/conversations/{state['conversation']}/messages")
                messages.raise_for_status()
                assert messages.json()
                message_count = len(messages.json())
            records = await memory.list(actor, fixture["project"])
            assert set(state["memory_ids"]) <= {r["id"] for r in records}
            for artifact in state["artifacts"]:
                assert hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
            checkpoints = await db.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE %s", (actor.tenant_id + ":%",))
            assert {r["thread_id"] for r in state["checkpoints"]} <= {r["thread_id"] for r in checkpoints}
            result = {"passed": True, "session_survived": True, "messages": message_count,
                "fixture_scope": state.get("fixture_scope", "Live provider fixture"),
                "persisted_memory_count": len(state["memory_ids"]), "persisted_artifacts": len(state["artifacts"]),
                "persisted_checkpoint_threads": len(state["checkpoints"])}
            if report.get("execution_mode"):
                for version in report["versions"]:
                    stored = await db.execute("SELECT status,manifest FROM procedure_versions WHERE id=%s AND tenant_id=%s", (version["id"], actor.tenant_id), one=True)
                    assert stored["status"] == "active" and stored["manifest"] == version["manifest"]
                claims = await db.execute("SELECT id FROM knowledge_claims WHERE tenant_id=%s AND id=ANY(%s)", (actor.tenant_id, [c["id"] for c in report["claims"]]))
                assert len(claims) == len(report["claims"])
                selected = await db.execute("SELECT winner_id FROM claim_resolutions WHERE tenant_id=%s AND project_id=%s", (actor.tenant_id, fixture["project"]), one=True)
                assert selected["winner_id"] == report["resolution"]["winner_id"]
                plan = await db.execute("SELECT status FROM runs WHERE id=%s", (report["plan"]["new_plan_id"],), one=True)
                assert plan["status"] == "blocked"
                result.update(persisted_procedure_versions=len(report["versions"]), persisted_claims=len(claims), persisted_plan_status=plan["status"])
            PROOF.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result))
    await db.pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
