"""Import immutable source ZIPs without checking out or executing host code."""

import hashlib
import io
from pathlib import PurePosixPath
import stat
import zipfile

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .db import db, uid
from .sandbox import publish_artifact
from .artifact_store import read as read_artifact


async def snapshot_access(actor, project, snapshot_id):
    row = await db.execute(
        "SELECT * FROM repository_snapshots WHERE id=%s AND tenant_id=%s AND project_id=%s",
        (snapshot_id, actor.tenant_id, project),
        one=True,
    )
    if not row:
        raise HTTPException(404, "Source snapshot unavailable")
    return row


async def import_zip(actor, project, name, data):
    actor.write()
    if len(data) > 8_000_000:
        raise HTTPException(413, "Source ZIP exceeds 8 MB")
    entries, skipped, total = [], [], 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = [f for f in archive.infolist() if not f.is_dir()]
            if not files or len(files) > 500:
                raise HTTPException(422, "Source ZIP requires 1–500 entries")
            prefix = files[0].filename.split("/")[0] + "/"
            strip = all(f.filename.startswith(prefix) for f in files)
            seen = set()
            for item in files:
                raw = item.filename
                path = PurePosixPath(raw)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in raw
                    or "\x00" in raw
                    or any(ord(char) < 32 or ord(char) == 127 for char in raw)
                    or ":" in raw
                    or stat.S_ISLNK(item.external_attr >> 16)
                ):
                    raise HTTPException(422, "Archive contains unsafe paths or links")
                raw = raw[len(prefix) :] if strip else raw
                path = PurePosixPath(raw)
                raw = str(path)
                if not path.parts or raw in seen:
                    raise HTTPException(422, "Archive contains empty or duplicate paths")
                seen.add(raw)
                if any(p in {".git", "node_modules", ".venv", "__pycache__", "dist"} for p in path.parts) or any(
                    p == ".env" or (p.startswith(".env.") and p not in {".env.example", ".env.sample"})
                    for p in path.parts
                ):
                    skipped.append({"path": raw, "reason": "excluded environment or generated directory"})
                    continue
                total += item.file_size
                if item.file_size > 1_000_000 or total > 20_000_000 or len(entries) >= 200:
                    raise HTTPException(413, "Source limit: 200 text files, 1 MB per file, 20 MB expanded")
                content = archive.read(item)
                try:
                    content.decode("utf-8")
                except UnicodeDecodeError:
                    skipped.append({"path": raw, "reason": "binary or non-UTF8 content"})
                    continue
                if b"\x00" in content:
                    skipped.append({"path": raw, "reason": "binary content"})
                    continue
                entries.append((raw, content))
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise HTTPException(422, "Invalid or unsupported source ZIP") from exc
    if not entries:
        raise HTTPException(422, "No supported source files in archive")
    manifest = []
    for path, content in entries:
        artifact = await publish_artifact(actor, project, None, path, content, "text/plain")
        manifest.append(
            {"path": path, "artifact_id": artifact["id"], "sha256": artifact["sha256"], "size": len(content)}
        )
    snapshot = await db.execute(
        """INSERT INTO repository_snapshots(id,tenant_id,project_id,user_id,name,digest,manifest,skipped)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (
            uid(),
            actor.tenant_id,
            project,
            actor.user_id,
            name,
            hashlib.sha256(data).hexdigest(),
            Jsonb(manifest),
            Jsonb(skipped),
        ),
        one=True,
    )
    await db.event(
        actor.tenant_id,
        "repository.imported",
        {"project_id": project, "snapshot_id": snapshot["id"], "files": len(manifest), "skipped": len(skipped)},
    )
    return snapshot


async def read_file(actor, project, snapshot_id, path):
    snapshot = await snapshot_access(actor, project, snapshot_id)
    entry = next((e for e in snapshot["manifest"] if e["path"] == path), None)
    if not entry:
        raise HTTPException(404, "Source file unavailable")
    row = await db.execute(
        "SELECT path,sha256 FROM artifacts WHERE id=%s AND tenant_id=%s AND project_id=%s",
        (entry["artifact_id"], actor.tenant_id, project),
        one=True,
    )
    data = await read_artifact(row)
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise HTTPException(409, "Source bytes changed from the snapshot")
    if len(data) > 200_000:
        raise HTTPException(413, "File exceeds the 200 KB source-reading response limit")
    return {"path": path, "content": data.decode("utf-8"), "sha256": entry["sha256"]}


async def make_patch(actor, project, snapshot_id, artifact_ids, run_id):
    import difflib

    snapshot = await snapshot_access(actor, project, snapshot_id)
    if not 1 <= len(set(artifact_ids)) <= 100:
        raise HTTPException(422, "Choose 1–100 changed artifacts")
    artifacts = await db.execute(
        """SELECT a.* FROM artifacts a JOIN runs r ON r.id=a.run_id
        WHERE a.id=ANY(%s) AND a.tenant_id=%s AND a.project_id=%s AND (r.visibility='team' OR r.user_id=%s)""",
        (artifact_ids, actor.tenant_id, project, actor.user_id),
    )
    if len(artifacts) != len(set(artifact_ids)) or len({a["name"] for a in artifacts}) != len(artifacts):
        raise HTTPException(422, "Choose accessible, unambiguous file versions")
    sections = []
    for artifact in sorted(artifacts, key=lambda a: a["name"]):
        data = await read_artifact(artifact)
        if len(data) > 200_000 or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise HTTPException(409, "Changed artifact exceeds the diff limit or has changed bytes")
        old_entry = next((e for e in snapshot["manifest"] if e["path"] == artifact["name"]), None)
        before = (await read_file(actor, project, snapshot_id, artifact["name"]))["content"] if old_entry else ""
        after = data.decode("utf-8")
        sections.append(
            "".join(
                line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                for line in difflib.unified_diff(
                    before.splitlines(keepends=True),
                    after.splitlines(keepends=True),
                    fromfile="a/" + artifact["name"] if old_entry else "/dev/null",
                    tofile="b/" + artifact["name"],
                )
            )
        )
    patch = "".join(sections).encode()
    if not patch or len(patch) > 1_000_000:
        raise HTTPException(422, "No textual changes, or patch exceeds 1 MB")
    published = await publish_artifact(actor, project, run_id, "changes.patch", patch, "text/x-diff")
    await db.event(
        actor.tenant_id,
        "repository.patch_created",
        {"snapshot_id": snapshot_id, "source_artifacts": artifact_ids, "patch_artifact_id": published["id"]},
        run_id,
    )
    return published
