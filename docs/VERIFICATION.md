# Local verification: 18 October 2026

<!-- track2-upgrade:start -->
## Track 2 upgrade: memory contracts and replay-safe coordination

ENGRAM now binds work to explicit memory references, loads compact context capsules and records durable memory passports with revisions, content hashes, projection fingerprints and budget accounting. Pinned obligations remain included. A reference superseded before startup is rejected; a correction racing with snapshot subscription also fails closed. Replacement plans bind the new active fact rather than treating historical quoted IDs as current instructions. Explicit full historical reads remain possible.

Handoffs use deterministic delivery identities and an unclaimable `awaiting_handoff` state. The envelope and queued transition commit together. Identical retries reuse one receiver; current evidence revisions are checked before acknowledgement, and replay preserves the first acknowledgement. Private references and parents mark tasks private before enqueue. Private-memory correction events are filtered from another member's timeline, including legacy untagged events.

### Four new live matched pairs

All eight verifier sessions passed the same ten real pytest cases with Groq `openai/gpt-oss-20b`, identical artifact hashes, alternating order and no discarded warmup. Both paths disabled automatic post-run curation. The baseline already had known correct files; this measures verification reuse, not avoided code generation.

| Median metric | Known-file baseline | Memory-capsule reuse |
| --- | ---: | ---: |
| Observed provider calls | 4 | 2 |
| Provider-reported tokens | 1,782.0 | 1,416.5 |
| Elapsed seconds including queue/startup | 28.391 | 26.390 |

Median paired savings: **2 calls**, **365.5 observed tokens** and **2.001 seconds**. That is 50% fewer median calls and about 20.5% fewer median tokens. Three timing pairs favored reuse; one was slower. Four local pairs cannot establish a general cost or latency guarantee. SDK-internal retries are not separately counted; failed calls can have unknown billed tokens.

The exact measured runtime source is preserved under ignored `data/collective/track2-upgrade/measured-runtime/` with digest `d87aba1fc7b1c3f06bd2d3ffd31f3a2a654096c214c187d75939854aa51d3db8`. Final private-reference, stale-binding, audit-event and coordinator context/scope recovery changes were tested separately; those changes are not retroactively relabeled as the source of the four-pair measurements.

### Real concurrency and crash recovery

- 128 direct-reference context reads at concurrency 8: **70.7 operations/s**, p95 **968.1 ms**, zero operation errors. This includes scoped retrieval and durable provenance, not semantic-search embeddings or LLM throughput.
- 16 semantic writes at concurrency 8: **20.968 seconds** total, p95 **14605.0 ms**, zero errors. Local CPU embeddings dominate this path; it is not a FalkorDB performance claim.
- Eight competing corrections: one committed replacement, seven stale-revision conflicts. Exactly **one of sixteen** bound consumers was invalidated; fifteen unrelated consumers were preserved at correction time.
- Twenty concurrent identical handoffs: one receiver and one envelope. A deliberately interrupted delivery survived actual API/worker restarts, recovered into the same receiver, and retained one acknowledgement after replay.

These load/recovery fixtures call real production functions and services with **zero provider calls**. They are not described as autonomous model completions. The earlier recovered end-to-end team scenario remains separately documented below.

### Final checks and remaining live blocker

Final real-service regression: **40 passed, 1 opt-in provider test skipped**. Provider inference was disabled for that suite. The live pairs above use actual provider inference separately. **8 local browser checks** and **1 public HTTPS checks** passed. Production build and Ruff passed.

The additional Groq120B team workflow completed across an actual API/worker restart: checked procedure reuse, researcher-to-curator handoff, real Mem0 write-back and correction, and a replacement plan recommending Priya. The calculator verifier remained completed while the graph invalidated consumers of the changed approval fact. Earlier 20B quota and 120B scope/budget attempts remain recorded; this is not a first-attempt success. Four-pair savings remain Groq20B measurements. The original Qwen long-argument fidelity failure remains unresolved. Permanent hosting and publishing the matching source repository remain pending; the public tunnel depends on its laptop.

