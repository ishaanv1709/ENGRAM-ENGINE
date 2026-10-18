"""An unchanged schema must open concurrently without blocking live writes."""
import asyncio
import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(os.getenv("ENGRAM_INTEGRATION") != "1", reason="Requires actual local PostgreSQL"),
]


async def test_concurrent_startup_skips_unchanged_ddl_while_user_row_is_written():
    from collective.auth import register
    from collective.db import Database, db, uid

    await db.open()
    user = await register(f"schema-{uid()}@example.test", "Schema-integration-123", "Schema", "Schema check")
    first, second = Database(), Database()
    try:
        async with db.pool.connection() as writer:
            async with writer.transaction():
                # This real RowExclusiveLock would block ALTER TABLE users.
                await writer.execute("UPDATE users SET name=name WHERE id=%s", (user,))
                await asyncio.wait_for(asyncio.gather(first.open(), second.open()), timeout=8)
                assert first.ready and second.ready
                state = await first.execute("SELECT digest FROM engram_schema_state WHERE id=1", one=True)
                assert len(state["digest"]) == 64
    finally:
        await first.pool.close()
        await second.pool.close()
