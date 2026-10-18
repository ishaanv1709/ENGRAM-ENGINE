"""Real services, real source files and real Docker checks; no model substitutes."""

import asyncio
import io
import os
from pathlib import Path
import zipfile

from fastapi import HTTPException
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires real local services"),
]


async def fixture():
    from collective.auth import Principal, register
    from collective.db import db, uid

    await db.open()
    email = f"workflow-{uid()}@example.test"
    user = await register(email, "Workflow-check-password-123", "Workflow checks", "Workflow checks")
    tenant = (await db.execute("SELECT tenant_id FROM memberships WHERE user_id=%s", (user,), one=True))["tenant_id"]
    actor = Principal(user, tenant, "owner", "Workflow checks")
    project = uid()
    await db.execute(
        "INSERT INTO projects(id,tenant_id,name) VALUES (%s,%s,'Controlled workflow checks; no inference')",
        (project, tenant),
    )
    return actor, project, email


def step(key, role="researcher", dependencies=None, acceptance="report", **extra):
    return {
        "key": key,
        "title": key,
        "role": role,
        "objective": "Execute the explicit infrastructure scenario; no model inference",
        "depends_on": dependencies or [],
        "acceptance": acceptance,
        **extra,
    }


async def cleanup(actor):
    from collective.db import db

    await db.execute(
        "UPDATE workflows SET status='cancelled' WHERE tenant_id=%s AND status!='completed'", (actor.tenant_id,)
    )
    await db.execute(
        "UPDATE runs SET status='cancelled',revision=revision+1,lease_token=NULL,lease_until=NULL WHERE tenant_id=%s AND status IN ('queued','running','waiting')",
        (actor.tenant_id,),
    )


