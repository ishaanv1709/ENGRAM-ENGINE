import asyncio
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from psycopg.errors import DeadlockDetected

from .settings import DependencyUnavailable, settings


def uid() -> str:
    return str(uuid4())


class Database:
    def __init__(self):
        self.pool = AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=16,
            open=False,
            timeout=30,
            kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
        )
        self.lock = asyncio.Lock()
        self.ready = False

    async def open(self):
        async with self.lock:
            if self.ready:
                return
            await self.pool.open()
            await self.pool.wait(timeout=6)
            schema = Path(__file__).with_name("schema.sql").read_text()
            digest = hashlib.sha256(schema.encode()).hexdigest()
            for attempt in range(3):
                try:
                    async with self.pool.connection() as conn:
                        async with conn.transaction():
                            await conn.execute(
                                "SELECT pg_advisory_xact_lock(hashtextextended('engram_collective_schema',0))"
                            )
                            await conn.execute(
                                "CREATE TABLE IF NOT EXISTS engram_schema_state (id integer PRIMARY KEY CHECK(id=1),digest text NOT NULL,applied_at timestamptz NOT NULL DEFAULT now())"
                            )
                            state = await (
                                await conn.execute("SELECT digest FROM engram_schema_state WHERE id=1")
                            ).fetchone()
                            if not state or state["digest"] != digest:
                                await conn.execute(schema)
                                await conn.execute(
                                    "INSERT INTO engram_schema_state(id,digest) VALUES (1,%s) ON CONFLICT(id) DO UPDATE SET digest=EXCLUDED.digest,applied_at=now()",
                                    (digest,),
                                )
                    break
                except DeadlockDetected:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.25 * (attempt + 1))
            self.ready = True

    async def execute(self, sql, params=(), *, one=False):
        if not self.ready:
            raise DependencyUnavailable("PostgreSQL is unavailable. Start the local services and restart the API.")
        async with self.pool.connection() as conn:
            cur = await conn.execute(sql, params)
            if cur.description is None:
                return None
            return await cur.fetchone() if one else await cur.fetchall()

    async def event(self, tenant, kind, payload, run_id=None):
        return await self.execute(
            "INSERT INTO events(tenant_id,run_id,kind,payload) VALUES (%s,%s,%s,%s) RETURNING *",
            (tenant, run_id, kind, Jsonb(payload)),
            one=True,
        )

    @asynccontextmanager
    async def delivery_lock(self, identity):
        # Release pooled connections while waiting: a delivery creates its task
        # through another connection, so blocked waiters must not fill the pool.
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            async with self.pool.connection() as conn:
                async with conn.transaction():
                    acquired = await (await conn.execute(
                        "SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) AS acquired", (identity,)
                    )).fetchone()
                    if acquired["acquired"]:
                        yield conn
                        return
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Handoff delivery is busy; retry the same request")
            await asyncio.sleep(0.05)

    async def enqueue(self, tenant, kind, payload, event_id=None):
        record_id = event_id or uid()
        await self.execute(
            "INSERT INTO outbox(id,tenant_id,kind,payload) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (record_id, tenant, kind, Jsonb(payload)),
        )
        return record_id


db = Database()
