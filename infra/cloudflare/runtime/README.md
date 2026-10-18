# ENGRAM ENGINE cloud runtime

This is the real FastAPI, DeepAgents worker, CPU embedding server and nested Docker execution deployment. It is separate from the already deployed public website Worker. No provider response, database, readiness check or sandbox is simulated.

## Current verification status

- Startup configuration boundaries passed three local tests, including rejection of loopback databases, unencrypted cloud stores, ephemeral Mem0 history, missing keys and host/operator inference credentials.
- Python and JavaScript syntax checks passed.
- The source allowlist context was generated on D with the actual 1.3 GB FP32 Mixedbread GGUF and exported restricted sandbox image. Models and image archives are not committed.
- A real `linux/amd64` Docker build was attempted. It exited during image pull/context transfer with `SIGBUS` while the Windows C volume was full. The image is not built or deployed. Do not restart it until the Docker/WSL disk has sufficient space or is safely relocated.
- Wrangler dry-run did not finish before the storage-related pause. No successful dry-run, image validation or remote execution is claimed.

## Persistent services are mandatory

The Container disk, Docker image store, workspace volumes and embedding cache are ephemeral. PostgreSQL, FalkorDB and Qdrant must use durable remote services. R2 stores published artifacts; it does not make an arbitrary SQL, graph, vector or Docker-volume directory durable. Worker leases and task recovery use PostgreSQL. Active uncheckpointed sandbox filesystem changes can be lost on a Container restart; published artifacts must be restored through the application's artifact flow.

Required runtime Worker secrets:

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | Durable PostgreSQL URL with TLS `sslmode=require`, `verify-ca` or `verify-full` |
| `FALKOR_HOST`, `FALKOR_PORT`, `FALKOR_USERNAME`, `FALKOR_PASSWORD`, `FALKOR_TLS` | Durable graph service, with `FALKOR_TLS=true` |
| `QDRANT_URL`, `QDRANT_API_KEY` | Durable HTTPS vector store and scoped service credential |
| `PROVIDER_ENCRYPTION_KEY` | Stable Fernet key, backed up outside the Container |
| `ARTIFACT_SERVICE_ORIGIN`, `ARTIFACT_SERVICE_TOKEN` | HTTPS private R2 service on the public Worker |
| `ORIGINS` | JSON array of exact permitted public HTTPS origins |
| `MEM0_HISTORY_BACKEND` | Must be `postgres` |
| `RUNTIME_SERVICE_TOKEN` | Shared transport secret between public Worker and runtime Worker |

Do not configure operator Groq, Anthropic, Jev or search credentials. Visitors use their own encrypted provider connections. Never commit `.env` files or upload the laptop's runtime directory.

The public website Worker must set `X-Engram-Runtime-Token` from its own secret when forwarding `/api` requests to this Worker. Never put this token into browser JavaScript. Only `/api` is exposed by the runtime Worker, with no caching. The constant Durable Object name and `max_instances: 1` select a single runtime. Cron wakes that same runtime every minute so queued work does not depend on laptop traffic. It still cannot guarantee that a cloud instance never restarts.

## Build and validation

From the repository root after resolving host storage:

```powershell
wsl -d Ubuntu-22.04 --exec docker save --output /mnt/d/Neurohacks/data/collective/cloud-runtime-sandbox.tar engram-sandbox:local
wsl -d Ubuntu-22.04 --exec chmod 644 /mnt/d/Neurohacks/data/collective/cloud-runtime-sandbox.tar
.\.venv-collective311\Scripts\python.exe infra/cloudflare/runtime/prepare_context.py --sandbox-image-tar data/collective/cloud-runtime-sandbox.tar
wsl -d Ubuntu-22.04 --exec docker build --platform linux/amd64 -t engram-engine-runtime:local /mnt/d/Neurohacks/data/collective/cloudflare-runtime-build
.\.venv-collective311\Scripts\python.exe infra/cloudflare/runtime/test_supervisor.py
```

The example WSL paths reflect the current checkout. Adapt them if the repository moves. `prepare_context.py` copies only named files and top-level `collective/*.py`, never `.env`, user uploads, sessions or browser cookies. Unexpected files already present in the staging context abort preparation for review. Reprepare after application source changes.

Under `infra/cloudflare/runtime`, install the exact lockfile with `npm ci`, then run `npm run check` for a non-publishing Wrangler dry-run. Wrangler must have access to the same real Docker engine. `WRANGLER_DOCKER_BIN` supports a custom Docker client path; Linux Wrangler must have a Linux Node runtime and its own authenticated deployment access. Do not assume the Windows Docker Desktop engine can access WSL's independent images.

Only after actual image validation, cloud secrets, credit entitlement checks and approval of any uncovered costs should `npm run deploy` be used. No deploy was performed by this preparation. `standard-4` and one maximum instance are configured for the actual CPU embedding and nested execution workload. Source and image publication alone do not establish a working durable backend.

## Startup and shutdown

The root supervisor validates durable cloud configuration before launching anything, starts a root Docker daemon with iptables, IPv6 iptables, IP forwarding and bridging disabled, loads the existing sandbox image, waits for real CPU embedding readiness, then starts the API on port 8088 and the background worker. It monitors every child and stops the group if a required child exits. SIGTERM/SIGINT stop workers and API before the Docker daemon, with bounded termination and kill escalation. Tini reaps orphaned processes.

Root is required for the outer daemon. Untrusted child execution retains the existing application's non-root UID, `network=none`, read-only root, dropped capabilities, CPU/memory/process limits and restricted mounts. No host Docker socket is mounted into untrusted children. The `vfs` nested storage driver avoids relying on nested overlay support; its disk and performance costs require measurement. These properties still need verification on the actual Cloudflare instance.

## Official platform references

- [Container configuration and deployment](https://developers.cloudflare.com/containers/get-started/)
- [Docker-in-Docker and ephemeral storage boundaries](https://developers.cloudflare.com/containers/faq/)
- [Container SDK lifecycle and startup API](https://developers.cloudflare.com/containers/api/container-class/)
- [Runtime environment and secrets](https://developers.cloudflare.com/containers/examples/env-vars-and-secrets/)
