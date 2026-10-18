import asyncio
import hashlib
import json
from uuid import UUID

from falkordb import FalkorDB
from redis.exceptions import ResponseError

from .settings import settings


def graph_name(tenant: str):
    return "engram_" + UUID(tenant).hex


class Graph:
    def __init__(self):
        self._client = None
        self.initialized = set()
        self.lock = asyncio.Lock()

    @property
    def client(self):
        if self._client is None:
            self._client = FalkorDB(
                host=settings.falkor_host,
                port=settings.falkor_port,
                username=settings.falkor_username,
                password=settings.falkor_password,
                ssl=settings.falkor_tls,
                socket_timeout=15,
                socket_connect_timeout=5,
            )
        return self._client

    async def query(self, tenant, statement, params=None):
        g = await asyncio.to_thread(lambda: self.client.select_graph(graph_name(tenant)))
        result = await asyncio.to_thread(g.query, statement, params or {})
        return result.result_set

    async def ensure(self, tenant):
        async with self.lock:
            if tenant in self.initialized:
                return
            statements = [
                "CREATE INDEX FOR (m:Memory) ON (m.id)",
                "CREATE INDEX FOR (m:Memory) ON (m.project_id)",
                f"CREATE VECTOR INDEX FOR (m:Memory) ON (m.embedding) OPTIONS {{dimension:{settings.embedding_dimension}, similarityFunction:'cosine'}}",
            ]
            for statement in statements:
                try:
                    await self.query(tenant, statement)
                except ResponseError as exc:
                    # Another worker or an earlier process may own these indexes.
                    # Only the explicit duplicate-index response is idempotent.
                    if not any(text in str(exc).lower() for text in ("already indexed", "already exists")):
                        raise
            self.initialized.add(tenant)

    async def put(self, tenant, record, vector=None):
        await self.ensure(tenant)
        props = {k: v for k, v in record.items() if v is not None and isinstance(v, (str, int, float, bool))}
        props["data"] = json.dumps(record)
        await self.query(
            tenant,
            "MERGE (m:Memory {id:$id}) SET m += $props, m.commit_complete=false",
            {"id": record["id"], "props": props},
        )
        if vector:
            await self.query(
                tenant, "MATCH (m:Memory {id:$id}) SET m.embedding=vecf32($v)", {"id": record["id"], "v": vector}
            )
        for source in record.get("source_ids", []):
            await self.query(
                tenant,
                "MATCH (m:Memory {id:$id}), (s:Memory {id:$source}) MERGE (m)-[:SUPPORTED_BY]->(s)",
                {"id": record["id"], "source": source},
            )
        for entity in record.get("entities", []):
            eid = hashlib.sha256((record.get("project_id", "") + ":" + entity.casefold()).encode()).hexdigest()
            await self.query(
                tenant,
                "MATCH (m:Memory {id:$id}) MERGE (e:Entity {id:$eid}) SET e.name=$name MERGE (m)-[:MENTIONS]->(e)",
                {"id": record["id"], "eid": eid, "name": entity},
            )
        for triple in record.get("triples", []):
            if len(triple) != 3:
                continue
            subject, predicate, obj = map(str, triple)
            await self.query(
                tenant,
                """MATCH (m:Memory {id:$id})
              MERGE (s:Entity {id:$sid}) SET s.name=$s
              MERGE (o:Entity {id:$oid}) SET o.name=$o
              MERGE (r:Relation {id:$rid}) SET r.predicate=$p
              MERGE (s)-[:SUBJECT_OF]->(r) MERGE (r)-[:OBJECT]->(o)
              MERGE (r)-[:SUPPORTED_BY]->(m)""",
                {
                    "id": record["id"],
                    "sid": hashlib.sha256((record.get("project_id", "") + subject.casefold()).encode()).hexdigest(),
                    "oid": hashlib.sha256((record.get("project_id", "") + obj.casefold()).encode()).hexdigest(),
                    "rid": record["id"] + hashlib.sha256(str(triple).encode()).hexdigest()[:12],
                    "s": subject,
                    "o": obj,
                    "p": predicate,
                },
            )
        await self.query(tenant, "MATCH (m:Memory {id:$id}) SET m.commit_complete=true", {"id": record["id"]})
        await self.query(tenant, "MERGE (s:State {id:'memory'}) SET s.revision=coalesce(s.revision,0)+1")

    async def complete(self, tenant, record_id):
        rows = await self.query(tenant, "MATCH (m:Memory {id:$id}) RETURN m.commit_complete", {"id": record_id})
        return bool(rows and rows[0][0])

    async def revision(self, tenant):
        rows = await self.query(tenant, "MATCH (s:State {id:'memory'}) RETURN s.revision")
        return rows[0][0] if rows else 0

    async def get(self, tenant, record_id):
        rows = await self.query(tenant, "MATCH (m:Memory {id:$id}) RETURN m.data", {"id": record_id})
        return json.loads(rows[0][0]) if rows else None

    async def list(self, tenant, project, limit=200):
        rows = await self.query(
            tenant,
            "MATCH (m:Memory) WHERE m.project_id=$p RETURN m.data ORDER BY m.created_at DESC LIMIT $n",
            {"p": project, "n": limit},
        )
        return [json.loads(r[0]) for r in rows]

    async def candidates(self, tenant, project, vector, limit=60):
        await self.ensure(tenant)
        rows = await self.query(
            tenant,
            """CALL db.idx.vector.queryNodes('Memory','embedding',$n,vecf32($v))
          YIELD node, score WHERE node.project_id=$p AND node.status='active'
          RETURN node.data, score""",
            {"n": limit, "v": vector, "p": project},
        )
        return [(json.loads(r[0]), float(r[1])) for r in rows]

    async def neighbors(self, tenant, record_id):
        rows = await self.query(
            tenant,
            """MATCH (m:Memory {id:$id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(r:Memory)
          WHERE r.status='active' RETURN DISTINCT r.data LIMIT 20""",
            {"id": record_id},
        )
        return [json.loads(r[0]) for r in rows]

    async def task(self, tenant, run):
        await self.query(
            tenant,
            "MERGE (t:Task {id:$id}) SET t.objective=$o,t.status=$s,t.project_id=$p",
            {"id": run["id"], "o": run["objective"], "s": run["status"], "p": run["project_id"]},
        )
        for dep in run.get("depends_on", []):
            await self.query(
                tenant,
                "MATCH (t:Task {id:$id}) MERGE (d:Task {id:$dep}) MERGE (t)-[:DEPENDS_ON_TASK]->(d)",
                {"id": run["id"], "dep": dep},
            )

    async def depend(self, tenant, run_id, memory_ids):
        for mid in memory_ids:
            await self.query(
                tenant,
                "MATCH (t:Task {id:$r}),(m:Memory {id:$m}) MERGE (t)-[:DEPENDS_ON]->(m)",
                {"r": run_id, "m": mid},
            )

    async def supersede(self, tenant, old, new):
        await self.query(
            tenant,
            "MATCH (o:Memory {id:$old}),(n:Memory {id:$new}) MERGE (n)-[:SUPERSEDES]->(o)",
            {"old": old, "new": new},
        )
        rows = await self.query(
            tenant,
            """MATCH (m:Memory {id:$id})<-[:DEPENDS_ON]-(t:Task)
          RETURN DISTINCT t.id""",
            {"id": old},
        )
        return [r[0] for r in rows]

    async def view(self, tenant, project):
        nodes = await self.query(
            tenant, "MATCH (m:Memory) WHERE m.project_id=$p RETURN m.id,m.data LIMIT 150", {"p": project}
        )
        edges = await self.query(
            tenant,
            """MATCH (a:Memory)-[r]->(b:Memory)
          WHERE a.project_id=$p AND b.project_id=$p RETURN a.id,type(r),b.id LIMIT 500""",
            {"p": project},
        )
        return {
            "nodes": [{"id": r[0], **json.loads(r[1])} for r in nodes],
            "edges": [{"source": r[0], "type": r[1], "target": r[2]} for r in edges],
        }

    async def entity_view(self, tenant, memory_ids):
        rows = await self.query(
            tenant,
            """MATCH (m:Memory)-[:MENTIONS]->(e:Entity)
          WHERE m.id IN $ids RETURN DISTINCT m.id,e.id,e.name LIMIT 300""",
            {"ids": memory_ids},
        )
        return rows


graph = Graph()
