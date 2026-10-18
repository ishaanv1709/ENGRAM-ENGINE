"""Actual auth routes and database state, without provider inference."""
import os
import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires local PostgreSQL")]


async def test_https_session_and_anonymous_scope():
    from collective.app import app
    from collective.db import db, uid
    await db.open()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="https://testserver") as client:
        for path in ("/api/projects", "/api/events", "/api/jobs", "/api/members", "/api/workflows/unknown", "/api/artifacts/unknown/download"):
            assert (await client.get(path)).status_code == 401
        credentials = {"email":f"https-check-{uid()}@example.test", "password":"Https-check-password-123", "name":"HTTPS check"}
        assert (await client.post("/api/auth/register",json=credentials)).status_code == 403
        bad = await client.post("/api/auth/register",json=credentials,headers={"X-Engram-Request":"1","Origin":"https://unapproved.example"})
        assert bad.status_code == 403
        result = await client.post("/api/auth/register",json=credentials,headers={"X-Engram-Request":"1"})
        assert result.status_code == 200
        cookie = result.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert (await client.get("/api/me")).status_code == 200
        assert (await client.get("/api/projects")).json() == []
        response = await client.get("/.env.collective")
        assert "text/html" in response.headers["content-type"]
        assert "GROQ_API_KEY=" not in response.text and "DATABASE_URL=" not in response.text
