import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.db import db


async def main():
    await db.open()
    fixture = json.loads(Path("data/collective/live-verification.json").read_text())["fixture"]
    if "--brief" in sys.argv:
        for query in ["SELECT role,status,count(*) FROM runs WHERE tenant_id=%s GROUP BY role,status ORDER BY role,status",
            "SELECT kind,count(*) FROM events WHERE tenant_id=%s AND kind IN ('memory.write_back','memory.corrected','procedure.version_verified','procedure.reused') GROUP BY kind",
            "SELECT family,version,status FROM procedure_versions WHERE tenant_id=%s",
            "SELECT run_id,kind,payload FROM events WHERE tenant_id=%s AND kind='agent.tool_rejected' ORDER BY id DESC LIMIT 5"]:
            print(json.dumps(await db.execute(query, (fixture["tenant"],)), default=str))
        await db.pool.close()
        return
    if "--checks" in sys.argv:
        from collective.evidence import verified_check

        rows = await db.execute(
            "SELECT e.id,e.run_id,e.payload FROM events e JOIN runs r ON r.id=e.run_id WHERE e.tenant_id=%s AND r.role='verifier' AND e.kind='tool.executed' ORDER BY e.id",
            (fixture["tenant"],),
        )
        print(
            json.dumps(
                {
                    "independent_execution_events": len(rows),
                    "passing_test_events": [
                        {"id": r["id"], "run_id": r["run_id"], "command": r["payload"].get("command")}
                        for r in rows
                        if verified_check(r["payload"])
                    ],
                }
            )
        )
        await db.pool.close()
        return
    if "--checkpoint" in sys.argv:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        run = await db.execute(
            "SELECT id FROM runs WHERE tenant_id=%s AND role=%s AND status='running' ORDER BY created_at DESC LIMIT 1",
            (fixture["tenant"], "coordinator" if "--coordinator" in sys.argv else "verifier" if "--verifier" in sys.argv else "curator" if "--curator" in sys.argv else "researcher" if "--researcher" in sys.argv else "builder"),
            one=True,
        )
        if not run:
            print("No running task for the selected role")
            await db.pool.close()
            return
        checkpoint = await AsyncPostgresSaver(db.pool).aget_tuple(
            {"configurable": {"thread_id": f"{fixture['tenant']}:{run['id']}"}}
        )
        for message in checkpoint.checkpoint["channel_values"]["messages"][-4:]:
            print(
                json.dumps(
                    {
                        "type": message.type,
                        "calls": getattr(message, "tool_calls", []),
                        "content": str(message.content)[:500],
                        "usage": getattr(message, "usage_metadata", None),
                        "finish_reason": getattr(message, "response_metadata", {}).get("finish_reason"),
                        "raw_tool_argument_lengths": [len(call.get("function", {}).get("arguments", "")) for call in getattr(message, "additional_kwargs", {}).get("tool_calls", [])],
                    },
                    default=str,
                )
            )
        await db.pool.close()
        return
    artifacts = await db.execute("SELECT id,name,sha256 FROM artifacts WHERE tenant_id=%s", (fixture["tenant"],))
    Path("data/collective/live-ui-fixture.json").write_text(
        json.dumps({"fixture": fixture, "workflow": {"artifacts": artifacts}}, default=str)
    )
    rows = await db.execute(
        "SELECT r.role,e.kind,e.payload,e.created_at FROM events e JOIN runs r ON r.id=e.run_id WHERE e.tenant_id=%s ORDER BY e.id DESC LIMIT 6",
        (fixture["tenant"],),
    )
    for row in reversed(rows):
        print(json.dumps(row, default=str)[:2500])
    print(
        json.dumps(
            await db.execute(
                "SELECT id,role,status,attempt,updated_at FROM runs WHERE tenant_id=%s ORDER BY created_at",
                (fixture["tenant"],),
            ),
            default=str,
        )
    )
    print(
        json.dumps(
            await db.execute(
                "SELECT split_part(key,':',1) AS model,tokens,created_at FROM model_reservations WHERE created_at>now()-interval '2 minutes' ORDER BY created_at"
            ),
            default=str,
        )
    )
    await db.pool.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
