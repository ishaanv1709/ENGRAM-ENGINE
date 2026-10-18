import hashlib
from uuid import NAMESPACE_URL, uuid5
from typing import Literal

from fastapi import HTTPException
from langchain_core.tools import tool

from .db import db
from .evidence import execution_progress, builder_completion_problem, is_test_command, verified_check, fresh_check_ids
from .graph import graph
from .memory import memory
from .runtime import alive, create_run, handoff
from .sandbox import Sandbox, publish_artifact
from .settings import settings


class RunTools:
    def __init__(self, actor, run):
        self.actor, self.run = actor, run
        self.sandbox = None
        self.call_count = 0
        self.last_checks = []
        self.discovered = set()
        self.authorized_tools = set()
        self.resources_prepared = False
        self.expected_artifact_ids = set()
        self.procedure = None
        self.curation_source = None

    async def guard(self):
        self.actor.write()
        if not await alive(self.run):
            raise PermissionError("Task lease revoked or task changed")
        from .workflows import reserve

        await reserve(self.run, "tool")
        self.call_count += 1
        if self.call_count > settings.max_tool_calls:
            raise RuntimeError("Run tool-call budget exhausted")

    async def box(self):
        if self.run["role"] not in {"builder", "verifier"}:
            raise PermissionError("This role cannot execute code")
        if self.sandbox is None:
            self.sandbox = await Sandbox(self.run["id"]).start()
        return self.sandbox

    async def close(self):
        if self.sandbox:
            await self.sandbox.close()

    def build(self):
        actor, run = self.actor, self.run
        project, agent_id = run["project_id"], run["id"]

        @tool
        async def memory_search(query: str, memory_type: str = "") -> dict:
            """Retrieve scoped evidence, current facts and relevant procedures. Returns evidence IDs."""
            await self.guard()
            return await memory.context(actor, project, query, agent_id, run["id"], memory_type or None)

        @tool
        async def memory_read(memory_id: str) -> dict:
            """Read a specific scoped memory, including a proposed procedure awaiting verification."""
            await self.guard()
            record = await memory.get(actor, project, memory_id, agent_id)
            from .context_passports import consume, tokens
            # Explicit full reads remain available and are accounted separately
            # from the bounded startup/retrieval capsule budget.
            await consume(actor, project, run["id"], [record], [record], mode="explicit_full",
                          budget=max(settings.memory_budget_tokens, tokens([record])))
            await db.event(actor.tenant_id, "memory.read", {"memory_id": memory_id}, run["id"])
            return record

        @tool
        async def memory_write(observation: str, visibility: str = "team", source_ids: list[str] = []) -> dict:
            """Record a grounded observation through the decision model and Mem0. Never store secrets."""
            await self.guard()
            for source in source_ids:
                await memory.get(actor, project, source, agent_id)
            current = await db.execute("SELECT visibility FROM runs WHERE id=%s", (run["id"],), one=True)
            if current["visibility"] == "user" and visibility == "team":
                visibility = "user"
            receipt_key = hashlib.sha256(repr((observation, visibility, sorted(source_ids))).encode()).hexdigest()
            previous = await db.execute(
                "SELECT payload FROM events WHERE tenant_id=%s AND run_id=%s AND kind='memory.write_back' AND payload->>'receipt_key'=%s ORDER BY id DESC LIMIT 1",
                (actor.tenant_id, run["id"], receipt_key),
                one=True,
            )
            if previous and previous["payload"].get("result"):
                return previous["payload"]["result"]
            result = await memory.ingest(actor, project, observation, visibility, agent_id, source_ids)
            await db.event(
                actor.tenant_id,
                "memory.write_back",
                {
                    "status": result["status"],
                    "source_ids": source_ids,
                    "fact_ids": [r["id"] for r in result["facts"]],
                    "receipt_key": receipt_key,
                    "result": result,
                },
                run["id"],
            )
            return result

        @tool
        async def team_dispatch(
            role: Literal["coordinator", "researcher", "builder", "verifier", "curator"],
            objective: str,
            dependencies: list[str],
            context_scope: Literal["auto", "team"] | None = None,
            profile_id: str | None = None,
            memory_ids: list[str] | None = None,
            auto_curate: bool | None = None,
        ) -> dict:
            """Coordinator only: create durable specialist work. Independent work executes in parallel.
            context_scope='team' permits shared memories ONLY. Use 'auto' or omit it for this owner's private memories;
            the receiver stays private and cannot read another user's private memory. A rejected dispatch creates no task.
            """
            await self.guard()
            if run["role"] != "coordinator":
                raise PermissionError("Only coordinator can delegate new tasks")
            count = await db.execute("SELECT count(*) AS n FROM runs WHERE parent_id=%s", (run["id"],), one=True)
            if count["n"] >= 12:
                raise RuntimeError("Delegation budget exhausted")
            if role == "coordinator" and not run.get("workflow_id"):
                raise ValueError("Nested coordinators require a budgeted workflow")
            if role not in {"coordinator", "researcher", "builder", "verifier", "curator"}:
                raise ValueError("Choose a specialist role")
            from .workflows import load_profile

            profile = await load_profile(actor, project, profile_id) if profile_id else None
            result = await create_run(
                actor, project, objective, role, run["id"], dependencies, context_scope=context_scope, profile=profile,
                memory_ids=memory_ids,
                auto_curate=run.get("auto_curate", True) if auto_curate is None else auto_curate,
            )
            return {"task_id": result["id"], "status": result["status"]}

        @tool
        async def team_status() -> list[dict]:
            """Read actual task states and results for this team; do not assume delegated work is complete."""
            await self.guard()
            rows = await db.execute(
                "SELECT id,role,status,objective,result,error,visibility,context_scope,memory_refs FROM runs WHERE tenant_id=%s AND project_id=%s AND (parent_id=%s OR id=%s) AND (visibility='team' OR user_id=%s) ORDER BY created_at",
                (actor.tenant_id, project, run["parent_id"] or run["id"], run["id"], actor.user_id),
            )
            if any(r["visibility"] != "team" for r in rows):
                await db.execute("UPDATE runs SET visibility='user' WHERE id=%s", (run["id"],))
            return rows

        @tool
        async def team_handoff(
            role: Literal["researcher", "builder", "verifier", "curator"],
            checkpoint: str,
            remaining: str,
            evidence_ids: list[str] = [],
            artifact_ids: list[str] | None = None,
            check_event_ids: list[int] | None = None,
        ) -> dict:
            """Transfer work with real resources. evidence_ids are memory UUIDs only. Test event integers belong in check_event_ids. Omitted artifact_ids/check_event_ids are loaded from this agent's real ledger. remaining must describe the receiver's work."""
            await self.guard()
            progress = await execution_progress(run["id"])
            if artifact_ids is None:
                artifact_ids = [a["id"] for a in progress["published_artifacts"]]
            if check_event_ids is None:
                check_event_ids = [c["id"] for c in progress["recent_checks"] if c["verified_passed"]]
            result = await handoff(actor, run, role, checkpoint, evidence_ids, artifact_ids, remaining, check_event_ids)
            return {"receiving_task": result["id"]}

        @tool
        async def capability_search(query: str) -> dict:
            """Discover relevant registered tools and verified procedures, with schemas and permissions."""
            await self.guard()
            bundle = await memory.context(
                actor,
                project,
                query,
                agent_id,
                run["id"],
                "procedural",
                limit=6,
                allowed_tool_names=self.authorized_tools,
            )
            for record in bundle["memories"]:
                metadata = record.get("metadata", {})
                if metadata.get("tool_name"):
                    self.discovered.add(metadata["tool_name"])
                if metadata.get("kind") == "workflow" and record["status"] == "active":
                    self.discovered.update(metadata.get("tools", []))
            await db.event(actor.tenant_id, "capability.discovered", {"tools": sorted(self.discovered)}, run["id"])
            return bundle

        @tool
        async def web_search(query: str) -> dict:
            """Search the live web and return actual source URLs and excerpts."""
            await self.guard()
            from .search import search_web

            previous = await db.execute(
                "SELECT payload FROM events WHERE tenant_id=%s AND run_id=%s AND kind='web.search' AND payload->>'query'=%s ORDER BY id DESC LIMIT 1",
                (actor.tenant_id, run["id"], query),
                one=True,
            )
            if previous and previous["payload"].get("result"):
                await db.event(
                    actor.tenant_id,
                    "web.search_reused",
                    {"query": query, "reason": "same run and exact query; persisted provider response"},
                    run["id"],
                )
                return previous["payload"]["result"]
            result = await search_web(query)
            await db.event(
                actor.tenant_id,
                "web.search",
                {
                    "urls": [r["url"] for r in result.get("results", []) if r.get("url")],
                    "provider": settings.web_search_provider,
                    "query": query,
                    "result": result,
                },
                run["id"],
            )
            return result

        @tool
        async def sandbox_execute(command: str, timeout_seconds: int = 60) -> dict:
            """Execute in the isolated sandbox. Only real passing pytest/unittest runs qualify as check evidence."""
            await self.guard()
            if run["role"] == "builder":
                progress = await execution_progress(run["id"])
                problem = builder_completion_problem(progress)
                if problem and problem.startswith("Publish the current checked versions"):
                    raise ValueError(problem + "; this command did not execute")
                if progress["repeated_write_without_progress"] and not is_test_command(command):
                    raise ValueError(
                        "Repeated writes are paused. Run actual pytest or unittest now; this command did not execute."
                    )
            result = await (await self.box()).execute(command, timeout_seconds)
            event = await db.event(
                actor.tenant_id, "tool.executed", {"tool": "sandbox_execute", "command": command, **result}, run["id"]
            )
            result["execution_event_id"] = event["id"]
            result["verification_passed"] = verified_check({"command": command, **result})
            if not is_test_command(command):
                result["verification_requirement"] = (
                    "This command is not accepted as test evidence, even if its output contains passing tests. "
                    "Run python -m pytest -q or python -m unittest discover -v as a SEPARATE command, without shell chaining."
                )
            if is_test_command(command):
                result["check_event_id"] = event["id"]
                self.last_checks.append(event["id"])
            return result

        @tool
        async def sandbox_write(path: str, content: str) -> dict:
            """Write UTF-8 content to a path under /workspace in this agent's sandbox."""
            await self.guard()
            if run["role"] == "builder":
                progress = await execution_progress(run["id"])
                problem = builder_completion_problem(progress)
                if progress["repeated_write_without_progress"] or (
                    problem and problem.startswith("Publish the current checked versions")
                ):
                    raise ValueError(
                        "File writing is paused: execute actual tests or publish checked versions before editing again."
                    )
            result = await (await self.box()).write(path, content)
            await db.event(
                actor.tenant_id,
                "sandbox.file_written",
                {"path": result["path"], "sha256": hashlib.sha256(content.encode()).hexdigest()},
                run["id"],
            )
            return result

        @tool
        async def sandbox_read(path: str) -> str:
            """Read a regular UTF-8 file under /workspace inside this agent's sandbox."""
            await self.guard()
            return (await (await self.box()).read(path)).decode("utf-8")

        @tool
        async def artifact_publish(path: str) -> dict:
            """Publish a real sandbox file with checksum so other agents can use it."""
            await self.guard()
            data = await (await self.box()).read(path)
            return await publish_artifact(actor, project, run["id"], path, data)

        @tool
        async def artifact_read(artifact_id: str, destination: str = "") -> dict:
            """Read a published project artifact or copy it into this agent's sandbox for verification."""
            await self.guard()
            row = await db.execute(
                "SELECT a.*,r.visibility FROM artifacts a LEFT JOIN runs r ON r.id=a.run_id WHERE a.id=%s AND a.tenant_id=%s AND a.project_id=%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s)",
                (artifact_id, actor.tenant_id, project, actor.user_id),
                one=True,
            )
            if not row:
                raise HTTPException(404, "Artifact not found")
            if row.get("visibility") == "user":
                await db.execute("UPDATE runs SET visibility='user' WHERE id=%s", (run["id"],))
            from .artifact_store import read as read_artifact

            data = await read_artifact(row)
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise HTTPException(409, "Artifact contents no longer match the published checksum")
            if destination:
                result = await (await self.box()).write(destination, data.decode("utf-8"))
                await db.event(
                    actor.tenant_id,
                    "sandbox.file_written",
                    {"path": result["path"], "sha256": row["sha256"], "source_artifact_id": artifact_id},
                    run["id"],
                )
                await db.event(
                    actor.tenant_id,
                    "artifact.read",
                    {"artifact_id": artifact_id, "destination": result["path"]},
                    run["id"],
                )
                return result
            await db.event(actor.tenant_id, "artifact.read", {"artifact_id": artifact_id}, run["id"])
            return {"name": row["name"], "content": data.decode("utf-8"), "sha256": row["sha256"]}

        @tool
        async def memory_correct(memory_id: str, corrected_content: str, expected_revision: int) -> dict:
            """Correct a sourced fact and invalidate plans that depend on its old version."""
            await self.guard()
            if run["role"] != "curator":
                raise PermissionError("Only the curator may propose automatic corrections")
            return await memory.supersede(actor, project, memory_id, corrected_content, expected_revision)

        @tool
        async def procedure_propose(
            name: str,
            purpose: str,
            preconditions: list[str],
            steps: list[str],
            tool_names: list[str],
            check_event_ids: list[int],
        ) -> dict:
            """Propose a reusable procedure backed by actual passing pytest/unittest evidence."""
            await self.guard()
            if not check_event_ids:
                raise ValueError("Procedure promotion requires real successful checks")
            checks = await db.execute(
                "SELECT id,payload FROM events WHERE tenant_id=%s AND kind='tool.executed' AND id=ANY(%s)",
                (actor.tenant_id, check_event_ids),
            )
            if len(checks) != len(set(check_event_ids)) or any(not verified_check(c["payload"]) for c in checks):
                raise ValueError("Missing or failing execution evidence")
            descriptor = {
                "kind": "workflow",
                "name": name,
                "purpose": purpose,
                "preconditions": preconditions,
                "steps": steps,
                "tools": tool_names,
                "check_event_ids": check_event_ids,
                "successes": 1,
            }
            from .procedures import bind_version

            record = await bind_version(actor, run, descriptor)
            verifier = await create_run(
                actor,
                project,
                f"Independently execute the proposed procedure {record['id']}. Inspect its preconditions, "
                "source artifacts and check evidence. Only call procedure_verify after your own successful checks.",
                "verifier",
                parent=run["parent_id"] or run["id"],
            )
            return {"procedure_id": record["id"], "status": "proposed", "verification_task": verifier["id"]}

        @tool
        async def procedure_verify(procedure_id: str, check_event_ids: list[int]) -> dict:
            """Verifier only: promote a proposed procedure after independently executing its checks."""
            await self.guard()
            if run["role"] != "verifier" or not check_event_ids:
                raise PermissionError("An independent verifier with execution evidence is required")
            record = await memory.get(actor, project, procedure_id, agent_id)
            if record["status"] != "proposed" or record["metadata"].get("kind") != "workflow":
                raise ValueError("Procedure is not awaiting verification")
            checks = await db.execute(
                "SELECT id,payload FROM events WHERE tenant_id=%s AND run_id=%s AND kind='tool.executed' AND id=ANY(%s)",
                (actor.tenant_id, run["id"], check_event_ids),
            )
            if len(checks) != len(set(check_event_ids)) or any(not verified_check(c["payload"]) for c in checks):
                raise ValueError("Verifier checks are missing or failed")
            if not set(check_event_ids) <= set(fresh_check_ids(await execution_progress(run["id"]))):
                raise ValueError("Procedure checks must verify this agent's current prepared files")
            from .procedures import verify_version

            hashes = {
                a["name"]: hashlib.sha256(await (await self.box()).read(a["name"])).hexdigest()
                for a in record["metadata"].get("artifact_manifest", [])
            }
            await verify_version(actor, run, record, check_event_ids, hashes)
            record.update(status="active", revision=record["revision"] + 1)
            record["metadata"]["verified_by"] = run["id"]
            record["metadata"]["verification_checks"] = check_event_ids
            await graph.put(actor.tenant_id, record)
            return record

        @tool
        async def workspace_documents() -> list[dict]:
            """List real uploaded project documents and published artifacts."""
            await self.guard()
            return await db.execute(
                "SELECT a.id,a.name,a.sha256,a.size,a.run_id FROM artifacts a LEFT JOIN runs r ON r.id=a.run_id WHERE a.tenant_id=%s AND a.project_id=%s AND (r.id IS NULL OR r.visibility='team' OR r.user_id=%s) ORDER BY a.created_at DESC LIMIT 100",
                (actor.tenant_id, project, actor.user_id),
            )

        @tool
        async def claim_submit(subject: str, predicate: str, value: str, source_id: str, source_time: str) -> dict:
            """Preserve a competing claim with its source memory ID and exact recorded observation timestamp."""
            await self.guard()
            from .coordination import submit_claim

            row = await submit_claim(actor, project, subject, predicate, value, source_id, source_time, agent_id)
            return {**row, "source_time": row["source_time"].isoformat(), "created_at": row["created_at"].isoformat()}

        @tool
        async def claims_resolve(subject: str, predicate: str) -> dict:
            """Resolve competing claims using active sources and timestamps; preserve equal-time conflicts as unresolved."""
            await self.guard()
            from .coordination import resolve_claims

            row = await resolve_claims(actor, project, subject, predicate)
            return {**row, "updated_at": row["updated_at"].isoformat()}

        @tool
        async def repository_list(snapshot_id: str) -> dict:
            """List actual source files in an authorized immutable repository snapshot."""
            await self.guard()
            from .repositories import snapshot_access

            snapshot = await snapshot_access(actor, project, snapshot_id)
            return {"snapshot_id": snapshot_id, "manifest": snapshot["manifest"], "skipped": snapshot["skipped"]}

        @tool
        async def repository_read(snapshot_id: str, path: str) -> dict:
            """Read a UTF-8 source file and checksum from an authorized repository snapshot."""
            await self.guard()
            from .repositories import read_file

            return await read_file(actor, project, snapshot_id, path)

        @tool
        async def repository_patch(snapshot_id: str, artifact_ids: list[str]) -> dict:
            """Publish a real unified patch comparing selected published outputs to original snapshot files. Does not push or deploy."""
            await self.guard()
            if run["role"] not in {"builder", "verifier"}:
                raise PermissionError("Only implementation and verification roles can publish patches")
            from .repositories import make_patch

            return await make_patch(actor, project, snapshot_id, artifact_ids, run["id"])

        core = [
            memory_search,
            memory_read,
            memory_write,
            team_status,
            capability_search,
            workspace_documents,
            artifact_read,
            repository_list,
            repository_read,
        ]
        if run["role"] == "coordinator":
            core.append(team_dispatch)
        else:
            core.append(team_handoff)
        optional = [web_search, procedure_propose, claim_submit, claims_resolve]
        if run["role"] in {"builder", "verifier"}:
            optional.extend([sandbox_execute, sandbox_write, sandbox_read, artifact_publish, repository_patch])
        if run["role"] == "verifier":
            optional.append(procedure_verify)
        if run["role"] == "curator":
            optional.append(memory_correct)
        # Execution and publication are the builder's basic role contract.
        # Keep these few capabilities present; discover the larger optional
        # catalog semantically instead of relying on a small model to recover
        # a missing publication tool after it has already executed its tests.
        essential = {
            "builder": {"sandbox_write", "sandbox_execute", "artifact_publish"},
            "verifier": {"sandbox_execute"},
        }.get(run["role"], set())
        core.extend(t for t in optional if t.name in essential)
        optional = [t for t in optional if t.name not in essential]
        self.authorized_tools = {t.name for t in core + optional}
        if run.get("agent_profile"):
            allowed = set(run["agent_profile"]["allowed_tools"])
            core = [t for t in core if t.name in allowed]
            optional = [t for t in optional if t.name in allowed]
            self.authorized_tools &= allowed
        return core, optional

    async def register(self, tools):
        for capability in tools:
            record_id = str(uuid5(NAMESPACE_URL, self.actor.tenant_id + self.run["project_id"] + capability.name))
            if not await graph.get(self.actor.tenant_id, record_id):
                await memory.commit(
                    self.actor,
                    self.run["project_id"],
                    capability.name + ": " + capability.description,
                    category="critical",
                    memory_type="procedural",
                    record_id=record_id,
                    metadata={"kind": "tool", "tool_name": capability.name, "schema": capability.args},
                )
