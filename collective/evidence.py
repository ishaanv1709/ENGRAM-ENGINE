"""Execution provenance and the supported Python test-evidence contract."""

import re
import shlex
from pathlib import PurePosixPath

from .db import db


def is_test_command(command):
    if not isinstance(command, str):
        return False
    # This exact, harmless workspace prefix is a common agent spelling of the
    # same test invocation. No other shell chaining or error suppression counts.
    command = re.sub(r"^cd\s+/workspace\s+&&\s+", "", command.strip(), count=1)
    if any(c in command for c in ";|&><\n\r"):
        return False
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    return bool(
        args
        and (
            args[0] == "pytest"
            or (
                args[0] in {"python", "python3", "python3.11"}
                and len(args) >= 3
                and args[1] == "-m"
                and args[2] in {"pytest", "unittest"}
            )
        )
    )


def verified_check(payload):
    if payload.get("exit_code") != 0 or not is_test_command(payload.get("command", "")):
        return False
    output = payload.get("stdout", "") + "\n" + payload.get("stderr", "")
    return bool(
        re.search(r"\b[1-9]\d* passed\b", output)
        or (re.search(r"\bRan [1-9]\d* tests?\b", output) and re.search(r"^OK(?:\s|$)", output, re.MULTILINE))
    )


async def execution_progress(run_id):
    artifacts = await db.execute(
        "SELECT DISTINCT ON (name) id,name,sha256 FROM artifacts WHERE run_id=%s ORDER BY name,created_at DESC,id DESC",
        (run_id,),
    )
    executions = await db.execute(
        "SELECT id,payload FROM events WHERE run_id=%s AND kind='tool.executed' ORDER BY id DESC LIMIT 32", (run_id,)
    )
    checks = [e for e in executions if is_test_command(e["payload"].get("command", ""))]
    handoffs = await db.execute(
        "SELECT h.id,h.to_run,r.status FROM handoffs h JOIN runs r ON r.id=h.to_run WHERE h.from_run=%s", (run_id,)
    )
    file_events = await db.execute(
        "SELECT id,payload FROM events WHERE run_id=%s AND kind='sandbox.file_written' ORDER BY id DESC LIMIT 24",
        (run_id,),
    )
    files = {}
    for event in file_events:
        files.setdefault(event["payload"]["path"], event)
    publication = await db.execute(
        "SELECT max(id) AS id FROM events WHERE run_id=%s AND kind IN ('artifact.published','task.handoff')",
        (run_id,),
        one=True,
    )
    last_progress = max([publication["id"] or 0, *[c["id"] for c in checks]])
    repeated = bool(
        file_events
        and any(e["payload"] == file_events[0]["payload"] for e in file_events[1:])
        and file_events[0]["id"] > last_progress
    )
    return {
        "published_artifacts": artifacts,
        "written_files": [{"event_id": f["id"], **f["payload"]} for f in files.values()],
        "repeated_write_without_progress": repeated,
        "recent_checks": [
            {
                "id": c["id"],
                "command": c["payload"].get("command"),
                "exit_code": c["payload"].get("exit_code"),
                "verified_passed": verified_check(c["payload"]),
                "stdout": c["payload"].get("stdout", "")[:350],
            }
            for c in checks[:2]
        ],
        "handoffs": handoffs,
    }


def fresh_check_ids(progress):
    latest_write = max((f["event_id"] for f in progress["written_files"]), default=0)
    if not progress["recent_checks"] or not progress["recent_checks"][0]["verified_passed"]:
        return []
    return [c["id"] for c in progress["recent_checks"] if c["verified_passed"] and c["id"] > latest_write]


def builder_completion_problem(progress):
    files = progress["written_files"]
    if not files:
        return None
    latest_write = max(f["event_id"] for f in files)
    if (
        not progress["recent_checks"]
        or not progress["recent_checks"][0]["verified_passed"]
        or progress["recent_checks"][0]["id"] <= latest_write
    ):
        return "Execute real passing pytest or unittest checks after the latest file writes."
    unpublished = [
        f["path"]
        for f in files
        if not any(
            a["name"] == str(PurePosixPath(f["path"]).relative_to("/workspace")) and a["sha256"] == f["sha256"]
            for a in progress["published_artifacts"]
        )
    ]
    if unpublished:
        return "Publish the current checked versions of these files: " + ", ".join(unpublished)
    return None
