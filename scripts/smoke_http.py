"""Exercise real HTTP auth, tenant isolation, project creation and persistence."""

import json
import secrets
import uuid

import httpx

base = "http://127.0.0.1:8088"
headers = {"X-Engram-Request": "1"}
results = {}
with (
    httpx.Client(base_url=base, headers=headers, timeout=30) as alice,
    httpx.Client(base_url=base, headers=headers, timeout=30) as bob,
):
    for client, name in [(alice, "Alice"), (bob, "Bob")]:
        response = client.post(
            "/api/auth/register",
            json={
                "email": f"smoke-{uuid.uuid4()}@example.test",
                "password": secrets.token_urlsafe(24),
                "name": name,
                "workspace": "HTTP verification fixture",
            },
        )
        response.raise_for_status()
    response = alice.post("/api/projects", json={"name": "HTTP verification fixture"})
    response.raise_for_status()
    project = response.json()["id"]
    results["real_project_created"] = bool(project)
    results["cross_tenant_project_denied"] = bob.get(f"/api/projects/{project}/runs").status_code == 404
    results["csrf_header_required"] = (
        alice.post("/api/projects", headers={"X-Engram-Request": ""}, json={"name": "Denied"}).status_code == 403
    )
    results["foreign_origin_denied"] = (
        alice.post("/api/projects", headers={"Origin": "https://attacker.example"}, json={"name": "Denied"}).status_code
        == 403
    )
    results["persistent_project_list"] = any(p["id"] == project for p in alice.get("/api/projects").json())
    results["cookie_is_httponly"] = "HttpOnly" in alice.cookies.jar._cookies["127.0.0.1"]["/"]["engram_session"]._rest
    print(json.dumps(results, indent=2))
    if not all(results.values()):
        raise SystemExit(1)
