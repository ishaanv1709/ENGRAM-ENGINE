"""Owner-approved remote MCP capabilities, retrieved through ENGRAM memory."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool

from .db import db


async def validate_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise HTTPException(422, "MCP URL must use public HTTPS on port 443 without embedded credentials")
    addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, 443, type=socket.SOCK_STREAM)
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise HTTPException(422, "Private, loopback and link-local MCP endpoints are not allowed")


async def load_tools(actor, toolkit):
    servers = await db.execute("SELECT * FROM tool_servers WHERE tenant_id=%s AND enabled=true", (actor.tenant_id,))
    result = []
    for server in servers:
        await validate_url(server["url"])
        client = MultiServerMCPClient({server["id"]: {"transport": "streamable_http", "url": server["url"]}})
        remote_tools = await client.get_tools()
        allowed = set(server.get("allowed_tools") or [])
        for remote in remote_tools:
            if remote.name not in allowed:
                continue

            tool_name = "mcp_" + server["id"].replace("-", "")[:8] + "_" + remote.name

            async def invoke(_remote=remote, _server=server, _name=tool_name, **kwargs):
                await toolkit.guard()
                if toolkit.run.get("workflow_id"):
                    from .workflow_actions import request_action
                    return await request_action(actor, toolkit.run, _name, _server, _remote.name, kwargs)
                return await _remote.ainvoke(kwargs)

            result.append(
                StructuredTool.from_function(
                    coroutine=invoke,
                    name=tool_name,
                    description=remote.description or remote.name,
                    args_schema=remote.args_schema,
                )
            )
    return result
