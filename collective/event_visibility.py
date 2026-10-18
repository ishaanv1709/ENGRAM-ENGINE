"""Apply memory visibility to audit events, including older untagged events."""
from uuid import UUID

from .graph import graph
from .memory import visible


async def readable_events(actor, rows):
    cache, allowed = {}, []
    for event in rows:
        payload = event["payload"]
        if not isinstance(payload, dict):
            continue
        refs = [payload.get(k) for k in ("memory_id", "old", "new", "procedure_id", "source_id")]
        for key in ("fact_ids", "evidence_ids"):
            values = payload.get(key)
            if isinstance(values, list):
                refs.extend(values)
        packet = payload.get("packet", {})
        if isinstance(packet, dict):
            refs.extend(e.get("id") for e in packet.get("evidence", []) if isinstance(e, dict))
        permitted = True
        for identity in refs:
            if not isinstance(identity, str):
                continue
            try:
                UUID(identity)
            except ValueError:
                continue
            if identity not in cache:
                cache[identity] = await graph.get(actor.tenant_id, identity)
            record = cache[identity]
            if not record or not visible(record, actor, record["project_id"], event.get("run_id") or ""):
                permitted = False
                break
        if permitted:
            allowed.append(event)
    return allowed
