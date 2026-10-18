"""Generate a fresh server environment without importing laptop credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("--origin", required=True)
parser.add_argument("--root", type=Path, default=Path("/opt/engram"))
args = parser.parse_args()
origin = urlsplit(args.origin)
if origin.scheme != "https" or not origin.hostname or origin.port not in (None, 443) or origin.path not in ("", "/") or origin.query or origin.fragment or origin.username or origin.password:
    parser.error("Supply one HTTPS origin without a path, credentials, query or fragment")
if not re.fullmatch(r"[A-Za-z0-9.-]+", origin.hostname):
    parser.error("Use a DNS hostname")
root = args.root.resolve()
destination = root / ".env.collective"
if destination.exists():
    parser.error("Existing environment retained. Update it deliberately; never regenerate database passwords")
database, graph = secrets.token_hex(32), secrets.token_hex(32)
values = {
    "ENGRAM_DATABASE_PASSWORD": database,
    "DATABASE_URL": f"postgresql://engram:{database}@127.0.0.1:55432/engram",
    "FALKOR_HOST": "127.0.0.1", "FALKOR_PORT": "56379", "FALKOR_PASSWORD": graph,
    "FALKOR_USERNAME": "default", "FALKOR_TLS": "false",
    "QDRANT_URL": "http://127.0.0.1:56333", "EMBEDDING_URL": "http://127.0.0.1:8091/v1",
    "EMBEDDING_MODEL_PATH": str(root / "data/models/mxbai-embed-large-v1_fp32.gguf"),
    "ARTIFACT_ROOT": str(root / "data/collective/artifacts"),
    "SANDBOX_RUNTIME": "docker", "SANDBOX_IMAGE": "engram-sandbox:local",
    "AGENT_PROVIDER": "unconfigured", "AGENT_MODEL": "", "AGENT_API_KEY": "",
    "GROQ_API_KEY": "****", "ANTHROPIC_API_KEY": "****", "JEV_API_KEY": "****",
    "TAVILY_API_KEY": "****", "LANGSEARCH_API_KEY": "****",
    "DECISION_PROVIDER": "personal_model", "LANGSEARCH_DAILY_LIMIT": "1000",
    "COOKIE_SECURE": "true", "ORIGINS": json.dumps([args.origin.rstrip("/")]),
    "MAX_PARALLEL_AGENTS": "2", "MAX_RUN_SECONDS": "1800",
    "GROQ_MAX_OUTPUT_TOKENS": "1000", "MEMORY_MAX_OUTPUT_TOKENS": "2000",
    "MEMORY_BUDGET_TOKENS": "2000",
}
root.mkdir(parents=True, exist_ok=True)
fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
    for key, value in values.items():
        handle.write(f"{key}={value}\n")
print(json.dumps({"created": str(destination), "operator_credentials_copied": False}))
