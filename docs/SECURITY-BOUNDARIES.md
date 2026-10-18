# What ENGRAM's security controls enforce

<!-- track2-upgrade:start -->
## Memory contracts, delivery and timeline isolation

Startup/retrieval capsules use a configured budget counted with `o200k_base`; this is a projection accounting unit, not native billing tokens for every supported provider. Explicit full reads are separately accounted. Durable passports retain selected IDs/revisions and hashes without treating a hash as a signature or proof of truth. Required context cannot be silently dropped to fit a budget. Superseded action bindings are rejected; historical reads still expose their superseded status.

Context snapshot validation and graph dependency attachment use the same per-memory PostgreSQL advisory locks as correction. A stale snapshot is rejected. These locks do not turn SQL and FalkorDB into one distributed transaction, and cannot cancel a provider request already in flight. Reference-focused tasks avoid unrelated broad recall; unrestricted retrieval can still record conservative dependencies.

Delivery identities deduplicate equivalent envelopes within ENGRAM. Receivers are unclaimable before envelope commit; acknowledgement validates current evidence and keeps its first timestamp. This does not establish exactly-once external tool effects. Private references, private parents and private replan evidence set task visibility before enqueue. Timeline responses recheck visibility for memory references in correction, claim and handoff events; hidden events still advance pagination/stream cursors. This is scoped hardening, not an exhaustive security audit.
<!-- track2-upgrade:end -->

This describes the implemented local configuration. It is not a completed penetration test or a claim that arbitrary hostile code is harmless.

| Boundary | Enforced behavior | Limit |
| --- | --- | --- |
| Sandbox process | Docker UID/GID 65534, all capabilities dropped, `no-new-privileges`, read-only image filesystem | Containers share their Docker host's kernel; this is not a microVM |
| Network | Sandbox uses Docker `network=none` | Host-side search, model and authorized MCP tools can use the network; this is not system-wide egress isolation |
| Filesystem | A per-run named volume at `/workspace`; writable limited `/tmp`; no host directory or Docker socket mounted | Code can inspect its own image and run volume. Data deliberately copied into that volume is visible to it. The volume persists to support restart continuity |
| Resources | 1 CPU, 512 MiB memory, 128 processes; commands bounded to 120 seconds; 64 MiB `/tmp` | `/workspace` has no storage quota here. Captured output uses temporary files and is size-checked after execution, not bounded while it is being written |
| Credentials | Sandbox launch deliberately passes no provider credentials; no host environment or source tree mount | Image-baked secrets or secrets supplied as task input would still be exposed; pattern detection is not comprehensive secret prevention |
| Paths/artifacts | Workspace-relative lexical paths; artifact publication rejects links/directories and records actual file hashes | This is not a complete defense against every within-container filesystem trick. Hash identity proves bytes, not that code is safe or correct |
| Procedure activation | Different verifier run, fresh recognized passing checks and actual current-file hashes matching the version manifest | Different run is not independent human judgment. Tests can be incomplete or misleading. Image tag is checked; it is not pinned to an immutable digest |
| Tenant/project scope | Authenticated memberships, scoped graph per tenant, project access checks, memory visibility and artifact authorization | Application isolation assumes trusted database/Docker administrators and correct server-side access checks; there is no separate deployment per tenant |
| Shared memory | Shared-only runs exclude private context from normal retrieval and explicit memory reads; automatic scope taints tasks that use private context | This does not prevent an authorized user or agent from deliberately entering private information into a shared task |
| Task ownership | Leased tasks carry revision/token checks; corrected dependencies revoke old ownership | Cross-store writes do not form a distributed atomic transaction; recovery and reconciliation remain relevant |

## Admission is a separate, probabilistic control

Complex workflows add user-owned milestone approvals, declared event gates, bounded task/delegation/attempt counters and deadlines. Pause, cancellation and expiry fence task completion; they cannot undo a command or provider request already in flight. Custom profiles narrow built-in role capabilities and are snapshotted into a plan. Attempt counters do not cap total provider spending. Workflow MCP effects require human approval of the exact stored arguments; uncertain remote outcomes are retained for manual reconciliation and are never blindly retried. See [the workflow guide](WORKFLOWS.md) for supported source import, patch and external integration limits.

The normal ingest path first rejects a limited set of credential-shaped strings, then persists an episode as **pending**. The selected personal model or dedicated personal admission connection returns typed admission/category/suspicious-input decisions. The live submission fixture selects Groq Safeguard for that separate connection. Suspicious input is quarantined; noise is archived; admitted input proceeds to semantic extraction. Recognized malformed Safeguard output is retried once on the same model. Failure to obtain a valid decision propagates an error and does not promote that pending episode to active. There is no accept-on-error substitute decision.

Safeguard is a model judgment, **not** the authorization mechanism, a calibrated probability, proof of truth or a guarantee against prompt injection. Authenticated scope, role restrictions, leases and sandbox controls are enforced by code independently of that judgment. Controlled internal `memory.commit` calls bypass admission by design; the infrastructure fixture is not evidence that arbitrary input passed Safeguard. No new policy-model quality evaluation is claimed in this provider-free work.

Claim resolution uses the latest active source observation and preserves competing evidence. A timestamp is not a signature; an admitted source can be wrong or malicious. Equal-time contradictory values remain unresolved. Approval authority and sensitive actions still require appropriate application controls outside this timestamp policy.

## What was actually checked without a provider

`scripts/measure-showcase.py` inspects a live container's user, network mode, read-only root, capabilities, privilege setting, resource limits and mounts. Bounded in-container probes check effective UID, a denied root write, a successful run-volume write, absent Docker socket and failed external connection. Lexical path probes exercise explicit 403 denials. The report records the actual image ID observed in this probe; that does not mean all production executions enforce digest pinning.

These checks do not attempt kernel escapes, exhaust memory/processes/disk, assess Safeguard accuracy, prove no information leakage or establish production deployment readiness. The API binds loopback and is published through the approved Cloudflare demo tunnel, with HTTPS session and exact-origin checks. Start building creates a private browser session; no login form is required. Personal keys are encrypted server-side and scoped to the user and tenant. The operator controls the encryption secret. Clearing browser site data loses automatic workspace access. See [BYOK.md](BYOK.md) for these limits. The demo still depends on the laptop; independent hosting remains pending.

Schema startup now checks a content digest under a PostgreSQL advisory lock. Unchanged clients skip repeated ALTER statements, addressing the deadlock observed during the live comparison. This does not promise that future schema changes can run without deployment coordination. Explicit plan replacement preserves the failed or cancelled plan and creates a new graph-linked task; active plans cannot be replaced through that recovery option.
