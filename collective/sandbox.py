import asyncio
import hashlib
import io
import sys
import tarfile
import subprocess
import tempfile
from pathlib import PurePosixPath

from fastapi import HTTPException

from .db import db, uid
from .settings import settings


def safe_path(path: str) -> str:
    p = PurePosixPath(path)
    if p.is_absolute():
        try:
            p = p.relative_to("/workspace")
        except ValueError:
            raise HTTPException(403, "Sandbox paths must stay inside /workspace") from None
    if not p.parts or any(part in {"..", "."} for part in p.parts) or "\x00" in path or "\\" in path:
        raise HTTPException(403, "Invalid sandbox path")
    return "/workspace/" + str(p)


async def docker_command(*args, data=None, timeout=30, limit=10_500_000):
    prefix = (
        ["wsl.exe", "-d", settings.wsl_distribution, "--exec", "docker"]
        if sys.platform == "win32" and settings.sandbox_runtime == "wsl"
        else ["docker"]
    )

    def call():
        # File-backed output avoids unbounded RAM use and works with psycopg's
        # Windows Selector loop, which does not implement async subprocesses.
        scratch = settings.artifact_root.parent / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=scratch) as stdout, tempfile.TemporaryFile(dir=scratch) as stderr:
            process = subprocess.run(
                [*prefix, *args],
                input=data,
                stdout=stdout,
                stderr=stderr,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if stdout.tell() > limit or stderr.tell() > 1_000_000:
                raise RuntimeError("Sandbox output limit exceeded")
            stdout.seek(0)
            stderr.seek(0)
            return process.returncode, stdout.read(), stderr.read()

    return await asyncio.to_thread(call)


class Sandbox:
    def __init__(self, run_id):
        self.run_id = run_id
        self.name = "engram-sandbox-" + run_id
        self.started = False

    async def start(self):
        existing, out, _ = await docker_command(
            "inspect", "--format", '{{index .Config.Labels "engram.run"}}', self.name
        )
        if existing == 0:
            if out.decode().strip() != self.run_id:
                raise PermissionError("Container name belongs to another owner")
            await docker_command("rm", "--force", self.name)
        code, _, err = await docker_command(
            "run",
            "--detach",
            "--name",
            self.name,
            "--user",
            "65534:65534",
            "--read-only",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            "128",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=volume,source=engram-work-{self.run_id},target=/workspace",
            "--label",
            "engram.managed=true",
            "--label",
            f"engram.run={self.run_id}",
            settings.sandbox_image,
            "sleep",
            "infinity",
        )
        if code:
            raise RuntimeError("Sandbox start failed: " + err.decode(errors="replace")[:500])
        self.started = True
        return self

    async def close(self):
        if self.started:
            code, _, err = await docker_command("rm", "--force", self.name)
            self.started = False
            if code:
                raise RuntimeError("Sandbox cleanup failed: " + err.decode(errors="replace")[:300])

    async def execute(self, command: str, timeout: int = 60):
        if not self.started:
            await self.start()
        if not command.strip() or len(command) > 12000:
            raise HTTPException(422, "Command must contain 1–12000 characters")
        try:
            code, out, err = await docker_command(
                "exec", self.name, "sh", "-lc", command, timeout=min(max(timeout, 1), 120), limit=1_000_000
            )
        except BaseException:
            await self.close()
            raise
        return {"exit_code": code, "stdout": out.decode(errors="replace"), "stderr": err.decode(errors="replace")}

    async def write(self, path, content):
        path = safe_path(path)
        if len(content.encode()) > 2_000_000:
            raise HTTPException(413, "File exceeds 2 MB")
        if not self.started:
            await self.start()
        data = content.encode()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            relative = PurePosixPath(path).relative_to("/workspace")
            for directory in reversed(relative.parents):
                if str(directory) == ".":
                    continue
                parent = tarfile.TarInfo(str(directory))
                parent.type, parent.uid, parent.gid, parent.mode = tarfile.DIRTYPE, 65534, 65534, 0o700
                tar.addfile(parent)
            entry = tarfile.TarInfo(str(relative))
            entry.size, entry.uid, entry.gid, entry.mode = len(data), 65534, 65534, 0o600
            tar.addfile(entry, io.BytesIO(data))
        code, _, err = await docker_command("cp", "-", self.name + ":/workspace", data=buffer.getvalue())
        if code:
            raise RuntimeError("Sandbox write failed: " + err.decode(errors="replace")[:300])
        if path.endswith(".py"):
            # A same-size edit within one second can otherwise reuse CPython's
            # timestamp-based bytecode, including caches in a resumed volume.
            code, _, err = await docker_command(
                "exec",
                self.name,
                "python",
                "-B",
                "-c",
                "import pathlib,sys; p=pathlib.Path(sys.argv[1]); c=p.parent/'__pycache__'; "
                "[f.unlink() for f in c.iterdir() if f.name.startswith(p.stem+'.') and f.name.endswith('.pyc')] if c.is_dir() else None",
                path,
            )
            if code:
                raise RuntimeError("Sandbox bytecode invalidation failed: " + err.decode(errors="replace")[:300])
        return {"path": path, "bytes": len(data)}

    async def read(self, path):
        path = safe_path(path)
        if not self.started:
            await self.start()
        code, out, err = await docker_command("cp", self.name + ":" + path, "-")
        if code:
            raise RuntimeError("Sandbox read failed: " + err.decode(errors="replace")[:300])
        with tarfile.open(fileobj=io.BytesIO(out)) as tar:
            entries = tar.getmembers()
            if len(entries) != 1 or not entries[0].isfile():
                raise HTTPException(422, "Publish an individual regular file, not a directory or link")
            return tar.extractfile(entries[0]).read()


async def publish_artifact(actor, project, run_id, name, data, media_type="application/octet-stream"):
    from .artifact_store import store

    artifact_id = uid()
    digest = hashlib.sha256(data).hexdigest()
    path = await store(actor.tenant_id, artifact_id, data, digest)
    await db.execute(
        "INSERT INTO artifacts(id,tenant_id,project_id,run_id,name,sha256,size,path,media_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            artifact_id,
            actor.tenant_id,
            project,
            run_id,
            str(PurePosixPath(safe_path(name)).relative_to("/workspace")),
            digest,
            len(data),
            str(path),
            media_type,
        ),
    )
    await db.event(
        actor.tenant_id, "artifact.published", {"artifact_id": artifact_id, "name": name, "sha256": digest}, run_id
    )
    return {"id": artifact_id, "name": name, "sha256": digest, "size": len(data)}
