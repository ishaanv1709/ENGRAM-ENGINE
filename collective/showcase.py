"""Read-only graph witnesses for the correction demo, not generated explanations."""

from .graph import graph


async def correction_witnesses(tenant, project, corrections, task_ids):
    memory_ids = list({e["payload"][k] for e in corrections for k in ("old", "new")})
    if not memory_ids:
        return {}
    dependency_query = """MATCH (t:Task)-[:DEPENDS_ON]->(m:Memory)
        WHERE t.id IN $tasks AND m.id IN $memories AND m.project_id=$project
        RETURN t.id,m.id"""
    parameters = {"tasks": sorted(task_ids), "memories": memory_ids, "project": project}
    dependencies = await graph.query(tenant, dependency_query, parameters)
    supersessions = await graph.query(tenant,
        """MATCH (n:Memory)-[:SUPERSEDES]->(o:Memory)
        WHERE n.id IN $memories AND o.id IN $memories AND n.project_id=$project AND o.project_id=$project
        RETURN n.id,o.id""", {"memories": memory_ids, "project": project})
    replans = await graph.query(tenant,
        """MATCH (n:Task)-[:REPLANS]->(o:Task)
        WHERE n.id IN $tasks AND o.id IN $tasks RETURN n.id,o.id""", {"tasks": list(task_ids)})
    return {e["id"]: {
        "source": "live FalkorDB traversal",
        "query": dependency_query,
        "parameters": parameters,
        "selected_previous_fact": e["payload"]["old"],
        "direct_readers": sorted({t for t, m in dependencies if m == e["payload"]["old"]}),
        "supersession_present": [e["payload"]["new"], e["payload"]["old"]] in [list(p) for p in supersessions],
        "new_fact_readers": sorted({t for t, m in dependencies if m == e["payload"]["new"]}),
        "revision_edges": [{"source": n, "type": "REPLANS", "target": o} for n, o in replans
            if o in e["payload"].get("affected_runs", [])],
        "effect": "Direct readers seed invalidation; SQL expands dependent tasks and parents, then revision fencing rejects late results.",
        "counterfactual": "Without a recorded DEPENDS_ON edge, this traversal cannot identify that direct reader. This is a read-only explanation, not an edge-deletion experiment.",
    } for e in corrections}
