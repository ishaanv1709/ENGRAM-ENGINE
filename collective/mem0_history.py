"""Mem0's synchronous history contract backed by durable PostgreSQL."""
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .settings import settings


class PostgresHistory:
    def __init__(self, namespace):
        self.namespace = namespace

    def add_history(self, memory_id, old_memory, new_memory, event, *, created_at=None,
                    updated_at=None, is_deleted=0, actor_id=None, role=None):
        with psycopg.connect(settings.database_url) as connection:
            connection.execute(
                """INSERT INTO mem0_history(namespace,id,memory_id,old_memory,new_memory,event,
                created_at,updated_at,is_deleted,actor_id,role) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (self.namespace, str(uuid4()), memory_id, old_memory, new_memory, event,
                 created_at, updated_at, bool(is_deleted), actor_id, role),
            )

    def get_history(self, memory_id):
        with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
            return connection.execute(
                """SELECT id,memory_id,old_memory,new_memory,event,created_at,updated_at,is_deleted,actor_id,role
                FROM mem0_history WHERE namespace=%s AND memory_id=%s
                ORDER BY created_at ASC NULLS FIRST,updated_at ASC NULLS FIRST,inserted_at,id""",
                (self.namespace, memory_id),
            ).fetchall()

    def reset(self):
        with psycopg.connect(settings.database_url) as connection:
            connection.execute("DELETE FROM mem0_history WHERE namespace=%s", (self.namespace,))

    def close(self):
        # Each operation closes its own connection, so restarts require no
        # local database or shared filesystem lock.
        pass
