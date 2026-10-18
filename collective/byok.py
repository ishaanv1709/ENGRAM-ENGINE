"""Encrypted personal provider connections and task-local routing. Never exports keys."""

from contextlib import asynccontextmanager
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi import HTTPException

from .db import db
from .settings import base_settings, provider_settings

CATALOG = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "protocols": ["chat"],
        "docs": "https://console.groq.com/keys",
    },
    "grok": {
        "name": "Grok / xAI",
        "base_url": "https://api.x.ai/v1",
        "protocols": ["chat", "responses"],
        "docs": "https://console.x.ai/",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "protocols": ["anthropic"],
        "docs": "https://console.anthropic.com/",
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "protocols": ["chat"],
        "docs": "https://aistudio.google.com/apikey",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "protocols": ["responses", "chat"],
        "docs": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "protocols": ["chat"],
        "docs": "https://platform.deepseek.com/",
    },
    "opencode": {
        "name": "OpenCode Console / Zen",
        "base_url": "https://opencode.ai/inference",
        "protocols": ["chat", "responses", "anthropic"],
        "docs": "https://opencode.ai/v2/docs/console/models/",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "protocols": ["chat"],
        "docs": "https://openrouter.ai/keys",
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "protocols": ["chat"],
        "docs": "https://console.mistral.ai/",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "protocols": ["chat"],
        "docs": "https://api.together.ai/",
    },
    "fireworks": {
        "name": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "protocols": ["chat"],
        "docs": "https://fireworks.ai/",
    },
}
SERVICES = {"langsearch", "tavily"}


def cipher():
    if base_settings.provider_encryption_key:
        return Fernet(base_settings.provider_encryption_key.encode())
    path = Path("data/collective/secrets/provider.key")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(Fernet.generate_key())
    return Fernet(path.read_bytes())


def encrypt(value):
    return cipher().encrypt(value.encode()).decode()


def decrypt(value):
    return cipher().decrypt(value.encode()).decode()


def endpoint(provider, protocol):
    if provider not in CATALOG or protocol not in CATALOG[provider]["protocols"]:
        raise HTTPException(422, "Choose a supported provider and API protocol")
    base = CATALOG[provider]["base_url"]
    if provider == "opencode":
        return base + ("/anthropic" if protocol == "anthropic" else "/openai/v1")
    return base


async def overrides(actor):
    row = await db.execute(
        "SELECT * FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active",
        (actor.user_id, actor.tenant_id),
        one=True,
    )
    # No user session or background task may inherit the operator's credentials.
    values = {
        "groq_api_key": "",
        "anthropic_api_key": "",
        "jev_api_key": "",
        "tavily_api_key": "",
        "langsearch_api_key": "",
        "agent_api_key": "",
        "agent_provider": "unconfigured",
        "agent_model": "",
        "agent_base_url": "",
        "decision_provider": "personal_model",
        "provider_identity": actor.user_id + ":" + actor.tenant_id,
    }
    if row:
        key = decrypt(row["encrypted_key"])
        values.update(
            agent_provider=row["provider"],
            agent_model=row["model"],
            agent_api_key=key,
            agent_protocol=row["protocol"],
            agent_base_url=endpoint(row["provider"], row["protocol"]),
            provider_identity=row["id"] + ":" + hashlib.sha256(row["encrypted_key"].encode()).hexdigest(),
        )
        if row["provider"] == "groq":
            values["groq_api_key"] = key
        if row["provider"] == "anthropic":
            values["anthropic_api_key"] = key
    services = await db.execute(
        "SELECT service,encrypted_key FROM user_service_keys WHERE user_id=%s AND tenant_id=%s",
        (actor.user_id, actor.tenant_id),
    )
    policy = await db.execute(
        "SELECT p.* FROM provider_connections p JOIN user_policy_connections s ON s.connection_id=p.id WHERE s.user_id=%s AND s.tenant_id=%s AND p.user_id=s.user_id AND p.tenant_id=s.tenant_id",
        (actor.user_id, actor.tenant_id),
        one=True,
    )
    values["policy_override"] = None
    if policy:
        policy_key = decrypt(policy["encrypted_key"])
        values["policy_override"] = {
            "agent_provider": policy["provider"],
            "agent_model": policy["model"],
            "agent_protocol": policy["protocol"],
            "agent_api_key": policy_key,
            "agent_base_url": endpoint(policy["provider"], policy["protocol"]),
            "groq_api_key": policy_key if policy["provider"] == "groq" else "",
            "anthropic_api_key": policy_key if policy["provider"] == "anthropic" else "",
            "safeguard_model": policy["model"],
        }
    for service in services:
        values[service["service"] + "_api_key"] = decrypt(service["encrypted_key"])
    values["web_search_provider"] = "langsearch" if values["langsearch_api_key"] else "tavily"
    return values


@asynccontextmanager
async def scope(actor):
    token = provider_settings.set(await overrides(actor))
    try:
        yield
    finally:
        provider_settings.reset(token)


def require_personal_model():
    from .settings import settings, DependencyUnavailable

    if not settings.agent_api_key:
        raise DependencyUnavailable(
            "Add and select your own AI connection in Profile & settings before starting. No host key is used."
        )