async def test_real_repository_workflow_gates_pause_nested_files_patch_and_independent_checks(tmp_path):
    from collective.db import db
    from collective.repositories import import_zip
    from collective.runtime import claim, alive, finish
    from collective.tools import RunTools
    from collective.agents import prepare_resources, validate_outcome, Outcome
    from collective.workflows import create_workflow, control, tick, step_action, profile_create, verify_bound_outputs

    actor, project, _ = await fixture()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("project/src/capacity.py", "def capacity(replicas, size):\n    return replicas + size\n")
        archive.writestr("project/README.txt", "Before without newline")
        archive.writestr(
            "project/test_capacity.py",
            'import pytest\nfrom src.capacity import capacity\n@pytest.mark.parametrize("r,s,want", [(3,25,75),(0,25,0)])\ndef test_capacity(r,s,want):\n    assert capacity(r,s)==want\n',
        )
        archive.writestr("project/.env", "EXCLUDED_TEST_VALUE=not-a-real-credential")
    source = await import_zip(actor, project, "controlled-source.zip", buffer.getvalue())
    assert len(source["manifest"]) == 3 and source["skipped"][0]["path"] == ".env"
    specialist = await profile_create(
        actor,
        project,
        "Source investigator",
        "researcher",
        "Read source and return evidence.",
        ["repository_list", "repository_read", "team_status"],
        "team",
    )
    wf = await create_workflow(
        actor,
        project,
        "Controlled source review and repair, no inference",
        [
            step("investigate", profile_id=specialist["id"]),
            step(
                "implement",
                "builder",
                ["investigate"],
                "artifacts",
                needs_approval=True,
                wait_for_signal="requirements_confirmed",
            ),
            step("verify", "verifier", ["implement"], "independent_checks"),
            step("review", "coordinator", ["verify"], needs_approval=True),
        ],
        {},
        snapshot_id=source["id"],
    )

    async def steps():
        return {s["key"]: s for s in await db.execute("SELECT * FROM workflow_steps WHERE workflow_id=%s", (wf["id"],))}

    async def toolkit(run):
        kit = RunTools(actor, run)
        core, optional = kit.build()
        packets = await db.execute("SELECT * FROM handoffs WHERE to_run=%s", (run["id"],))
        await prepare_resources(kit, core, packets)
        return kit, {t.name: t for t in core + optional}

    try:
        await control(actor, wf["id"], "start")
        await tick(wf["id"])
        await tick(wf["id"])
        assert (await db.execute("SELECT count(*) AS n FROM runs WHERE workflow_id=%s", (wf["id"],), one=True))[
            "n"
        ] == 1
        research = await claim("workflow-test", actor.tenant_id)
        assert research["agent_profile"]["instructions"] == "Read source and return evidence."
        kit, tools = await toolkit(research)
        try:
            assert "sandbox_execute" not in tools and "memory_write" not in tools
            files = await tools["repository_list"].ainvoke({"snapshot_id": source["id"]})
            actual = await tools["repository_read"].ainvoke({"snapshot_id": source["id"], "path": "src/capacity.py"})
            assert len(files["manifest"]) == 3 and "replicas + size" in actual["content"]
            await finish(
                research, "completed", {"summary": "Infrastructure driver inspected the actual bug; no inference"}
            )
        finally:
            await kit.close()
        await tick(wf["id"])
        current = await steps()
        assert current["implement"]["status"] == "awaiting_approval"
        assert await claim("workflow-test", actor.tenant_id) is None
        with pytest.raises(HTTPException):
            await step_action(actor, wf["id"], current["review"]["id"], "approve")
        await step_action(actor, wf["id"], current["implement"]["id"], "approve")
        await tick(wf["id"])
        assert (await steps())["implement"]["status"] == "waiting_signal"
        await step_action(
            actor, wf["id"], current["implement"]["id"], "signal", {"observation": "Controlled requirements inspected"}
        )
        await tick(wf["id"])
        old = await claim("workflow-test", actor.tenant_id)
        await control(actor, wf["id"], "pause")
        assert not await alive(old)
        assert await claim("workflow-test", actor.tenant_id) is None
        with pytest.raises(RuntimeError):
            await finish(old, "completed", {"summary": "Must be fenced"})
        await control(actor, wf["id"], "resume")
        builder = await claim("workflow-test", actor.tenant_id)
        assert builder["id"] == old["id"] and builder["revision"] > old["revision"]
        kit, tools = await toolkit(builder)
        try:
            await tools["sandbox_execute"].ainvoke({"command": "python -m compileall -q src"})
            failing = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert failing["exit_code"] != 0 and not failing["verification_passed"]
            await tools["sandbox_write"].ainvoke(
                {"path": "src/capacity.py", "content": "def capacity(replicas, size):\n    return replicas * size\n"}
            )
            await tools["sandbox_write"].ainvoke({"path": "README.txt", "content": "After without newline"})
            checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"] and "2 passed" in checked["stdout"], checked
            artifacts = [
                await tools["artifact_publish"].ainvoke({"path": p})
                for p in ["src/capacity.py", "test_capacity.py", "README.txt"]
            ]
            patch = await tools["repository_patch"].ainvoke(
                {"snapshot_id": source["id"], "artifact_ids": [a["id"] for a in artifacts]}
            )
            row = await db.execute("SELECT path FROM artifacts WHERE id=%s", (patch["id"],), one=True)
            text = Path(row["path"]).read_text()
            assert "--- a/src/capacity.py" in text and "+    return replicas * size" in text
            assert "\\ No newline at end of file" in text
            from collective.repositories import read_file
            import subprocess

            for entry in source["manifest"]:
                destination = tmp_path / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(
                    (await read_file(actor, project, source["id"], entry["path"]))["content"].encode()
                )
            applied = subprocess.run(
                ["git", "apply", "--check", str(Path(row["path"]).resolve())],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )
            assert applied.returncode == 0, applied.stderr
            await validate_outcome(
                actor,
                builder,
                Outcome(
                    summary="Infrastructure driver repaired and checked actual files; no inference",
                    artifact_ids=[a["id"] for a in artifacts] + [patch["id"]],
                    check_event_ids=[checked["check_event_id"]],
                ),
            )
            await finish(
                builder,
                "completed",
                {
                    "summary": "Infrastructure driver repaired and checked actual files; no inference",
                    "artifact_ids": [a["id"] for a in artifacts] + [patch["id"]],
                    "check_event_ids": [checked["check_event_id"]],
                },
            )
        finally:
            await kit.close()
        await tick(wf["id"])
        verifier = await claim("workflow-test", actor.tenant_id)
        assert verifier["role"] == "verifier" and verifier["id"] != builder["id"]
        kit, tools = await toolkit(verifier)
        try:
            checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            await tools["sandbox_execute"].ainvoke({"command": "printf '\\n# changed after test' >> src/capacity.py"})
            with pytest.raises(ValueError, match="bytes differ"):
                await verify_bound_outputs(actor, verifier, kit)
            await tools["artifact_read"].ainvoke({"artifact_id": artifacts[0]["id"], "destination": "src/capacity.py"})
            checked = await tools["sandbox_execute"].ainvoke({"command": "python -m pytest -q"})
            assert checked["verification_passed"]
            await verify_bound_outputs(actor, verifier, kit)
            await finish(
                verifier,
                "completed",
                {
                    "summary": "Separate container checked exact bound bytes; no inference",
                    "check_event_ids": [checked["check_event_id"]],
                },
            )
        finally:
            await kit.close()
        await tick(wf["id"])
        current = await steps()
        assert current["verify"]["status"] == "completed" and current["review"]["status"] == "awaiting_approval"
        await step_action(actor, wf["id"], current["review"]["id"], "approve")
        await tick(wf["id"])
        review = await claim("workflow-test", actor.tenant_id)
        await finish(
            review,
            "completed",
            {"summary": "Infrastructure review packet retains real patch and check receipts; no autonomous inference"},
        )
        await tick(wf["id"])
        assert (await db.execute("SELECT status FROM workflows WHERE id=%s", (wf["id"],), one=True))[
            "status"
        ] == "completed"
        assert not await db.execute(
            "SELECT id FROM events WHERE run_id IN (SELECT id FROM runs WHERE workflow_id=%s) AND kind='model.usage'",
            (wf["id"],),
        )
    finally:
        await cleanup(actor)


