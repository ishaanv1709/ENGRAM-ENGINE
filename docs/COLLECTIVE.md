# ENGRAM ENGINE

Persistent graph memory and coordination for agent teams.

## Open locally

The application is served at **http://127.0.0.1:8088**. Register an account, create a project, upload source documents, then submit an objective. There are no pre-created user accounts or simulated agent responses.

From PowerShell in the repository:

```powershell
# First installation or reproducible reinstall (downloads dependencies).
.\scripts\start-local.ps1 -Install

# Subsequent starts.
.\scripts\start-local.ps1

# Stop only app processes recorded by the launcher; preserve database volumes.
.\scripts\stop-local.ps1
```

Requirements: Windows with the existing `Ubuntu-22.04` WSL2 distribution, Docker Engine inside WSL, Node.js, and uv. The existing model `data/models/mxbai-embed-large-v1_fp32.gguf` is used for actual CPU embeddings. Triton is intentionally deferred.

On a fresh checkout without that model, download Mixedbread's official F16 GGUF and set the model path explicitly before starting:

```powershell
New-Item -ItemType Directory -Force data/models
curl.exe --fail --location "https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1/resolve/b33106f/gguf/mxbai-embed-large-v1-f16.gguf" --output data/models/mxbai-embed-large-v1-f16.gguf
# Add this to .env.collective:
# EMBEDDING_MODEL_PATH=data/models/mxbai-embed-large-v1-f16.gguf
```

The verified local run uses the existing FP32 file; the F16 download above is an alternative published by the model author. The legacy chat-model files are not needed by the Groq-backed Collective app.

The Python agent/API environment is `.venv-collective311`; the CPU embedding environment is `.venv-collective-linux`. Python 3.11 is required. `uv.lock` pins the application dependencies. The Linux-only embedding wheel is separately pinned in `collective/embedding-requirements.txt`.

## Credentials

`.env.collective` is ignored by Git. Start from `.env.collective.example`.

```dotenv
AGENT_PROVIDER=groq
AGENT_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=****
DECISION_PROVIDER=safeguard
SAFEGUARD_MODEL=openai/gpt-oss-safeguard-20b
WEB_SEARCH_PROVIDER=langsearch
LANGSEARCH_API_KEY=****
LANGSEARCH_DAILY_LIMIT=1000
```

Replace these values locally; never put secrets into a conversation, document, or source commit. Restart the API and worker after editing settings. `****` is explicitly rejected as a credential.

- Groq: actual agent inference, Mem0 extraction and relation extraction; Safeguard supplies policy decisions using the same key.
- LangSearch: actual web research with a shared 1,000-request daily limit.
- Anthropic, Jev and Tavily are explicitly selectable alternatives and require their respective keys only when selected.
- Self-hosted Mem0 requires no Mem0 Platform key.

### Groq, local Kev, and LangSearch

The alternative provider path is explicit; it never silently switches providers:

```dotenv
AGENT_PROVIDER=groq
AGENT_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=****
DECISION_PROVIDER=kev
DECISION_URL=http://127.0.0.1:8009/v1/systemone
JEV_MODEL=kev-latest
WEB_SEARCH_PROVIDER=langsearch
LANGSEARCH_API_KEY=****
LANGSEARCH_DAILY_LIMIT=1000
```

Install Kev with `scripts/install-kev.ps1` before starting this configuration. It has a separate Python 3.12 environment and runs `jaredpalmer/kev-0.8b@v1.0` on CPU. The first start needs the adapter and approximately 1.7 GB of base weights. Its source is the Apache-2.0 project at https://github.com/jaredpalmer/kev; the unrelated PyPI package named `kev` is not used. Local inference has no hosted request quota but consumes memory, CPU time and electricity. Kev is not the Jev model, and API compatibility does not establish equivalent accuracy or security screening.

Groq executes the real DeepAgents tool loop. The runtime builds the structured outcome from persisted graph dependencies, published artifacts, search-source events and successful sandbox checks. It preserves the model's original report, validates execution evidence and asks builders/verifiers to continue when required evidence is missing. Separate specialist workers can run concurrently. Shared PostgreSQL token reservations pace model requests across processes; account daily limits still apply and are surfaced without substituting a model.

