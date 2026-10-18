"""Authenticated workflow and specialist configuration routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .auth import principal
from .db import db
from . import workflows as engine

router = APIRouter(prefix="/api")


async def project_access(actor, project):
    if not await db.execute(
        "SELECT id FROM projects WHERE id=%s AND tenant_id=%s", (project, actor.tenant_id), one=True
    ):
        raise HTTPException(404, "Project unavailable")


class ProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_role: str
    instructions: str = Field(min_length=1, max_length=6000)
    allowed_tools: list[str] = Field(max_length=50)
    context_scope: str = "team"


class StepInput(BaseModel):
    key: str = Field(min_length=1, max_length=48)
    parent_key: str | None = None
    title: str = Field(min_length=1, max_length=160)
    role: str
    objective: str = Field(min_length=1, max_length=8000)
    depends_on: list[str] = Field(default_factory=list, max_length=64)
    profile_id: str | None = None
    acceptance: str = "report"
    needs_approval: bool = False
    wait_for_signal: str | None = Field(default=None, max_length=100)


class WorkflowInput(BaseModel):
    goal: str = Field(min_length=3, max_length=12000)
    steps: list[StepInput] = Field(min_length=1, max_length=64)
    limits: dict[str, int] = Field(default_factory=dict)
    context_scope: str = "team"
    duration_minutes: int = Field(default=1440, ge=1, le=10080)
    snapshot_id: str | None = None


class ActionInput(BaseModel):
    payload: dict = Field(default_factory=dict)
    limits: dict[str, int] = Field(default_factory=dict)


@router.get("/projects/{project}/agent-profiles")
async def profiles(project: str, actor=Depends(principal)):
    await project_access(actor, project)
    return {
        "profiles": await db.execute(
            "SELECT * FROM agent_profiles WHERE tenant_id=%s AND project_id=%s AND user_id=%s ORDER BY created_at DESC",
            (actor.tenant_id, project, actor.user_id),
        ),
        "tools": sorted(engine.TOOLS),
        "roles": sorted(engine.ROLES),
    }


@router.post("/projects/{project}/agent-profiles")
async def add_profile(project: str, body: ProfileInput, actor=Depends(principal)):
    await project_access(actor, project)
    return await engine.profile_create(
        actor, project, body.name, body.base_role, body.instructions, body.allowed_tools, body.context_scope
    )


@router.get("/projects/{project}/source-snapshots")
async def snapshots(project: str, actor=Depends(principal)):
    await project_access(actor, project)
    return await db.execute(
        "SELECT * FROM repository_snapshots WHERE tenant_id=%s AND project_id=%s ORDER BY created_at DESC LIMIT 50",
        (actor.tenant_id, project),
    )


@router.post("/projects/{project}/source-snapshots")
async def add_snapshot(project: str, file: UploadFile = File(...), actor=Depends(principal)):
    await project_access(actor, project)
    from .repositories import import_zip

    data = await file.read(8_000_001)
    return await import_zip(actor, project, (file.filename or "source.zip")[:160], data)


@router.get("/projects/{project}/workflows")
async def workflows(project: str, actor=Depends(principal)):
    await project_access(actor, project)
    return await db.execute(
        "SELECT * FROM workflows WHERE tenant_id=%s AND project_id=%s AND user_id=%s ORDER BY created_at DESC LIMIT 100",
        (actor.tenant_id, project, actor.user_id),
    )


@router.post("/projects/{project}/workflows")
async def add_workflow(project: str, body: WorkflowInput, actor=Depends(principal)):
    await project_access(actor, project)
    return await engine.create_workflow(
        actor,
        project,
        body.goal,
        [s.model_dump() for s in body.steps],
        body.limits,
        body.context_scope,
        body.duration_minutes,
        body.snapshot_id,
    )


@router.get("/workflows/{workflow_id}")
async def workflow(workflow_id: str, actor=Depends(principal)):
    wf = await engine.access(actor, workflow_id)
    return {
        "workflow": wf,
        "steps": await db.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id=%s ORDER BY position,created_at,key", (workflow_id,)
        ),
        "runs": await db.execute("SELECT * FROM runs WHERE workflow_id=%s ORDER BY created_at", (workflow_id,)),
        "usage": await db.execute(
            "SELECT kind,count(*) AS attempts FROM workflow_reservations WHERE workflow_id=%s GROUP BY kind",
            (workflow_id,),
        ),
        "actions": await db.execute(
            "SELECT * FROM workflow_actions WHERE workflow_id=%s ORDER BY created_at", (workflow_id,)
        ),
    }


@router.post("/workflows/{workflow_id}/steps/{step_id}/{action}")
async def step_control(workflow_id: str, step_id: str, action: str, body: ActionInput, actor=Depends(principal)):
    import json

    if len(json.dumps(body.payload).encode()) > 16000:
        raise HTTPException(413, "Signal payload exceeds 16 KB")
    await engine.step_action(actor, workflow_id, step_id, action, body.payload)
    return {"recorded": True}


@router.post("/workflows/{workflow_id}/actions/{action_id}/{decision}")
async def external_action(workflow_id: str, action_id: str, decision: str, actor=Depends(principal)):
    from .workflow_actions import execute_action

    return await execute_action(actor, workflow_id, action_id, decision)


@router.post("/workflows/{workflow_id}/{action}")
async def workflow_control(workflow_id: str, action: str, body: ActionInput, actor=Depends(principal)):
    await engine.access(actor, workflow_id, True)
    if action in {"start", "resume"}:
        from .byok import require_personal_model
        require_personal_model()
    return await engine.control(actor, workflow_id, action, body.limits)
