"""Real database/session/encryption tests. No inference responses are substituted."""

import asyncio
import os

import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires local PostgreSQL"),
]
HEADERS = {"X-Engram-Request": "1"}


async def client():
    from collective.app import app
    from collective.db import db

    await db.open()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver", headers=HEADERS)


async def test_start_building_is_private_persistent_and_requires_personal_key():
    from collective.db import db

    async with await client() as first, await client() as second:
        assert (await first.get("/api/projects")).status_code == 401
        created = await first.post("/api/auth/start")
        assert created.status_code == 200
        assert "secure" in created.headers["set-cookie"].lower() and "httponly" in created.headers["set-cookie"].lower()
        resumed = await first.post("/api/auth/start")
        assert resumed.json()["user_id"] == created.json()["user_id"] and resumed.json()["resumed"]
        me = (await first.get("/api/me")).json()
        assert not me["has_provider"] and me["browser_workspace"]
        projects = (await first.get("/api/projects")).json()
        assert len(projects) == 1 and projects[0]["name"] == "My first project"
        blocked = await first.post(
            "/api/projects/" + projects[0]["id"] + "/runs", json={"objective": "Must not spend the host's key"}
        )
        assert blocked.status_code == 503 and "Profile & settings" in blocked.json()["detail"]
        assert not await db.execute("SELECT id FROM runs WHERE tenant_id=%s", (me["workspace_id"],))
        await second.post("/api/auth/start")
        assert (await second.get("/api/projects/" + projects[0]["id"] + "/memory")).status_code == 404
        assert (await first.get("/api/projects")).json()[0]["id"] != (await second.get("/api/projects")).json()[0]["id"]


async def test_personal_connections_are_encrypted_scoped_selected_and_deletable():
    from collective.byok import decrypt
    from collective.db import db

    async with await client() as first, await client() as second:
        await first.post("/api/auth/start")
        await second.post("/api/auth/start")
        # Deliberately non-working test input. It is never sent to a provider.
        key = "nonworking-personal-scope-check-credential"
        invalid = await first.post("/api/profile/connections", json={"provider": "gemini", "api_key": key})
        assert invalid.status_code == 422 and key not in invalid.text
        saved = await first.post(
            "/api/profile/connections",
            json={
                "provider": "gemini",
                "label": "Scope check",
                "model": "not-an-inference-test",
                "protocol": "chat",
                "api_key": key,
                "activate": True,
            },
        )
        assert saved.status_code == 200
        identity = saved.json()["id"]
        row = await db.execute("SELECT * FROM provider_connections WHERE id=%s", (identity,), one=True)
        assert row["encrypted_key"] != key and key not in row["encrypted_key"] and decrypt(row["encrypted_key"]) == key
        view = await first.get("/api/profile")
        assert key not in view.text and "encrypted_key" not in view.text
        assert view.json()["host_key_fallback"] is False
        assert {"groq", "grok", "anthropic", "gemini", "openai", "deepseek", "opencode"} <= {
            p["id"] for p in view.json()["catalog"]
        }
        assert (await second.get("/api/profile")).json()["connections"] == []
        for path, method in [("/activate", "post"), ("/test", "post"), ("", "delete")]:
            response = await getattr(second, method)("/api/profile/connections/" + identity + path)
            assert response.status_code == 404
        other = await first.post(
            "/api/profile/connections",
            json={
                "provider": "openai",
                "label": "Second check",
                "model": "not-an-inference-test",
                "protocol": "responses",
                "api_key": key + "2",
                "activate": True,
            },
        )
        assert other.status_code == 200
        assert sum(item["active"] for item in (await first.get("/api/profile")).json()["connections"]) == 1
        assert (await first.post("/api/profile/connections/" + identity + "/activate")).status_code == 200
        assert (await first.post("/api/profile/services/langsearch", json={"api_key": key})).status_code == 200
        assert key not in (await first.get("/api/profile")).text
        assert (await second.get("/api/profile")).json()["services"] == []
        assert (await first.delete("/api/profile/services/langsearch")).status_code == 200
        for item in (await first.get("/api/profile")).json()["connections"]:
            assert (await first.delete("/api/profile/connections/" + item["id"])).status_code == 200
        assert not (await first.get("/api/me")).json()["has_provider"]


async def test_settings_context_and_sdk_clients_do_not_cross_users_or_threads():
    from collective.byok import CATALOG, endpoint
    from collective.models import chat_model
    from collective.settings import provider_settings, settings, base_settings

    async def inspect(identity, provider, protocol):
        token = provider_settings.set(
            {
                "provider_identity": identity,
                "agent_provider": provider,
                "agent_model": "configuration-check-only",
                "agent_protocol": protocol,
                "agent_api_key": identity,
                "agent_base_url": endpoint(provider, protocol),
                "anthropic_api_key": identity,
                "groq_api_key": identity,
            }
        )
        try:
            await asyncio.sleep(0)
            assert await asyncio.to_thread(lambda: settings.agent_api_key) == identity
            model = chat_model(max_tokens=512)
            secret = model.anthropic_api_key if protocol == "anthropic" else model.openai_api_key
            assert secret.get_secret_value() == identity
        finally:
            provider_settings.reset(token)

    await asyncio.gather(
        *(
            inspect("nonworking-configuration-check-" + provider + protocol, provider, protocol)
            for provider, data in CATALOG.items()
            for protocol in data["protocols"]
        )
    )
    assert settings.agent_provider == base_settings.agent_provider and settings.provider_identity == "host"


async def test_admission_connection_uses_only_its_owners_key():
    from collective.auth import Principal
    from collective.byok import scope
    from collective.settings import settings

    async with await client() as first, await client() as second:
        await first.post("/api/auth/start")
        await second.post("/api/auth/start")
        owner = (await first.get("/api/me")).json()
        policy = await first.post(
            "/api/profile/connections",
            json={
                "provider": "groq",
                "label": "Policy configuration check",
                "model": "openai/gpt-oss-safeguard-20b",
                "protocol": "chat",
                "api_key": "nonworking-policy-key-check",
                "activate": False,
            },
        )
        identity = policy.json()["id"]
        assert (await first.post("/api/profile/policy", json={"connection_id": identity})).status_code == 200
        assert (await second.post("/api/profile/policy", json={"connection_id": identity})).status_code == 404
        actor = Principal(owner["id"], owner["workspace_id"], "owner", "Check")
        async with scope(actor):
            assert not settings.agent_api_key
            assert settings.policy_override["groq_api_key"] == "nonworking-policy-key-check"
            assert settings.agent_provider == "unconfigured"
        assert "nonworking-policy-key-check" not in (await first.get("/api/profile")).text
        assert (await first.delete("/api/profile/connections/" + identity)).status_code == 200
        assert (await first.get("/api/profile")).json()["policy_connection_id"] is None