LangSearch reservations are stored atomically in PostgreSQL and shared by workers and tenants. The local budget caps attempted requests at 1,000 per UTC database day; failed requests count conservatively. Calls made outside ENGRAM are not tracked. Search exhaustion produces an explicit error and never switches to another search provider.

For this local application, values in `.env.collective` take precedence over inherited environment variables, preventing an unrelated host provider key from overriding the selected local key. Stop and start the app after changing this file.

### Groq Safeguard decisions

Set `DECISION_PROVIDER=safeguard` and `SAFEGUARD_MODEL=openai/gpt-oss-safeguard-20b` to replace the local Kev decision service. This uses the existing `GROQ_API_KEY`; no Jev key or local decision-model process is required. `AGENT_MODEL` selects the main model independently. The current local configuration explicitly selects `qwen/qwen3.8-27b`. Its full live-team verification is quota-blocked; see `DEMO-STATUS.md`.

Safeguard evaluates a versioned application policy and returns schema-validated boolean decisions with rationales and category choices. These are not calibrated probabilities, and the application does not pass them off as Jev probability scores. Positive fact admission, rejection/quarantine and supported corrections remain distinct decisions. Tenant authorization, lease/revision fences and sandbox limits remain deterministic server checks. A successful sample classification does not establish general detector accuracy.

The tested account limits Safeguard to 2,000 tokens/minute and the main model to 8,000 tokens/minute. The compact policy fits a short observation; provider throttling can still make concurrent workflows slow. The adapter uses bounded provider retries and never changes models silently.

Until keys are supplied, account management, project storage, artifact uploads, service diagnostics, direct retrieval of committed memory, and infrastructure tests can run. Model-driven tasks become **blocked**, with an explicit missing-key error. No other model, canned response, or synthetic completion is substituted.

## Services

| Service | Local endpoint | Authority |
|---|---|---|
| API and built React UI | 127.0.0.1:8088 | Authenticated application |
| PostgreSQL | 127.0.0.1:55432 | Users, memberships, conversations, runtime tasks, leases, checkpoints, events, outbox |
| FalkorDB | 127.0.0.1:56379 | Connected memories, entities, relations, provenance, task dependencies |
| FalkorDB Browser | 127.0.0.1:53000 | Local database inspection |
| Qdrant | 127.0.0.1:56333 | Mem0's derived vector index |
| GGUF embeddings | 127.0.0.1:8091 | Actual normalized Mixedbread vectors, llama.cpp CPU |
| Docker sandboxes | WSL Docker Engine | Restricted builder/verifier execution |

All published service ports bind to loopback. Database passwords in the example are local development credentials. This configuration is not a public hosting configuration. No automatic public deployment is performed.

The launcher keeps a foreground WSL process alive so Linux services survive after PowerShell exits, and waits for all six local services to report ready. The stop script terminates only recorded app processes and preserves database containers and volumes.

For FalkorDB Cloud, configure `FALKOR_HOST`, `FALKOR_PORT`, `FALKOR_USERNAME`, `FALKOR_PASSWORD`, and `FALKOR_TLS` using the connection details supplied by the cloud console. Match its TLS setting; `falkors://` or `rediss://` denotes TLS. A URL containing only `username@host:port` still needs the instance password. Restart the app and workers. The ENGRAM adapter and Mem0 plugin transport both use the configured connection. PostgreSQL, the vector index, embeddings, and sandboxes can remain local. Switching graph endpoints does not migrate existing local graphs.

## Agent architecture

Each executable worker is created using the actual Deep Agents library. A durable ENGRAM scheduler coordinates specialist runs instead of relying on an untracked nested agent call.

- Coordinator: plans work and dispatches independent tasks.
- Researcher: inspects sources and records grounded observations.
- Builder: creates artifacts in an isolated container and runs checks.
- Verifier: independently executes checks and verifies procedures.
- Curator: consolidates episodes into sourced facts and proposes reusable workflows.

