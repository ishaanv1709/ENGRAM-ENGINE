import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request

from .db import db, uid

hasher = PasswordHasher()


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str
    name: str

    def write(self):
        if self.role == "viewer":
            raise HTTPException(403, "Read-only workspace membership")


async def principal(request: Request) -> Principal:
    token = request.cookies.get("engram_session", "")
    if not token:
        raise HTTPException(401, "Sign in to continue")
    tenant = request.headers.get("X-Workspace", "")
    row = await db.execute(
        """SELECT u.id,u.name,m.tenant_id,m.role FROM auth_sessions s
      JOIN users u ON u.id=s.user_id JOIN memberships m ON m.user_id=u.id
      WHERE s.token_hash=%s AND s.expires_at>now() AND (%s='' OR m.tenant_id=%s)
      ORDER BY m.tenant_id LIMIT 1""",
        (hashlib.sha256(token.encode()).hexdigest(), tenant, tenant),
        one=True,
    )
    if not row:
        raise HTTPException(401, "Session expired or workspace unavailable")
    return Principal(row["id"], row["tenant_id"], row["role"], row["name"])


async def register(email, password, name, workspace):
    user, tenant = uid(), uid()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            if await (await conn.execute("SELECT 1 FROM users WHERE email=%s", (email.lower(),))).fetchone():
                raise HTTPException(409, "An account with that email exists")
            await conn.execute(
                "INSERT INTO users(id,email,name,password_hash) VALUES (%s,%s,%s,%s)",
                (user, email.lower(), name, hasher.hash(password)),
            )
            await conn.execute("INSERT INTO tenants(id,name) VALUES (%s,%s)", (tenant, workspace))
            await conn.execute("INSERT INTO memberships VALUES (%s,%s,'owner')", (tenant, user))
    return user


async def login(email, password):
    row = await db.execute("SELECT * FROM users WHERE email=%s", (email.lower(),), one=True)
    # Verify an Argon2 hash even for unknown users to avoid a cheap timing oracle.
    digest = row["password_hash"] if row else DUMMY_HASH
    try:
        hasher.verify(digest, password)
    except VerificationError:
        raise HTTPException(401, "Incorrect email or password") from None
    if not row:
        raise HTTPException(401, "Incorrect email or password")
    return row["id"]


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


async def issue_session(user_id, days=7):
    token = secrets.token_urlsafe(48)
    await db.execute(
        "INSERT INTO auth_sessions VALUES (%s,%s,%s)",
        (hashlib.sha256(token.encode()).hexdigest(), user_id, datetime.now(timezone.utc) + timedelta(days=days)),
    )
    return token
