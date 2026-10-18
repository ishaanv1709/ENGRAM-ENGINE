"""Actual PostgreSQL history durability and concurrent namespace isolation."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires real PostgreSQL"),
]


async def test_postgres_mem0_history_concurrency_namespace_and_new_process():
    from collective.db import db, uid
    from collective.mem0_history import PostgresHistory

    await db.open()
    namespace, other_namespace, memory_id = uid(), uid(), uid()
    first, other = PostgresHistory(namespace), PostgresHistory(other_namespace)
    await asyncio.gather(*[
        asyncio.to_thread(first.add_history, memory_id, None, f"verified-{index}", "ADD",
            created_at=f"2026-10-18T12:00:{index:02d}+00:00")
        for index in range(16)
    ])
    await asyncio.to_thread(other.add_history, memory_id, None, "other-tenant", "ADD")
    history = await asyncio.to_thread(first.get_history, memory_id)
    assert len(history) == 16
    assert {row["new_memory"] for row in history} == {f"verified-{index}" for index in range(16)}
    assert [row["new_memory"] for row in await asyncio.to_thread(other.get_history, memory_id)] == ["other-tenant"]
    script = (
        "import json,sys; from collective.mem0_history import PostgresHistory; "
        "print(json.dumps(PostgresHistory(sys.argv[1]).get_history(sys.argv[2])))"
    )
    process = await asyncio.to_thread(subprocess.run,
        [sys.executable, "-c", script, namespace, memory_id],
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert len(json.loads(process.stdout)) == 16
    await asyncio.to_thread(first.reset)
    assert await asyncio.to_thread(first.get_history, memory_id) == []
    assert len(await asyncio.to_thread(other.get_history, memory_id)) == 1
    await asyncio.to_thread(other.reset)
