"""Shared PostgreSQL token reservations for Groq's per-model minute limits."""

import asyncio
import hashlib
import json
import math
import time
import os
from pathlib import Path
from uuid import uuid4
from functools import lru_cache

import psycopg
import tiktoken
from langchain_openai import ChatOpenAI
from openai import RateLimitError

from .settings import DependencyUnavailable, settings

os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(Path("data/collective/tokenizers").resolve()))


@lru_cache(maxsize=1)
def tokenizer():
    return tiktoken.get_encoding("o200k_base")


def estimate_tokens(payload):
    def encode(value):
        return value.model_json_schema() if hasattr(value, "model_json_schema") else str(value)

    prompt = {k: v for k, v in payload.items() if k not in {"max_tokens", "max_completion_tokens"}}
    return math.ceil(len(tokenizer().encode(json.dumps(prompt, default=encode))) * 1.15) + int(
        payload.get("max_completion_tokens") or payload.get("max_tokens") or 3000
    )


def try_reserve(key, amount, capacity, request_id=None):
    if amount > capacity:
        raise DependencyUnavailable(f"Model request exceeds its {capacity}-token minute budget; compact its context")
    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('engram_model_budget_schema',0))")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS model_reservations(id text PRIMARY KEY,key text NOT NULL,tokens integer NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp())"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS model_reservations_window ON model_reservations(key,created_at)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS model_waiters(id text PRIMARY KEY,key text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),last_seen timestamptz NOT NULL DEFAULT clock_timestamp())"
        )
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
        if request_id:
            conn.execute(
                "DELETE FROM model_waiters WHERE key=%s AND last_seen<clock_timestamp()-interval '30 seconds'", (key,)
            )
            conn.execute(
                "INSERT INTO model_waiters(id,key) VALUES (%s,%s) ON CONFLICT(id) DO UPDATE SET last_seen=clock_timestamp()",
                (request_id, key),
            )
            first = conn.execute(
                "SELECT id FROM model_waiters WHERE key=%s ORDER BY created_at,id LIMIT 1", (key,)
            ).fetchone()
            if first[0] != request_id:
                return None, 2
        used, oldest = conn.execute(
            "SELECT COALESCE(sum(tokens),0),min(created_at) FROM model_reservations WHERE key=%s AND created_at>clock_timestamp()-interval '60 seconds'",
            (key,),
        ).fetchone()
        if used + amount <= capacity:
            ticket = str(uuid4())
            conn.execute("INSERT INTO model_reservations(id,key,tokens) VALUES (%s,%s,%s)", (ticket, key, amount))
            if request_id:
                conn.execute("DELETE FROM model_waiters WHERE id=%s", (request_id,))
            return ticket, 0
        now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        return None, min(2, max(0.2, 60 - (now - oldest).total_seconds() + 0.2))


def observe_provider(ticket, payload):
    """Record provider receipts separately from agent-loop usage events.

    Includes policy and Mem0 calls through this adapter. Failed SDK requests
    have unknown billed tokens; no zero-cost assumption is made for them.
    """
    from .memory import agent_run

    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        run_id = agent_run.get()
        owner = conn.execute("SELECT tenant_id FROM runs WHERE id=%s", (run_id,)).fetchone() if run_id else None
        if not owner and settings.provider_identity != "host":
            owner = conn.execute(
                "SELECT tenant_id FROM provider_connections WHERE id=%s", (settings.provider_identity.split(":", 1)[0],)
            ).fetchone()
        if not owner:
            return
        row = conn.execute("SELECT key FROM model_reservations WHERE id=%s", (ticket,)).fetchone()
        payload = {
            **payload,
            "model": row[0].split(":", 1)[0],
            "adapter": "groq",
            "sdk_internal_retries_included_in_count": False,
        }
        from psycopg.types.json import Jsonb

        conn.execute(
            "INSERT INTO events(tenant_id,run_id,kind,payload) VALUES (%s,%s,'model.provider_receipt',%s)",
            (owner[0], run_id, Jsonb(payload)),
        )


def refund(ticket, result, elapsed_ms=None):
    usage = (result.llm_output or {}).get("token_usage", {}).get("total_tokens")
    if usage is not None:
        with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
            conn.execute("UPDATE model_reservations SET tokens=%s WHERE id=%s", (int(usage), ticket))
    observe_provider(
        ticket, {"status": "success", "usage": (result.llm_output or {}).get("token_usage"), "elapsed_ms": elapsed_ms}
    )


class BudgetedChatOpenAI(ChatOpenAI):
    def budget(self, messages, stop, kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        capacity = (
            settings.safeguard_tokens_per_minute
            if self.model_name == settings.safeguard_model
            else settings.groq_tokens_per_minute
        )
        key = self.model_name + ":" + hashlib.sha256(self.openai_api_key.get_secret_value().encode()).hexdigest()
        return key, estimate_tokens(payload), capacity

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        budget = self.budget(messages, stop, kwargs)
        request_id = str(uuid4())
        for attempt in range(2):
            while True:
                ticket, delay = try_reserve(*budget, request_id)
                if ticket:
                    break
                time.sleep(delay)
            try:
                started = time.perf_counter()
                result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                refund(ticket, result, (time.perf_counter() - started) * 1000)
                return result
            except RateLimitError as exc:
                observe_provider(ticket, {"status": "failed", "error_type": "RateLimitError", "usage": None})
                if "per day" in str(exc).lower():
                    raise DependencyUnavailable(
                        f"Groq daily quota reached for {self.model_name}; raise the account limit or wait for quota to replenish."
                    ) from None
                if attempt:
                    raise
                time.sleep(60)
            except Exception as exc:
                observe_provider(ticket, {"status": "failed", "error_type": type(exc).__name__, "usage": None,
                                          "error_code": getattr(exc, "code", None), "http_status": getattr(exc, "status_code", None)})
                raise

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        budget = self.budget(messages, stop, kwargs)
        request_id = str(uuid4())
        for attempt in range(2):
            while True:
                ticket, delay = await asyncio.to_thread(try_reserve, *budget, request_id)
                if ticket:
                    break
                await asyncio.sleep(delay)
            try:
                started = time.perf_counter()
                result = await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
                await asyncio.to_thread(refund, ticket, result, (time.perf_counter() - started) * 1000)
                return result
            except RateLimitError as exc:
                await asyncio.to_thread(
                    observe_provider, ticket, {"status": "failed", "error_type": "RateLimitError", "usage": None}
                )
                if "per day" in str(exc).lower():
                    raise DependencyUnavailable(
                        f"Groq daily quota reached for {self.model_name}; raise the account limit or wait for quota to replenish."
                    ) from None
                if attempt:
                    raise
                await asyncio.sleep(60)
            except Exception as exc:
                await asyncio.to_thread(
                    observe_provider, ticket, {"status": "failed", "error_type": type(exc).__name__, "usage": None,
                                              "error_code": getattr(exc, "code", None), "http_status": getattr(exc, "status_code", None)}
                )
                raise