async def test_workflow_concurrency_budgets_depth_and_cycle_guards():
    from collective.db import db
    from collective.runtime import claim, create_run, alive, finish
    from collective.workflows import create_workflow, control, tick, reserve, validate_plan
    from collective.settings import DependencyUnavailable

    actor, project, _ = await fixture()
    try:
        with pytest.raises(HTTPException):
            validate_plan([step("a", dependencies=["b"]), step("b", dependencies=["a"])])
        wf = await create_workflow(
            actor,
            project,
            "Check actual allocation budgets",
            [step("a"), step("b")],
            {"parallel": 1, "tool_calls": 1, "model_calls": 1, "max_depth": 1, "max_tasks": 3},
        )
        await control(actor, wf["id"], "start")
        await tick(wf["id"])
        leases = await asyncio.gather(claim("one", actor.tenant_id), claim("two", actor.tenant_id))
        assert sum(r is not None for r in leases) == 1
        run = next(r for r in leases if r)
        await reserve(run, "tool")
        with pytest.raises(DependencyUnavailable):
            await reserve(run, "tool")
        await reserve(run, "model")
        with pytest.raises(DependencyUnavailable):
            await reserve(run, "model")
        child = await create_run(actor, project, "Nested planning", "coordinator", parent=run["id"])
        assert child["workflow_id"] == wf["id"] and child["depth"] == 1
        with pytest.raises(HTTPException):
            await create_run(actor, project, "Too deep", "researcher", parent=child["id"])
        with pytest.raises(HTTPException):
            await create_run(actor, project, "Too many", "researcher", parent=run["id"])
        await control(actor, wf["id"], "pause")
        await control(actor, wf["id"], "limits", {"tool_calls": 4})
        assert (
            await db.execute(
                "SELECT count(*) AS n FROM workflow_reservations WHERE workflow_id=%s AND kind='tool'",
                (wf["id"],),
                one=True,
            )
        )["n"] == 1
        await control(actor, wf["id"], "resume")
        lease = await claim("deadline", actor.tenant_id)
        await db.execute("UPDATE workflows SET deadline_at=now()-interval '1 second' WHERE id=%s", (wf["id"],))
        assert not await alive(lease)
        assert await claim("expired", actor.tenant_id) is None
        with pytest.raises(RuntimeError):
            await finish(lease, "completed", {"summary": "Expired completion must be rejected"})
        await tick(wf["id"])
        assert (await db.execute("SELECT status FROM workflows WHERE id=%s", (wf["id"],), one=True))[
            "status"
        ] == "blocked"
    finally:
        await cleanup(actor)