The worker process has three slots by default. A coordinator that has pending children releases its slot in a `waiting` state and resumes after the children settle. PostgreSQL `FOR UPDATE SKIP LOCKED` claims tasks; renewable leases and revision fencing reject results from expired or revoked owners. Dependency failure blocks dependent completion. Worker heartbeat appears in service readiness.

The Deep Agents default `task` tool is excluded from the authorized model-visible tool set. Delegation goes through `team_dispatch` so ownership, checkpoints, events, and resource limits remain visible. The original planning/context-management harness is still used. Full checkpoints use `AsyncPostgresSaver` with a tenant/run-specific thread identifier.

`MAX_PARALLEL_AGENTS`, `MAX_AGENT_STEPS`, `MAX_TOOL_CALLS`, and `MAX_RUN_SECONDS` bound execution. A coordinator can create at most twelve direct delegated tasks through its dispatch tool. Arbitrary third-party actions are not claimed to be exactly-once; tool operations must supply their own idempotency guarantees if that behavior is required.

## Memory model and ENGRAM continuity

The original six categories remain: pinned, critical, episodic, relational, temporary, and discard. Categories control importance/lifecycle. Memory type and visibility are independent dimensions.

| Type | Contents |
|---|---|
| Episodic | Observations, source chunks, task outcomes and their evidence |
| Semantic | Mem0-extracted facts, named entities, supported relations, corrections |
| Procedural | Real tool descriptors/schemas and proposed or independently verified workflows |

The original three tiers remain conceptually intact:

1. Pinned context, limited to 2 KB per visible project context.
2. A bounded LRU retrieval cache, keyed by tenant/user/project/agent/query/graph revision.
3. Durable graph memory and retrieval indexes.

FalkorDB revisions invalidate cache snapshots across worker/API processes. Hybrid retrieval combines vector candidates, scoped BM25 lexical scores, and entity-neighbor expansion. Approximate token budgeting bounds injected context. Retrieval currently considers at most 1,000 visible project records for pinned/lexical candidates and 60 vector candidates; this is a deliberate bounded implementation, not a claim of unlimited-scale retrieval.

The original `src/memory_influence.py` now preserves custom pinned fields and temporary memories. Legacy terminal commands and data are retained; existing personal memory files are not automatically imported into a shared project.

## Graph model

Essential nodes: `Memory`, `Entity`, `Relation`, `Task`, and a revision `State` node. Each authenticated tenant uses its own derived graph name. Mem0 namespaces separate project and visibility scopes within the derived extraction store.

Essential relationships:

```cypher
// Evidence behind a fact.
MATCH (fact:Memory)-[:SUPPORTED_BY]->(source:Memory)
WHERE fact.id = $id
RETURN fact, source

// Other memories sharing an entity.
MATCH (m:Memory {id:$id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(related:Memory)
RETURN related

// Decisions affected by a corrected belief.
MATCH (task:Task)-[:DEPENDS_ON]->(fact:Memory {id:$id})
RETURN task.id

// Fact version history.
MATCH (newer:Memory)-[:SUPERSEDES]->(older:Memory)
RETURN newer, older

// Explicit subject/predicate/object with supporting memory.
MATCH (s:Entity)-[:SUBJECT_OF]->(r:Relation)-[:OBJECT]->(o:Entity),
      (r)-[:SUPPORTED_BY]->(evidence:Memory)
RETURN s.name,r.predicate,o.name,evidence.id
```

Memory writes have durable outbox records, deterministic replay behavior, and a completion marker so partial graph writes can be retried. Corrections use an expected revision and a per-record database advisory lock. They invalidate direct readers, dependent tasks, and parent coordinators. Separate database systems do not form a distributed transaction; an interrupted cross-store operation must be reconciled rather than described as atomic.

## Handoffs and resources

Handoff packets contain the objective, checkpoint, remaining work, memory IDs/revisions, artifact IDs and typed integer test-event IDs. These identifier types are validated separately. Agents may omit artifact/test references to attach their own current resources from the actual execution ledger. Receivers verify memory revisions before acknowledging. A stale packet fails explicitly and requires replanning.

