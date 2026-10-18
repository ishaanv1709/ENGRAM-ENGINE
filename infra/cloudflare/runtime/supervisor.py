"""Supervise real services; fail before startup on local or non-durable config."""

import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen


def required(name):
    value = os.environ.get(name, "").strip()
    if not value or "****" in value or value.startswith("your_") or value.startswith("your-"):
        raise ValueError(f"Configure cloud runtime secret {name}")
    return value


def remote_host(host, name):
    if not host or host.lower() in {"localhost", "host.docker.internal"}:
        raise ValueError(f"{name} must point to a durable remote service")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if address.is_loopback or address.is_unspecified or address.is_link_local:
        raise ValueError(f"{name} cannot use a local address")


def validate_environment():
    database = urlsplit(required("DATABASE_URL"))
    if database.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must be PostgreSQL")
    remote_host(database.hostname, "DATABASE_URL")
    if parse_qs(database.query).get("sslmode", [""])[0] not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("DATABASE_URL requires TLS sslmode")
    remote_host(required("FALKOR_HOST"), "FALKOR_HOST")
    if required("FALKOR_TLS").lower() != "true":
        raise ValueError("Cloud FalkorDB requires TLS")
    required("FALKOR_PASSWORD")
    for name in ("QDRANT_URL", "ARTIFACT_SERVICE_ORIGIN"):
        parsed = urlsplit(required(name))
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError(f"{name} requires an HTTPS endpoint without embedded credentials")
        remote_host(parsed.hostname, name)
    required("QDRANT_API_KEY")
    required("ARTIFACT_SERVICE_TOKEN")
    from cryptography.fernet import Fernet

    Fernet(required("PROVIDER_ENCRYPTION_KEY").encode())
    if required("MEM0_HISTORY_BACKEND") != "postgres":
        raise ValueError("MEM0_HISTORY_BACKEND must be postgres; container SQLite is ephemeral")
    if os.environ.get("ARTIFACT_BACKEND") != "r2":
        raise ValueError("Cloud artifact storage must use R2")
    origins = json.loads(required("ORIGINS"))
    if not isinstance(origins, list) or not origins:
        raise ValueError("ORIGINS must be a nonempty JSON list")
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme != "https" or parsed.path not in {"", "/"}:
            raise ValueError("ORIGINS requires exact HTTPS origins")
        remote_host(parsed.hostname, "ORIGINS")
    # No host/operator model credentials are shipped into the runtime.
    for name in ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "JEV_API_KEY", "TAVILY_API_KEY", "LANGSEARCH_API_KEY"):
        if os.environ.get(name, "") not in {"", "****"}:
            raise ValueError(f"Do not configure operator credential {name}; use visitor BYOK")


children = []
stopping = False


def shutdown(_signum=None, _frame=None):
    global stopping
    stopping = True
    # Stop workers first, API next, embeddings, then daemon last.
    for process in reversed(children):
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 25
    for process in reversed(children):
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def start(command):
    process = subprocess.Popen(command, cwd="/opt/engram")
    children.append(process)
    return process


def check_children():
    for child in children:
        if child.poll() is not None:
            raise RuntimeError(f"Required runtime process exited with status {child.returncode}")


def wait_for(check, seconds):
    deadline = time.monotonic() + seconds
    while not stopping and time.monotonic() < deadline:
        check_children()
        try:
            if check():
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("Required service did not become ready before its startup deadline")


def embeddings_ready():
    with urlopen("http://127.0.0.1:8091/health", timeout=2) as response:
        return response.status == 200 and json.load(response).get("status") == "ready"


def main():
    validate_environment()
    if not Path(os.environ["EMBEDDING_MODEL_PATH"]).is_file():
        raise ValueError("Embedding GGUF is missing from the real runtime image")
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        start(["dockerd", "--host=unix:///var/run/docker.sock", "--iptables=false", "--ip6tables=false",
               "--ip-forward=false", "--bridge=none", "--storage-driver=vfs"])
        wait_for(lambda: subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL, timeout=4).returncode == 0, 60)
        subprocess.run(["docker", "load", "--input", "/opt/engram/sandbox-image.tar"], check=True, timeout=180)
        start([sys.executable, "-m", "collective.embedding_server"])
        wait_for(embeddings_ready, 90)
        # Uvicorn imports the real API, including its normal dependency health checks.
        start([sys.executable, "-m", "uvicorn", "collective.app:app", "--host", "0.0.0.0", "--port", "8088"])
        start([sys.executable, "-m", "collective.agents"])
        while not stopping:
            check_children()
            time.sleep(0.5)
    finally:
        shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print a URL, credential or exception body from external services.
        print(f"Cloud runtime startup failed: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