async def test_workflow_api_scope_archive_rejection_and_exact_action_pause():
    import httpx
    from collective.app import app
    from collective.db import db, uid
    from collective.runtime import claim
    from collective.repositories import import_zip
    from collective.workflows import create_workflow, control, tick
    from collective.workflow_actions import request_action, execute_action
    from collective.settings import DependencyUnavailable

    actor, project, email = await fixture()
    outsider, _, _ = await fixture()
    try:
        bad = io.BytesIO()
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("../escape.py", "print(1)")
        with pytest.raises(HTTPException):
            await import_zip(actor, project, "bad.zip", bad.getvalue())
        wf = await create_workflow(actor, project, "Pause on proposed external effects", [step("a")], {})
        await control(actor, wf["id"], "start")
        await tick(wf["id"])
        run = await claim("actions", actor.tenant_id)
        # This exercises the real proposal/approval ledger only. No remote tool
        # is installed or executed and no substitute remote result is supplied.
        server = {"id": uid(), "url": "https://example.com/mcp"}
        with pytest.raises(DependencyUnavailable):
            await request_action(
                actor, run, "mcp_test_open_pr", server, "open_pr", {"title": "Review me", "body": "Exact arguments"}
            )
        row = await db.execute("SELECT * FROM workflow_actions WHERE workflow_id=%s", (wf["id"],), one=True)
        assert row["arguments"]["title"] == "Review me" and row["status"] == "pending"
        assert (await db.execute("SELECT status FROM workflows WHERE id=%s", (wf["id"],), one=True))[
            "status"
        ] == "paused"
        with pytest.raises(HTTPException):
            await execute_action(outsider, wf["id"], row["id"], "reject")
        await execute_action(actor, wf["id"], row["id"], "reject")
        with pytest.raises(PermissionError):
            await request_action(
                actor, run, "mcp_test_open_pr", server, "open_pr", {"title": "Review me", "body": "Exact arguments"}
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver", headers={"X-Engram-Request": "1"}
        ) as client:
            assert (await client.get("/api/workflows/" + wf["id"])).status_code == 401
            assert (
                await client.post("/api/auth/login", json={"email": email, "password": "Workflow-check-password-123"})
            ).status_code == 200
            view = await client.get("/api/workflows/" + wf["id"])
            assert view.status_code == 200 and view.json()["actions"][0]["status"] == "rejected"
            assert (await client.get("/api/projects/" + project + "/agent-profiles")).status_code == 200
            assert (await client.get("/api/workflows/" + uid())).status_code == 404
            assert (
                await client.post("/api/workflows/" + wf["id"] + "/steps/" + uid() + "/approve", json={})
            ).status_code == 404
            assert (
                await client.post(
                    "/api/projects/" + project + "/workflows",
                    json={"goal": "Bad cycle", "steps": [step("a", dependencies=["a"])]},
                )
            ).status_code == 422
    finally:
        await cleanup(actor)
        await cleanup(outsider)
