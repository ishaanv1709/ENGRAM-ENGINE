import asyncio
import hashlib
import io
import json
import logging
import time
import secrets
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import Principal, issue_session, login, principal, register
from .db import db, uid
from .graph import graph
from .memory import memory, visible
from .runtime import create_run, handoff
from .sandbox import publish_artifact
from .settings import DependencyUnavailable, configured, settings
from .workflow_api import router as workflow_router
from .profile_api import router as profile_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    try:
        await db.open()
    except Exception as exc:
        logger.error("PostgreSQL startup unavailable: %s", type(exc).__name__)
    yield
    await db.pool.close()


app = FastAPI(title="ENGRAM Collective", version="1.0.0", lifespan=lifespan)
app.include_router(workflow_router)
app.include_router(profile_router)
attempts = defaultdict(deque)


@app.middleware("http")
async def request_security(request, call_next):
    if int(request.headers.get("content-length", "0")) > 12_000_000:
        return JSONResponse({"detail": "Request exceeds 12 MB"}, status_code=413)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.origins:
            return JSONResponse({"detail": "Origin not permitted"}, status_code=403)
        if request.headers.get("X-Engram-Request") != "1":
            return JSONResponse({"detail": "Missing request protection header"}, status_code=403)
    if db.ready and request.cookies.get("engram_session"):
        try:
            actor = await principal(request)
        except HTTPException:
            response = await call_next(request)
        else:
            from .byok import scope

            async with scope(actor):
                response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.exception_handler(DependencyUnavailable)
async def dependency_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=503)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Validation errors can otherwise echo an entire body containing API keys.
    return JSONResponse(
        {"detail": [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()]},
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error("Request %s failed: %s", request.url.path, type(exc).__name__)
    return JSONResponse(
        {
            "detail": "A required operation failed. Check service status and local logs; no substitute result was generated."
        },
        status_code=503,
    )


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(default="", max_length=100)
    workspace: str = Field(default="My workspace", min_length=1, max_length=100)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)


class RunInput(BaseModel):
    objective: str = Field(min_length=3, max_length=12000)
    role: str = "coordinator"
    conversation_id: str | None = None
    context_scope: Literal["auto", "team"] = "auto"
    memory_ids: list[str] | None = Field(default=None, max_length=32)


