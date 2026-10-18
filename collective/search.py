"""Real web search with a persistent, atomic LangSearch request budget."""

import httpx
import hashlib

from .db import db
from .settings import DependencyUnavailable, require_key, settings


async def search_web(query: str) -> dict:
    async with httpx.AsyncClient(timeout=45) as client:
        if settings.web_search_provider == "langsearch":
            key = require_key("LANGSEARCH_API_KEY", settings.langsearch_api_key)
            # Reserve before I/O: failed requests count conservatively. All tenants
            # and worker processes sharing this credential share one UTC budget.
            reserved = await db.execute(
                "INSERT INTO provider_usage(provider,day,requests) VALUES (%s,CURRENT_DATE,1) "
                "ON CONFLICT(provider,day) DO UPDATE SET requests=provider_usage.requests+1 "
                "WHERE provider_usage.requests < %s RETURNING requests",
                ("langsearch:" + hashlib.sha256(key.encode()).hexdigest(), settings.langsearch_daily_limit),
                one=True,
            )
            if not reserved:
                raise DependencyUnavailable("LangSearch daily request budget exhausted")
            response = await client.post(
                "https://api.langsearch.com/v1/web-search",
                headers={"Authorization": f"Bearer {key}"},
                json={"query": query, "count": 5, "contents": {"text": {"maxCharacters": 1200}}},
            )
            response.raise_for_status()
            body = response.json()
            if body.get("code") != 200:
                raise DependencyUnavailable(f"LangSearch rejected the request ({body.get('code')})")
            entries = body.get("data", {}).get("webPages", {}).get("value", [])
            return {
                "provider": "langsearch",
                "query": query,
                "results": entries,
                "daily_requests_reserved": reserved["requests"],
            }
        if settings.web_search_provider == "tavily":
            key = require_key("TAVILY_API_KEY", settings.tavily_api_key)
            response = await client.post(
                "https://api.tavily.com/search", json={"api_key": key, "query": query, "max_results": 5}
            )
            response.raise_for_status()
            return response.json()
        raise DependencyUnavailable("Unsupported WEB_SEARCH_PROVIDER")
