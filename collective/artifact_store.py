"""Checksum-verified local or private R2 artifacts. No storage fallback."""
import asyncio
import hashlib
import hmac
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from .settings import DependencyUnavailable, settings

KEY = re.compile(r"v1/[a-f0-9-]{36}/[a-f0-9-]{36}/[a-f0-9]{64}")


def service_url(key):
    origin = urlsplit(settings.artifact_service_origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in {"", "/"} or origin.query or origin.fragment or not KEY.fullmatch(key)
            or len(settings.artifact_service_token) < 32):
        raise DependencyUnavailable("Private R2 artifact service is not configured")
    return settings.artifact_service_origin.rstrip("/") + "/internal/artifacts/" + key


async def store(tenant_id, artifact_id, data, digest):
    if settings.artifact_backend == "local":
        root = settings.artifact_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        path = root / artifact_id
        await asyncio.to_thread(path.write_bytes, data)
        return str(path)
    if settings.artifact_backend != "r2":
        raise DependencyUnavailable("Unsupported artifact storage backend")
    key = f"v1/{tenant_id}/{artifact_id}/{digest}"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.put(service_url(key), content=data,
            headers={"Authorization": "Bearer " + settings.artifact_service_token})
        response.raise_for_status()
        receipt = response.json()
        if receipt.get("sha256") != digest or receipt.get("size") != len(data):
            raise DependencyUnavailable("Private R2 artifact receipt is invalid")
    return f"r2://{settings.artifact_bucket}/{key}"


async def read(artifact):
    """Callers must first authorize the artifact's tenant, project and visibility."""
    path = artifact["path"]
    if path.startswith("r2://"):
        parsed = urlsplit(path)
        if parsed.netloc != settings.artifact_bucket or parsed.query or parsed.fragment:
            raise DependencyUnavailable("Unexpected artifact bucket")
        key = parsed.path.lstrip("/")
        if not KEY.fullmatch(key) or key.split("/")[-1] != artifact["sha256"]:
            raise HTTPException(409, "Artifact locator does not match the published checksum")
        if artifact.get("id") and key.split("/")[2] != artifact["id"]:
            raise HTTPException(409, "Artifact locator does not match its identity")
        if artifact.get("tenant_id") and key.split("/")[1] != artifact["tenant_id"]:
            raise HTTPException(409, "Artifact locator does not match its tenant")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(service_url(key),
                headers={"Authorization": "Bearer " + settings.artifact_service_token})
            response.raise_for_status()
            data = response.content
    else:
        local = Path(path).resolve()
        if not local.is_relative_to(settings.artifact_root.resolve()):
            raise HTTPException(409, "Artifact path is outside configured storage")
        data = await asyncio.to_thread(local.read_bytes)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), artifact["sha256"]):
        raise HTTPException(409, "Artifact contents no longer match the published checksum")
    return data
