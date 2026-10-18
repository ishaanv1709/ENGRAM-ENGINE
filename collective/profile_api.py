"""Personal BYOK management. Response models never contain stored key material."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr

from .auth import principal
from .byok import CATALOG, SERVICES, decrypt, encrypt, endpoint, overrides
from .db import db, uid
from .settings import provider_settings

router = APIRouter(prefix="/api/profile")
PUBLIC_COLUMNS = "id,provider,label,model,protocol,active,created_at,updated_at,tested_at,test_status"


class ConnectionInput(BaseModel):
    provider: str
    label: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=160)
    protocol: str = "chat"
    api_key: SecretStr
    activate: bool = False


class ServiceInput(BaseModel):
    api_key: SecretStr


class NameInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PolicyInput(BaseModel):
    connection_id: str | None = None


def checked_key(value):
    key = value.get_secret_value().strip()
    if not 8 <= len(key) <= 4096 or any(c.isspace() for c in key) or key in {"your_actual_key", "********"}:
        raise HTTPException(422, "Enter a valid provider API key without whitespace or placeholders")
    return key


@router.get("")
async def view(actor=Depends(principal)):
    return {
        "name": actor.name,
        "catalog": [{"id": key, **value} for key, value in CATALOG.items()],
        "connections": await db.execute(
            f"SELECT {PUBLIC_COLUMNS} FROM provider_connections WHERE user_id=%s AND tenant_id=%s ORDER BY created_at",
            (actor.user_id, actor.tenant_id),
        ),
        "services": [
            row["service"]
            for row in await db.execute(
                "SELECT service FROM user_service_keys WHERE user_id=%s AND tenant_id=%s",
                (actor.user_id, actor.tenant_id),
            )
        ],
        "storage": "encrypted_at_rest",
        "policy_connection_id": (
            await db.execute(
                "SELECT connection_id FROM user_policy_connections WHERE user_id=%s AND tenant_id=%s",
                (actor.user_id, actor.tenant_id),
                one=True,
            )
            or {}
        ).get("connection_id"),
        "host_key_fallback": False,
    }


@router.post("/name")
async def rename(body: NameInput, actor=Depends(principal)):
    await db.execute("UPDATE users SET name=%s WHERE id=%s", (body.name.strip(), actor.user_id))
    return {"updated": True}


@router.post("/policy")
async def choose_policy(body: PolicyInput, actor=Depends(principal)):
    if body.connection_id:
        await connection(actor, body.connection_id)
    await db.execute(
        "INSERT INTO user_policy_connections(user_id,tenant_id,connection_id) VALUES (%s,%s,%s) ON CONFLICT(user_id,tenant_id) DO UPDATE SET connection_id=EXCLUDED.connection_id",
        (actor.user_id, actor.tenant_id, body.connection_id),
    )
    return {"saved": True}


@router.post("/connections")
async def save(body: ConnectionInput, actor=Depends(principal)):
    endpoint(body.provider, body.protocol)
    if not body.model.strip():
        raise HTTPException(422, "Enter the provider's exact model ID")
    key = checked_key(body.api_key)
    identity = uid()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", (actor.user_id,))
            if body.activate:
                await conn.execute(
                    "UPDATE provider_connections SET active=false WHERE user_id=%s AND tenant_id=%s",
                    (actor.user_id, actor.tenant_id),
                )
            await conn.execute(
                "INSERT INTO provider_connections(id,user_id,tenant_id,provider,label,model,protocol,encrypted_key,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    identity,
                    actor.user_id,
                    actor.tenant_id,
                    body.provider,
                    body.label.strip(),
                    body.model.strip(),
                    body.protocol,
                    encrypt(key),
                    body.activate,
                ),
            )
    await db.event(
        actor.tenant_id,
        "profile.connection_saved",
        {"connection_id": identity, "provider": body.provider, "model": body.model, "user_id": actor.user_id},
    )
    return {"id": identity, "saved": True, "tested": False}


async def connection(actor, identity):
    row = await db.execute(
        "SELECT * FROM provider_connections WHERE id=%s AND user_id=%s AND tenant_id=%s",
        (identity, actor.user_id, actor.tenant_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Connection unavailable")
    return row


@router.post("/connections/{identity}/activate")
async def activate(identity: str, actor=Depends(principal)):
    await connection(actor, identity)
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT id FROM users WHERE id=%s FOR UPDATE", (actor.user_id,))
            await conn.execute(
                "UPDATE provider_connections SET active=false WHERE user_id=%s AND tenant_id=%s",
                (actor.user_id, actor.tenant_id),
            )
            await conn.execute(
                "UPDATE provider_connections SET active=true,updated_at=now() WHERE id=%s AND user_id=%s AND tenant_id=%s",
                (identity, actor.user_id, actor.tenant_id),
            )
    return {"selected": True}


@router.delete("/connections/{identity}")
async def remove(identity: str, actor=Depends(principal)):
    await connection(actor, identity)
    await db.execute(
        "DELETE FROM provider_connections WHERE id=%s AND user_id=%s AND tenant_id=%s",
        (identity, actor.user_id, actor.tenant_id),
    )
    return {"deleted": True}


@router.post("/connections/{identity}/test")
async def test(identity: str, actor=Depends(principal)):
    row = await connection(actor, identity)
    values = await overrides(actor)
    key = decrypt(row["encrypted_key"])
    values.update(
        agent_provider=row["provider"],
        agent_model=row["model"],
        agent_protocol=row["protocol"],
        agent_api_key=key,
        agent_base_url=endpoint(row["provider"], row["protocol"]),
    )
    if row["provider"] == "groq":
        values["groq_api_key"] = key
    if row["provider"] == "anthropic":
        values["anthropic_api_key"] = key
    token = provider_settings.set(values)
    try:
        from .models import chat_model

        nonce = secrets.token_hex(6)
        tool = {
            "type": "function",
            "function": {
                "name": "engram_connection_check",
                "description": "Return the supplied nonce for a harmless connection check.",
                "parameters": {"type": "object", "properties": {"nonce": {"type": "string"}}, "required": ["nonce"]},
            },
        }
        reply = (
            await chat_model(max_tokens=512)
            .bind_tools([tool])
            .ainvoke("Call engram_connection_check exactly once with nonce " + nonce + ". Do not answer in plain text.")
        )
        if not any(
            item["name"] == "engram_connection_check" and item["args"] == {"nonce": nonce} for item in reply.tool_calls
        ):
            raise ValueError("The selected model did not return the required tool call")
        await db.execute(
            "UPDATE provider_connections SET tested_at=now(),test_status='tool_call_passed' WHERE id=%s AND user_id=%s",
            (identity, actor.user_id),
        )
        return {
            "passed": True,
            "scope": "Actual inference and exact tool-call argument check; not a full autonomous workflow",
        }
    except Exception as exc:
        await db.execute(
            "UPDATE provider_connections SET tested_at=now(),test_status=%s WHERE id=%s AND user_id=%s",
            ("failed:" + type(exc).__name__, identity, actor.user_id),
        )
        raise HTTPException(
            502,
            "Connection test failed ("
            + type(exc).__name__
            + "). Check the exact model ID, API protocol, key permissions and provider quota. No substitute was used.",
        ) from None
    finally:
        provider_settings.reset(token)


@router.post("/services/{service}")
async def save_service(service: str, body: ServiceInput, actor=Depends(principal)):
    if service not in SERVICES:
        raise HTTPException(422, "Choose LangSearch or Tavily")
    await db.execute(
        "INSERT INTO user_service_keys(user_id,tenant_id,service,encrypted_key) VALUES (%s,%s,%s,%s) ON CONFLICT(user_id,tenant_id,service) DO UPDATE SET encrypted_key=EXCLUDED.encrypted_key,updated_at=now()",
        (actor.user_id, actor.tenant_id, service, encrypt(checked_key(body.api_key))),
    )
    return {"saved": True}


@router.delete("/services/{service}")
async def remove_service(service: str, actor=Depends(principal)):
    if service not in SERVICES:
        raise HTTPException(422, "Unknown service")
    await db.execute(
        "DELETE FROM user_service_keys WHERE user_id=%s AND tenant_id=%s AND service=%s",
        (actor.user_id, actor.tenant_id, service),
    )
    return {"deleted": True}