Each sandbox uses a private named volume. Shared artifacts are individually published files with SHA-256 checksums; agents copy authorized artifacts into their own sandbox before use. Concurrent workers do not write into a shared mutable source directory.

## Tools as procedural memory

The stable control tools handle memory, coordination, document discovery and capability search, with a small role-specific core for basic execution/publication. Optional capabilities are semantically retrieved from registered descriptions and bound into the model-visible tool set. Role permissions are applied before the retrieval limit so another role's tools cannot crowd out authorized matches. Role checks are enforced again at execution.

Real tools include web search, sandbox command/file operations, artifact publication and reading, corrections, procedure proposal and verification. Workflow proposals require real successful check event IDs. Activation requires an independent verifier's own successful execution evidence. Model-generated claims of test success are not accepted as check events.

The current sandbox's verification contract supports Python pytest and unittest. A check must actually execute at least one passing test; a file-writing command, `echo`, collection-only output or an ordinary zero exit code is not passing test evidence. General commands retain execution receipts. The runtime refreshes the file-write/check/publication ledger on every reasoning step, pauses repeated identical writes, and rejects completion when tracked changed files lack fresh tests or matching published bytes.

Workspace owners can connect public HTTPS MCP servers and authorize exact advertised tool names. Empty authorization grants no tools. Private-network endpoints, embedded URL credentials, and non-HTTPS endpoints are rejected. This version supports public MCP connections without custom authentication headers; authenticated MCP integrations require an explicit credential adapter before use.

## Security boundaries

- Argon2 password hashing, opaque hashed session tokens, HttpOnly/SameSite cookies.
- Server-derived tenant identity and owner/member/viewer membership.
- Same-origin mutation checks and an explicit CSRF protection header.
- Separate user/team/agent memory scopes. Access to private context narrows the run's result visibility; private-derived memory is not automatically promoted to team scope.
- Pending observations are not retrieval candidates before admission; suspicious observations are quarantined.
- Recognizable private-key/provider-token patterns are rejected from memory ingestion. This is not a comprehensive secret scanner.
- Container execution uses uid 65534, no network, read-only root, dropped capabilities, process/memory/CPU/time limits, and no provider keys or Docker socket inside the container.
- Provider responses and headers are not dumped into public error messages.

The trusted backend controls the Docker engine. A container is not an absolute isolation guarantee against kernel vulnerabilities. This implementation has focused tests, not an exhaustive security audit.

## Verification

```powershell
# Pure contracts (no substitutes for external services).
.\.venv-collective311\Scripts\python.exe -m pytest collective/tests/test_contracts.py -q

# Real HTTP authentication, CSRF, isolation and persistence checks.
.\.venv-collective311\Scripts\python.exe scripts/smoke_http.py

# Real service tests, Windows event-loop compatibility included.
.\.venv-collective311\Scripts\python.exe scripts/test-local.py

# Real selected providers, with normal worker pause/restore.
.\scripts\verify-live.ps1
.\scripts\verify-live.ps1 -Memory

# Real browser workflow.
cd frontend
npx playwright test
```

Credential-gated tests are in `collective/tests/test_providers.py`. They deliberately skip unless `ENGRAM_PROVIDER_TESTS=1` and the selected providers' real keys are configured. `scripts/verify-live-workflow.py` exercises the selected live models, research provider, Mem0 and sandbox workflow. A skipped provider test does not count as a working agent integration. The in-app memory benchmark writes clearly labeled evaluation fixtures and reports actual measurements; it does not invent an agent accuracy score.

## Project structure

```
collective/         API, memory, integrations, scheduler, tools, security and tests
frontend/          React/TypeScript application and real-browser test
infra/             Sandbox image and pinned wheel requirements
scripts/           Local startup, shutdown and verification
src/               Original ENGRAM implementation
data/collective/   Local runtime files/logs/artifacts (ignored by Git)
```

The main provider calls, live web research, autonomous fact consolidation, and full multi-agent behavior require credentials and must be verified against those providers before a complete demonstration can be claimed. Triton and public deployment remain deferred by the user.