class MemoryInput(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    visibility: str = "team"


class Correction(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    expected_revision: int = Field(ge=1)


class MemberInput(BaseModel):
    email: str
    role: str = "member"


class HandoffInput(BaseModel):
    role: str
    checkpoint: str
    remaining: str
    evidence_ids: list[str] = []
    artifact_ids: list[str] = []
    check_event_ids: list[int] = Field(default_factory=list)


class MCPInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str
    allowed_tools: list[str] = []


async def project_access(project_id: str, actor: Principal):
    row = await db.execute(
        "SELECT * FROM projects WHERE id=%s AND tenant_id=%s", (project_id, actor.tenant_id), one=True
    )
    if not row:
        raise HTTPException(404, "Project not found")
    return row


async def run_access(run_id, actor):
    row = await db.execute("SELECT * FROM runs WHERE id=%s AND tenant_id=%s", (run_id, actor.tenant_id), one=True)
    if not row:
        raise HTTPException(404, "Task not found")
    if row["visibility"] != "team" and row["user_id"] != actor.user_id:
        raise HTTPException(404, "Task not found")
    return row


@app.get("/api/health")
async def health():
    async def probe(name, fn):
        try:
            await asyncio.wait_for(fn(), 4)
            return name, {"state": "ready"}
        except Exception as exc:
            return name, {"state": "unavailable", "reason": type(exc).__name__}

    async def postgres():
        await db.execute("SELECT 1")

    async def falkor():
        await asyncio.to_thread(lambda: graph.client.connection.ping())

    async def http_probe(url, headers=None):
        async with httpx.AsyncClient(timeout=3) as client:
            (await client.get(url, headers=headers)).raise_for_status()

    async def worker_probe():
        row = await db.execute(
            "SELECT sum(slots) AS slots FROM workers WHERE last_seen>now()-interval '30 seconds'", one=True
        )
        if not row["slots"]:
            raise DependencyUnavailable("Start the agent worker")

    async def sandbox_probe():
        from .sandbox import docker_command

        code, _, _ = await docker_command("image", "inspect", settings.sandbox_image, "--format", "{{.Id}}", timeout=5)
        if code:
            raise DependencyUnavailable("Build the local sandbox image")

    checks = dict(
        await asyncio.gather(
            probe("postgres", postgres),
            probe("falkordb", falkor),
            probe("embeddings", lambda: http_probe(settings.embedding_url.rsplit("/v1", 1)[0] + "/health")),
            probe("qdrant", lambda: http_probe(settings.qdrant_url.rstrip("/") + "/healthz",
                {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else None)),
            probe("worker", worker_probe),
            probe("sandbox", sandbox_probe),
        )
    )
    if settings.decision_provider == "kev":
        name, status = await probe("kev", lambda: http_probe(settings.decision_url.rsplit("/v1/", 1)[0] + "/v1/models"))
        checks[name] = status
    personal = settings.provider_identity != "host"
    main_key = settings.agent_api_key if personal else ""
    policy = settings.policy_override if personal else None
    for name, value in [
        ("agent_model", main_key),
        ("admission", policy["agent_api_key"] if policy else main_key),
        (
            "web_search",
            (settings.langsearch_api_key if settings.web_search_provider == "langsearch" else settings.tavily_api_key)
            if personal
            else "",
        ),
    ]:
        checks[name] = {"state": "configured_not_verified" if configured(value) else "needs_key"}
    if personal:
        checks["agent_model"].update(provider=settings.agent_provider, model=settings.agent_model)
    checks["triton"] = {"state": "deferred"}
    return {"name": "ENGRAM Collective", "services": checks, "database_ready": db.ready}


def limit_login(request):
    key = request.client.host
    q = attempts[key]
    while q and q[0] < time.monotonic() - 60:
        q.popleft()
    if len(q) >= 10:
        raise HTTPException(429, "Too many authentication attempts; wait one minute")
    q.append(time.monotonic())
    if len(attempts) > 10000:
        attempts.clear()


@app.post("/api/auth/register")
async def register_route(body: Credentials, request: Request, response: Response):
    limit_login(request)
    if not db.ready:
        raise DependencyUnavailable("PostgreSQL must be running before creating an account")
    user_id = await register(body.email, body.password, body.name or body.email.split("@")[0], body.workspace)
    await db.execute("UPDATE users SET browser_workspace=true WHERE id=%s", (user_id,))
    response.set_cookie(
        "engram_session",
        await issue_session(user_id),
        httponly=True,
        secure=settings.cookie_secure or request.url.scheme == "https",
        samesite="strict",
        max_age=604800,
    )
    return {"user_id": user_id}


@app.post("/api/auth/start")
async def start_building(request: Request, response: Response):
    if request.cookies.get("engram_session"):
        try:
            actor = await principal(request)
            return {"user_id": actor.user_id, "resumed": True}
        except HTTPException:
            pass
    limit_login(request)
    identity = uid()
    user = await register(
        "builder-" + identity + "@browser.engram.invalid", secrets.token_urlsafe(48), "Builder", "My workspace"
    )
    await db.execute("UPDATE users SET browser_workspace=true WHERE id=%s", (user,))
    project = uid()
    member = await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True)
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'My first project')", (project, member["tenant_id"])
    )
    response.set_cookie(
        "engram_session",
        await issue_session(user, days=365),
        httponly=True,
        secure=settings.cookie_secure or request.url.scheme == "https",
        samesite="strict",
        max_age=31536000,
    )
    return {"user_id": user, "project_id": project, "resumed": False}