Inspect `/evidence/live/` on the running app. `track2-upgrade.json` contains sanitized receipts and every paired observation. The Procedures page exposes Memory passports, Durable handoff receipts and the repeated live comparison without adding navigation destinations.
<!-- track2-upgrade:end -->

## Completed live submission scenario

The ORCHID team scenario completed with recovery. It used real DeepAgents, Groq, LangSearch, Safeguard, Mem0, PostgreSQL, FalkorDB, Qdrant and restricted Docker execution. Qwen started the work; the explicitly authorized Groq 20B model completed it. No response, file, route or passing receipt was mocked.

| Boundary | Verified evidence |
| --- | --- |
| Team and handoff | Published calculator/test artifacts, acknowledged handoff, separate verifier checks and active artifact-bound procedure v1 |
| Graph changes action | Actual Maya recommendation, retained competing claims, dependency traversal, stale work and completed Priya recommendation |
| Restart persistence | Actual API/worker process change; session, two messages, two hashes and 40 original coordinator checkpoint rows retained |
| Matched live reuse | Both fresh containers passed ten tests; actual provider receipts counted below |
| Browser to API to data | Five local Chromium checks passed in 40.8 seconds: BYOK isolation, beginner guide, full navigation, graph/reuse/artifact evidence, unauthenticated public evidence |
| Public HTTPS | One Chromium check passed in 10.6 seconds: Start building, Secure/HttpOnly/SameSite session, actual artifact hash and cross-tenant denial |
| Regression | 34 passed, one opt-in provider test skipped, 281.43 seconds; provider inference disabled for this suite |
| Build and article | Production frontend build and Ruff passed; all 12 article images loaded at 1440/390 px with no browser errors or overflow |

The live pair used `openai/gpt-oss-20b`: baseline 4 calls / 1,823 tokens / 66.407 seconds; reuse 3 calls / 5,034 tokens / 53.918 seconds. Reuse saved one call and 12.489 observed seconds, but used 3,211 more tokens. One baseline-first pair cannot establish general cost or latency savings. Timing includes queue/startup. Both arms disabled automatic post-run curation. Failed SDK calls can have unknown billed tokens, and internal retries are not separately counted.

This is recovered execution with eight excluded comparison pilots and one stopped initial replan, not first-attempt success. Conservative graph dependencies invalidated eight historical runs; minimal semantic impact analysis is not demonstrated. The old Qwen 800-character fidelity failure remains unresolved. Existing video footage predates this live validation. Permanent hosting and publishing the matching code remain pending.

The sanitized public report is served at `/evidence/live/`. `outputs/submission-live/verification.json`, `evidence.json`, `public-check.json` and `backend-checks.txt` retain the current receipts. Private sessions and runtime credentials are excluded from the evidence ZIP. The full source report remains in ignored runtime storage.

## Historical verification records

The following sections describe earlier fixtures at their original dates.

# Local verification — 17 October 2026

This records checks performed against real local services. Infrastructure success is separate from the credential-backed workflow results below.

Groq/Safeguard/LangSearch live results and the earlier failed Kev admission assertion are recorded in [PROVIDER-VERIFICATION.md](PROVIDER-VERIFICATION.md). The original Anthropic/Jev path remains unverified.

## Results

