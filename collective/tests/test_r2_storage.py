"""Actual Cloudflare R2 and PostgreSQL tests, with no provider inference."""
import hashlib
import os
from pathlib import Path

from dotenv import dotenv_values
from fastapi import HTTPException
import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_R2_INTEGRATION") != "1", reason="Requires configured actual Cloudflare R2"),
]


def configure(monkeypatch):
    from collective.settings import base_settings

    values = dotenv_values(Path(".env.cloudflare"))
    monkeypatch.setattr(base_settings, "artifact_backend", "r2")
    monkeypatch.setattr(base_settings, "artifact_service_token", values["ARTIFACT_SERVICE_TOKEN"])
    monkeypatch.setattr(base_settings, "artifact_service_origin", "https://" + values["ENGRAM_PUBLIC_HOSTNAME"])


async def test_real_r2_integrity_authentication_and_no_fallback(monkeypatch):
    from collective.artifact_store import read, store, service_url
    from collective.db import uid

    configure(monkeypatch)
    tenant, artifact_id = uid(), uid()
    data = b"ENGRAM private cloud artifact verification. No provider calls.\n"
    digest = hashlib.sha256(data).hexdigest()
    path = await store(tenant, artifact_id, data, digest)
    artifact = {"path": path, "id": artifact_id, "tenant_id": tenant, "sha256": digest}
    assert path.startswith("r2://")
    assert await read(artifact) == data
    from collective.settings import settings

    url = service_url(f"v1/{tenant}/{artifact_id}/{digest}")
    async with httpx.AsyncClient(timeout=60) as client:
        assert (await client.get(url)).status_code == 404
        assert (await client.get(url, headers={"Authorization": "Bearer invalid"})).status_code == 404
        invalid = await client.put(url, content=b"corrupted",
            headers={"Authorization": "Bearer " + settings.artifact_service_token})
        assert invalid.status_code == 409
    assert await read(artifact) == data  # Rejected overwrite preserved original bytes.
    with pytest.raises(HTTPException) as wrong_tenant:
        await read({**artifact, "tenant_id": uid()})
    assert wrong_tenant.value.status_code == 409
    from collective.settings import base_settings
    monkeypatch.setattr(base_settings, "artifact_service_token", "invalid" * 8)
    with pytest.raises(httpx.HTTPStatusError):
        await read(artifact)  # A storage failure cannot fall back to local bytes.


async def test_real_r2_published_artifact_download_and_tenant_denial(monkeypatch):
    from collective.app import app
    from collective.auth import Principal, issue_session, register
    from collective.db import db, uid
    from collective.repositories import import_zip, read_file
    from collective.sandbox import publish_artifact
    import io
    import zipfile

    configure(monkeypatch)
    await db.open()
    actors = []
    for _ in range(2):
        user = await register(f"cloud-storage-{uid()}@example.test", "Cloud-storage-check-password-123", "Storage check", "Storage checks")
        member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
        actors.append(Principal(user, member["tenant_id"], "owner", "Storage check"))
    actor, outsider = actors
    project = uid()
    await db.execute("INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Actual R2 integration')", (project, actor.tenant_id))
    data = b"Actual cloud object, authorized through the ENGRAM API.\n"
    published = await publish_artifact(actor, project, None, "private-proof.txt", data)
    row = await db.execute("SELECT * FROM artifacts WHERE id=%s", (published["id"],), one=True)
    assert row["path"].startswith("r2://")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://engram.test") as client:
        client.cookies.set("engram_session", await issue_session(actor.user_id))
        downloaded = await client.get(f"/api/artifacts/{published['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content == data
        assert downloaded.headers["cache-control"] == "no-store"
        client.cookies.set("engram_session", await issue_session(outsider.user_id))
        assert (await client.get(f"/api/artifacts/{published['id']}/download")).status_code == 404
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("cloud-proof.py", "print('actual R2 source snapshot')\n")
    snapshot = await import_zip(actor, project, "cloud-proof.zip", stream.getvalue())
    assert (await read_file(actor, project, snapshot["id"], "cloud-proof.py"))["content"] == "print('actual R2 source snapshot')\n"