@app.post("/api/auth/login")
async def login_route(body: Credentials, request: Request, response: Response):
    limit_login(request)
    user_id = await login(body.email, body.password)
    response.set_cookie(
        "engram_session",
        await issue_session(user_id),
        httponly=True,
        secure=settings.cookie_secure or request.url.scheme == "https",
        samesite="strict",
        max_age=604800,
    )
    return {"user_id": user_id}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("engram_session", "")
    await db.execute("DELETE FROM auth_sessions WHERE token_hash=%s", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie("engram_session")
    return {"signed_out": True}


@app.get("/api/me")
async def me(actor=Depends(principal)):
    workspaces = await db.execute(
        "SELECT t.id,t.name,m.role FROM tenants t JOIN memberships m ON m.tenant_id=t.id WHERE m.user_id=%s ORDER BY t.created_at",
        (actor.user_id,),
    )
    return {
        "id": actor.user_id,
        "name": actor.name,
        "workspace_id": actor.tenant_id,
        "role": actor.role,
        "workspaces": workspaces,
        "has_provider": bool(
            await db.execute(
                "SELECT id FROM provider_connections WHERE user_id=%s AND tenant_id=%s AND active",
                (actor.user_id, actor.tenant_id),
                one=True,
            )
        ),
        "browser_workspace": bool(
            (await db.execute("SELECT browser_workspace FROM users WHERE id=%s", (actor.user_id,), one=True))[
                "browser_workspace"
            ]
        ),
    }


@app.post("/api/workspaces")
async def new_workspace(body: ProjectInput, actor=Depends(principal)):
    tenant = uid()
    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("INSERT INTO tenants(id,name) VALUES (%s,%s)", (tenant, body.name))
            await conn.execute("INSERT INTO memberships VALUES (%s,%s,'owner')", (tenant, actor.user_id))
    return {"id": tenant, "name": body.name}


@app.get("/api/members")
async def members(actor=Depends(principal)):
    return await db.execute(
        "SELECT u.id,u.email,u.name,m.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.tenant_id=%s",
        (actor.tenant_id,),
    )


@app.post("/api/members")
async def add_member(body: MemberInput, actor=Depends(principal)):
    if actor.role != "owner" or body.role not in {"member", "viewer"}:
        raise HTTPException(403, "Workspace owner can add members or viewers")
    user = await db.execute("SELECT id FROM users WHERE email=%s", (body.email.lower(),), one=True)
    if not user:
        raise HTTPException(404, "User must register an account first")
    existing = await db.execute(
        "SELECT role FROM memberships WHERE tenant_id=%s AND user_id=%s", (actor.tenant_id, user["id"]), one=True
    )
    if existing and existing["role"] == "owner":
        raise HTTPException(409, "This operation cannot change an owner's role")
    await db.execute(
        "INSERT INTO memberships VALUES (%s,%s,%s) ON CONFLICT(tenant_id,user_id) DO UPDATE SET role=EXCLUDED.role",
        (actor.tenant_id, user["id"], body.role),
    )
    return {"added": True}


@app.get("/api/projects")
async def projects(actor=Depends(principal)):
    return await db.execute("SELECT * FROM projects WHERE tenant_id=%s ORDER BY created_at", (actor.tenant_id,))


@app.post("/api/projects")
async def create_project(body: ProjectInput, actor=Depends(principal)):
    actor.write()
    await graph.ensure(actor.tenant_id)
    row = await db.execute(
        "INSERT INTO projects(id,tenant_id,name,description) VALUES (%s,%s,%s,%s) RETURNING *",
        (uid(), actor.tenant_id, body.name, body.description),
        one=True,
    )
    await db.event(actor.tenant_id, "project.created", {"project_id": row["id"], "name": body.name})
    return row


@app.get("/api/projects/{project_id}/conversations")
async def conversations(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await db.execute(
        "SELECT * FROM conversations WHERE tenant_id=%s AND project_id=%s AND user_id=%s ORDER BY created_at DESC",
        (actor.tenant_id, project_id, actor.user_id),
    )


@app.post("/api/projects/{project_id}/conversations")
async def create_conversation(project_id: str, body: ProjectInput, actor=Depends(principal)):
    actor.write()
    await project_access(project_id, actor)
    return await db.execute(
        "INSERT INTO conversations(id,tenant_id,project_id,user_id,title) VALUES (%s,%s,%s,%s,%s) RETURNING *",
        (uid(), actor.tenant_id, project_id, actor.user_id, body.name),
        one=True,
    )


@app.get("/api/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, actor=Depends(principal)):
    row = await db.execute(
        "SELECT id FROM conversations WHERE id=%s AND tenant_id=%s AND user_id=%s",
        (conversation_id, actor.tenant_id, actor.user_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Conversation unavailable")
    return await db.execute("SELECT * FROM messages WHERE conversation_id=%s ORDER BY created_at", (conversation_id,))


@app.get("/api/projects/{project_id}/runs")
async def runs(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await db.execute(
        "SELECT * FROM runs WHERE tenant_id=%s AND project_id=%s AND (visibility='team' OR user_id=%s) ORDER BY created_at DESC LIMIT 200",
        (actor.tenant_id, project_id, actor.user_id),
    )


@app.post("/api/projects/{project_id}/runs")
async def submit_run(project_id: str, body: RunInput, actor=Depends(principal)):
    await project_access(project_id, actor)
    from .byok import require_personal_model

    require_personal_model()
    if body.conversation_id:
        conv = await db.execute(
            "SELECT id FROM conversations WHERE id=%s AND tenant_id=%s AND project_id=%s AND user_id=%s",
            (body.conversation_id, actor.tenant_id, project_id, actor.user_id),
            one=True,
        )
        if not conv:
            raise HTTPException(404, "Conversation unavailable")
    run = await create_run(
        actor,
        project_id,
        body.objective,
        body.role,
        conversation=body.conversation_id,
        context_scope=body.context_scope,
        memory_ids=body.memory_ids,
    )
    if body.conversation_id:
        await db.execute(
            "INSERT INTO messages(id,conversation_id,tenant_id,role,content) VALUES (%s,%s,%s,'user',%s)",
            (uid(), body.conversation_id, actor.tenant_id, body.objective),
        )
    return run


@app.post("/api/runs/{run_id}/{action}")
async def control_run(run_id: str, action: str, actor=Depends(principal)):
    actor.write()
    run = await run_access(run_id, actor)
    if action == "cancel":
        status = "cancelled"
    elif action == "resume" and run["status"] in {"blocked", "failed", "stale", "cancelled"}:
        from .context_passports import current_reference
        for memory_id in run.get("memory_refs") or []:
            record = await memory.get(actor, run["project_id"], memory_id, run["id"])
            if not current_reference(record):
                raise HTTPException(409, "Bound evidence changed. Create a revised plan from the causal timeline instead of retrying stale references.")
        status = "queued"
    else:
        raise HTTPException(409, "Action is not valid for the current task state")
    await db.execute(
        "UPDATE runs SET status=%s,attempt=0,error=NULL,revision=revision+1,lease_token=NULL,lease_until=NULL,updated_at=now() WHERE id=%s",
        (status, run_id),
    )
    await db.event(actor.tenant_id, "task." + action, {"task_id": run_id}, run_id)
    return {"status": status}


@app.post("/api/runs/{run_id}/handoffs/create")
async def handoff_route(run_id: str, body: HandoffInput, actor=Depends(principal)):
    actor.write()
    run = await run_access(run_id, actor)
    return await handoff(
        actor,
        run,
        body.role,
        body.checkpoint,
        body.evidence_ids,
        body.artifact_ids,
        body.remaining,
        body.check_event_ids,
    )


@app.get("/api/projects/{project_id}/memory")
async def memories(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    records = await graph.list(actor.tenant_id, project_id, 1000)
    return [
        r
        for r in records
        if visible(r, actor, project_id) or (r["visibility"] == "agent" and r["owner_id"] == actor.user_id)
    ]


@app.post("/api/projects/{project_id}/memory/{memory_id}/publish")
async def publish_memory(project_id: str, memory_id: str, actor=Depends(principal)):
    actor.write()
    await project_access(project_id, actor)
    record = await graph.get(actor.tenant_id, memory_id)
    if not record or record["project_id"] != project_id or record["owner_id"] != actor.user_id:
        raise HTTPException(404, "Only your own memory can be published")
    if record["status"] != "active":
        raise HTTPException(409, "Only active memory can be published")
    result = await memory.commit(
        actor,
        project_id,
        record["content"],
        category=record["category"],
        memory_type=record["memory_type"],
        visibility="team",
        agent_id=record.get("agent_id", ""),
        source_ids=[record["id"]],
        entities=record.get("entities"),
        triples=record.get("triples"),
        metadata={**record.get("metadata", {}), "promoted_by": actor.user_id},
        allow_promotion=True,
    )
    await db.event(actor.tenant_id, "memory.published", {"source_id": memory_id, "published_id": result["id"]})
    return result


@app.post("/api/projects/{project_id}/memory")
async def add_memory(project_id: str, body: MemoryInput, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await memory.ingest(actor, project_id, body.content, body.visibility)


@app.post("/api/projects/{project_id}/memory/{memory_id}/correct")
async def correct(project_id: str, memory_id: str, body: Correction, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await memory.supersede(actor, project_id, memory_id, body.content, body.expected_revision)


@app.post("/api/projects/{project_id}/search")
async def search(project_id: str, body: MemoryInput, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await memory.context(actor, project_id, body.content)


@app.get("/api/projects/{project_id}/graph")
async def graph_view(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    data = await graph.view(actor.tenant_id, project_id)
    data["nodes"] = [
        r for r in data["nodes"] if visible(r, actor, project_id) and r.get("metadata", {}).get("kind") != "tool"
    ]
    ids = {r["id"] for r in data["nodes"]}
    data["edges"] = [r for r in data["edges"] if r["source"] in ids and r["target"] in ids]
    for mid, eid, name in await graph.entity_view(actor.tenant_id, list(ids)):
        if eid not in ids:
            data["nodes"].append({"id": eid, "content": name, "memory_type": "entity", "category": "entity"})
            ids.add(eid)
        data["edges"].append({"source": mid, "target": eid, "type": "MENTIONS"})
    tasks = await db.execute(
        "SELECT id,objective,status,role FROM runs WHERE tenant_id=%s AND project_id=%s AND (visibility='team' OR user_id=%s) ORDER BY created_at DESC LIMIT 100",
        (actor.tenant_id, project_id, actor.user_id),
    )
    data["nodes"].extend({**t, "content": t["objective"], "memory_type": "task", "category": t["role"]} for t in tasks)
    ids.update(t["id"] for t in tasks)
    causal = await graph.query(
        actor.tenant_id,
        "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids RETURN a.id,type(r),b.id LIMIT 700",
        {"ids": list(ids)},
    )
    data["edges"] = [{"source": r[0], "type": r[1], "target": r[2]} for r in causal]
    return data


@app.get("/api/projects/{project_id}/artifacts")
async def artifacts(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    return await db.execute(
        "SELECT a.id,a.name,a.size,a.sha256,a.media_type,a.run_id,a.created_at FROM artifacts a LEFT JOIN runs r ON r.id=a.run_id WHERE a.tenant_id=%s AND a.project_id=%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s) ORDER BY a.created_at DESC",
        (actor.tenant_id, project_id, actor.user_id),
    )


class ClaimInput(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=2000)
    source_id: str
    source_time: str


class ResolveInput(BaseModel):
    subject: str
    predicate: str


@app.post("/api/projects/{project_id}/claims")
async def add_claim(project_id: str, body: ClaimInput, actor=Depends(principal)):
    await project_access(project_id, actor)
    from .coordination import submit_claim

    try:
        return await submit_claim(actor, project_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post("/api/projects/{project_id}/claims/resolve")
async def resolve_claim(project_id: str, body: ResolveInput, actor=Depends(principal)):
    await project_access(project_id, actor)
    from .coordination import resolve_claims

    return await resolve_claims(actor, project_id, body.subject, body.predicate)


@app.get("/api/projects/{project_id}/coordination")
async def coordination_view(project_id: str, actor=Depends(principal)):
    await project_access(project_id, actor)
    records = await memory.list(actor, project_id)
    ids = {r["id"] for r in records}
    claims = await db.execute(
        "SELECT * FROM knowledge_claims WHERE tenant_id=%s AND project_id=%s ORDER BY source_time DESC",
        (actor.tenant_id, project_id),
    )
    resolutions = await db.execute(
        "SELECT * FROM claim_resolutions WHERE tenant_id=%s AND project_id=%s ORDER BY updated_at DESC",
        (actor.tenant_id, project_id),
    )
    events = await db.execute(
        """SELECT * FROM events WHERE tenant_id=%s
        AND kind IN ('memory.corrected','plan.revised') AND payload->>'project_id'=%s ORDER BY id DESC LIMIT 100""",
        (actor.tenant_id, project_id),
    )
    accessible = await db.execute(
        "SELECT id,role,objective,status,result FROM runs WHERE tenant_id=%s AND project_id=%s AND (visibility='team' OR user_id=%s)",
        (actor.tenant_id, project_id, actor.user_id),
    )
    task_ids = {r["id"] for r in accessible}
    events = [e for e in events if e["payload"].get("new") in ids and (not e["run_id"] or e["run_id"] in task_ids)]
    from .showcase import correction_witnesses

    witnesses = await correction_witnesses(
        actor.tenant_id, project_id, [e for e in events if e["kind"] == "memory.corrected"], task_ids
    )
    for event in events:
        event["payload"]["affected_runs"] = [r for r in event["payload"].get("affected_runs", []) if r in task_ids]
        event["payload"]["affected_tasks"] = [
            {k: task[k] for k in ("id", "role", "objective", "status")}
            for task in accessible
            if task["id"] in event["payload"]["affected_runs"]
        ]
        if event["kind"] == "memory.corrected":
            witness = witnesses[event["id"]]
            witness["revision_edges"] = [
                edge for edge in witness["revision_edges"] if edge["target"] in event["payload"]["affected_runs"]
            ]
            event["payload"]["graph_witness"] = witness
        if event["kind"] == "plan.revised":
            plan = next((task for task in accessible if task["id"] == event["payload"].get("new_plan_id")), None)
            if plan:
                event["payload"]["new_plan_status"] = plan["status"]
                event["payload"]["new_plan_result"] = plan["result"]
    versions = await db.execute(
        "SELECT * FROM procedure_versions WHERE tenant_id=%s AND project_id=%s ORDER BY family,version DESC",
        (actor.tenant_id, project_id),
    )
    versions = [v for v in versions if v["id"] in ids]
    uses = await db.execute(
        """SELECT u.* FROM procedure_uses u JOIN runs r ON r.id=u.run_id
        WHERE u.tenant_id=%s AND r.project_id=%s AND (r.visibility='team' OR r.user_id=%s) ORDER BY u.started_at DESC""",
        (actor.tenant_id, project_id, actor.user_id),
    )
    benchmarks = await db.execute(
        """SELECT id,created_at,payload FROM events WHERE tenant_id=%s
        AND kind='procedure.benchmark' AND payload->>'project_id'=%s ORDER BY id DESC LIMIT 10""",
        (actor.tenant_id, project_id),
    )
    benchmarks = [
        b
        for b in benchmarks
        if b["payload"].get("procedure_id") in ids and all(r in task_ids for r in b["payload"].get("run_ids", []))
    ]
    passports = await db.execute(
        """SELECT e.id,e.run_id,e.created_at,e.payload,r.role FROM events e JOIN runs r ON r.id=e.run_id
        WHERE e.tenant_id=%s AND r.project_id=%s AND e.kind='memory.context'
        AND (r.visibility='team' OR r.user_id=%s) ORDER BY e.id DESC LIMIT 60""",
        (actor.tenant_id, project_id, actor.user_id),
    )
    deliveries = await db.execute(
        """SELECT h.id,h.from_run,h.to_run,h.acknowledged_at,h.packet,r.role,r.status FROM handoffs h
        JOIN runs r ON r.id=h.to_run JOIN runs s ON s.id=h.from_run
        WHERE h.tenant_id=%s AND r.project_id=%s AND (r.visibility='team' OR r.user_id=%s)
        AND (s.visibility='team' OR s.user_id=%s) ORDER BY h.created_at DESC LIMIT 30""",
        (actor.tenant_id, project_id, actor.user_id, actor.user_id),
    )
    return {
        "claims": [c for c in claims if c["memory_id"] in ids],
        "resolutions": resolutions,
        "causes": events,
        "versions": versions,
        "uses": [u for u in uses if u["procedure_id"] in ids],
        "benchmarks": benchmarks,
        "passports": passports,
        "deliveries": deliveries,
    }


@app.post("/api/projects/{project_id}/corrections/{event_id}/replan")
async def replan_correction(project_id: str, event_id: int, replace_failed: bool = False, actor=Depends(principal)):
    await project_access(project_id, actor)
    from .coordination import replan

    return await replan(actor, project_id, event_id, replace_failed=replace_failed)


@app.get("/api/artifacts/{artifact_id}/download")
async def download(artifact_id: str, actor=Depends(principal)):
    row = await db.execute(
        "SELECT a.* FROM artifacts a LEFT JOIN runs r ON r.id=a.run_id WHERE a.id=%s AND a.tenant_id=%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s)",
        (artifact_id, actor.tenant_id, actor.user_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Artifact unavailable")
    from .artifact_store import read as read_artifact
    from urllib.parse import quote

    data = await read_artifact(row)
    return Response(data, media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row["name"], safe=""),
        "Cache-Control": "no-store",
    })


@app.post("/api/projects/{project_id}/documents")
async def upload(project_id: str, file: UploadFile = File(...), actor=Depends(principal)):
    actor.write()
    await project_access(project_id, actor)
    data = await file.read(10_000_001)
    if len(data) > 10_000_000:
        raise HTTPException(413, "Document exceeds 10 MB")
    name = file.filename or "document.txt"
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader

        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, "Upload a UTF-8 text/source file or PDF") from None
    if len(text) > 200000:
        raise HTTPException(413, "Extracted document exceeds 200,000 characters")
    artifact = await publish_artifact(
        actor, project_id, None, name, data, file.content_type or "application/octet-stream"
    )
    job = await db.enqueue(
        actor.tenant_id,
        "document.ingest",
        {"project_id": project_id, "user_id": actor.user_id, "artifact_id": artifact["id"], "text": text},
    )
    return {"artifact": artifact, "ingestion_job_id": job, "status": "pending"}


@app.get("/api/events")
async def events(response: Response, after: int = 0, actor=Depends(principal)):
    from .event_visibility import readable_events
    order = "ASC" if after else "DESC"
    rows = await db.execute(
        f"SELECT e.* FROM events e LEFT JOIN runs r ON r.id=e.run_id WHERE e.tenant_id=%s AND e.id>%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s) ORDER BY e.id {order} LIMIT 200",
        (actor.tenant_id, after, actor.user_id),
    )
    response.headers["X-Engram-Next-Event"] = str(max((r["id"] for r in rows), default=after))
    if not after:
        rows.reverse()
    return await readable_events(actor, rows)


@app.get("/api/events/stream")
async def event_stream(request: Request, after: int = 0, actor=Depends(principal)):
    from .event_visibility import readable_events
    async def stream():
        cursor = after
        while not await request.is_disconnected():
            rows = await db.execute(
                "SELECT e.* FROM events e LEFT JOIN runs r ON r.id=e.run_id WHERE e.tenant_id=%s AND e.id>%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s) ORDER BY e.id LIMIT 100",
                (actor.tenant_id, cursor, actor.user_id),
            )
            if rows:
                cursor = rows[-1]["id"]
            permitted = await readable_events(actor, rows)
            for row in permitted:
                yield f"id: {row['id']}\ndata: {json.dumps(jsonable_encoder(row))}\n\n"
            if not permitted:
                yield ": heartbeat\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/jobs")
async def jobs(actor=Depends(principal)):
    return await db.execute(
        "SELECT id,kind,status,attempts,error,created_at FROM outbox WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 100",
        (actor.tenant_id,),
    )


@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str, actor=Depends(principal)):
    actor.write()
    row = await db.execute(
        "UPDATE outbox SET attempts=0,error=NULL,status='pending' WHERE id=%s AND tenant_id=%s RETURNING id",
        (job_id, actor.tenant_id),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Job unavailable")
    return row


@app.get("/api/evaluations")
async def evaluations(actor=Depends(principal)):
    return await db.execute(
        "SELECT * FROM evaluations WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 50", (actor.tenant_id,)
    )


@app.post("/api/projects/{project_id}/evaluate")
async def run_evaluation(project_id: str, actor=Depends(principal)):
    actor.write()
    await project_access(project_id, actor)
    from .evaluate import evaluate

    return await evaluate(actor, project_id)


@app.get("/api/tool-servers")
async def tool_servers(actor=Depends(principal)):
    return await db.execute(
        "SELECT id,name,url,enabled,allowed_tools FROM tool_servers WHERE tenant_id=%s", (actor.tenant_id,)
    )


@app.post("/api/tool-servers")
async def connect_mcp(body: MCPInput, actor=Depends(principal)):
    if actor.role != "owner":
        raise HTTPException(403, "Only the workspace owner may authorize external tools")
    from .mcp_registry import validate_url
    from langchain_mcp_adapters.client import MultiServerMCPClient

    await validate_url(body.url)
    tools = await MultiServerMCPClient({"discovery": {"transport": "streamable_http", "url": body.url}}).get_tools()
    names = {t.name for t in tools}
    if set(body.allowed_tools) - names:
        raise HTTPException(422, "Requested tools are not advertised by this MCP server")
    server_id = uid()
    await db.execute(
        "INSERT INTO tool_servers(id,tenant_id,name,url,allowed_tools) VALUES (%s,%s,%s,%s,%s)",
        (server_id, actor.tenant_id, body.name, body.url, body.allowed_tools),
    )
    return {
        "id": server_id,
        "available_tools": [{"name": t.name, "description": t.description} for t in tools],
        "allowed_tools": body.allowed_tools,
    }


@app.post("/api/tool-servers/{server_id}/disable")
async def disable_mcp(server_id: str, actor=Depends(principal)):
    if actor.role != "owner":
        raise HTTPException(403, "Owner permission required")
    await db.execute("UPDATE tool_servers SET enabled=false WHERE id=%s AND tenant_id=%s", (server_id, actor.tenant_id))
    return {"disabled": True}


frontend = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend.exists():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    # Only build-owned public directories are exposed. Runtime reports,
    # sessions and credentials live outside this tree and remain private.
    for public_path in ("examples", "evidence/live"):
        directory = frontend / public_path
        if directory.is_dir():
            app.mount("/" + public_path, StaticFiles(directory=directory, html=True), name=public_path.replace("/", "-"))


@app.get("/{path:path}")
async def index(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API route not found")
    if not (frontend / "index.html").exists():
        return JSONResponse({"detail": "Build the frontend with npm run build in frontend/"}, status_code=503)
    return FileResponse(frontend / "index.html")
