"""Portable local API entrypoint (psycopg requires Selector on Windows)."""

import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    server = uvicorn.Server(uvicorn.Config("collective.app:app", host="127.0.0.1", port=8088))
    asyncio.run(server.serve())
