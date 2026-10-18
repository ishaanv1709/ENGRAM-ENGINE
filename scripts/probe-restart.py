"""Run prepare, restart the actual API process, then run verify."""

import asyncio
import json
import secrets
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.auth import Principal
from collective.db import db
from collective.memory import memory

STATE = Path("data/collective/restart-probe.json")


def prepare():
    with httpx.Client(base_url="http://127.0.0.1:8088", headers={"X-Engram-Request": "1"}, timeout=30) as client:
        client.post(
            "/api/auth/register",
            json={
                "email": f"restart-{uuid4()}@example.test",
                "password": secrets.token_urlsafe(24),
                "name": "Restart probe",
                "workspace": "Restart probe",
            },
        ).raise_for_status()
        actor = client.get("/api/me").json()
        project = client.post("/api/projects", json={"name": "Restart continuity"}).json()["id"]
        conversation = client.post(f"/api/projects/{project}/conversations", json={"name": "Durable history"}).json()[
            "id"
        ]
        run = client.post(
            f"/api/projects/{project}/runs",
            json={"objective": "Remember the restart-continuity fixture message.", "conversation_id": conversation},
        ).json()["id"]
        client.post(f"/api/runs/{run}/cancel").raise_for_status()
        STATE.write_text(
            json.dumps(
                {"actor": actor, "project": project, "conversation": conversation, "cookies": dict(client.cookies)}
            )
        )

    async def seed():
        await db.open()
        principal = Principal(actor["id"], actor["workspace_id"], actor["role"], actor["name"])
        await memory.commit(
            principal, project, "Restart fixture: the release codename is ORCHID.", memory_type="semantic"
        )
        await db.pool.close()

    asyncio.run(seed())
    print("Prepared real conversation, session and FalkorDB memory. Restart the API now.")


def verify():
    state = json.loads(STATE.read_text())
    with httpx.Client(
        base_url="http://127.0.0.1:8088", headers={"X-Engram-Request": "1"}, cookies=state["cookies"], timeout=30
    ) as client:
        client.get("/api/me").raise_for_status()
        messages = client.get(f"/api/conversations/{state['conversation']}/messages")
        messages.raise_for_status()
        assert any("restart-continuity" in r["content"] for r in messages.json())
        found = client.post(
            f"/api/projects/{state['project']}/search", json={"content": "What is the release codename?"}
        )
        found.raise_for_status()
        assert any("ORCHID" in r["content"] for r in found.json()["memories"])
    print("PASS: session, conversation history and sourced graph retrieval survived an actual API process restart")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    (prepare if sys.argv[1] == "prepare" else verify)()