- Complex workflow extension: **28 passed, 1 skipped** in the complete real backend suite (`verify-advanced.ps1 -Stage all-checks`, 242.81 seconds). Provider tests were explicitly disabled. Coverage includes source repair, separate-container verification, nested artifact paths, stale Python bytecode invalidation, a Git-applicable patch including missing-newline handling, workflow budgets, deadlines, approvals, signals and scoped controls.
- Current browser checks: **four passed** across the workspace clarity view, infrastructure evidence view, specialist/source/draft creation and a post-restart draft comparison. The restart-only test was deliberately skipped in the initial pre-restart run, then passed after the actual restart. Desktop and 390-pixel mobile screenshots were captured; the mobile screenshot was visually inspected and had no horizontal overflow.
- Actual API and worker processes restarted. A running workflow waiting for human approval preserved its workflow/step state, specialist record and snapshot, source manifest/bytes and empty execution ledgers. The isolated check was cancelled afterward. Evidence: `data/collective/workflow-restart-proof.json` and `restart-process-proof.json`. A separate browser-created draft also survived unchanged. No model-driven task was started by these checks.
- Frontend production build, Python compilation and Ruff passed. [The workflow guide](WORKFLOWS.md) describes supported execution and external-action boundaries. Autonomous model-driven completion and remote MCP execution are not established by these results.

- Previous Python suite: **25 passed, 1 skipped** (`scripts/test-local.py`, 288.73 seconds during film rendering). The skipped test requires explicit `ENGRAM_PROVIDER_TESTS=1`; live provider checks are also run separately. The suite includes Safeguard decision semantics, atomic cross-process token reservations, role-filtered catalog retrieval and cache isolation, current-file publication requirements, and rejection of ordinary shell success as test evidence.
- Infrastructure tests used PostgreSQL, FalkorDB, Qdrant and the existing GGUF model through llama.cpp. They exercised concurrent memory writes, visibility filtering, graph relations and retrieval, correction invalidation, handoffs, lease fencing and a real Docker sandbox.
- Sandbox checks executed Python and pytest as uid 65534, confirmed read-only root restrictions, and checked that provider credentials were absent.
- HTTP smoke checks passed for account registration, project creation and persistence, cross-tenant denial, CSRF header enforcement, foreign-origin rejection and HttpOnly cookies.
- Playwright: **1 passed**, covering actual account registration, project creation, task submission, service diagnostics and memory navigation against the built UI.
- Separate live-artifact Playwright flow: **1 passed**. Real published files downloaded with matching SHA-256 checksums; another tenant received 404; artifact cards and the real graph rendered. This verifies delivery and isolation, not the correctness of every historical artifact version.
- Current infrastructure-evidence Playwright flow: **1 passed**. It checks both artifact versions, exact downloaded hashes, the corrected fact and blocked replan, preserved claims, the new logo and cross-tenant denials. It explicitly asserts that autonomous team verification is false.
- Production frontend build, Python Ruff checks and `git diff --check` passed.
- The initial API health check reported PostgreSQL, FalkorDB, Qdrant, embeddings, worker and sandbox **ready**, with missing provider keys. Selected real Groq, Safeguard and LangSearch credentials are now configured; provider behavior is verified separately from configuration-only health labels. Triton remains **deferred**.

## Remaining credential-dependent checks

The selected provider path is Groq Qwen, Groq Safeguard and LangSearch. Anthropic, Jev and Tavily need credentials only if explicitly selected. Run `.\scripts\verify-live.ps1` for the team workflow, or add `-Memory` for extraction/correction. The wrapper pauses the normal worker while the live harness schedules the test tenant, then restores it. Actual API process restart continuity has passed independently.

Real 20B Mem0 extraction and correction have passed: replacement ownership became active, the previous fact became superseded and dependent work became stale. The full procedural lifecycle is tracked separately in the live team report. No substitute model or canned response is used. No external MCP endpoint is configured or claimed as tested. FalkorDB Cloud has not been authenticated or migrated; the verified graph endpoint is local WSL Docker.

The code includes explicit missing-service errors. A running local UI does not imply that model-dependent workflows are operational before credentials are supplied.

The final six infrastructure service probes returned ready after rendering. The current Qwen workflow remains quota-blocked; the direct-tool, zero-model-call walkthrough scenario is documented separately in [DEMO-STATUS.md](DEMO-STATUS.md).
