# Provider verification: 18 October 2026

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

## Completed live evidence: 18 October 2026

The real DeepAgents coordinator dispatched researcher and builder work, published two files, acknowledged a handoff, completed independent checks and retained an artifact-bound procedure. The initial model was Qwen; after its daily token quota was exhausted, the user explicitly authorized Groq 20B to finish. An agent first recommended routing ORCHID approval to Maya. A supplied newer source named Priya. FalkorDB dependencies identified old readers and fenced stale work. After an actual API and worker restart, the repaired replacement plan completed and recommended Priya without repeating documentation research or rebuilding code. The same private session, two conversation messages, both artifact hashes and 40 original coordinator checkpoint rows survived.

| Measured metric | Exact artifact bundle | Verified procedure | Baseline minus reuse |
| --- | ---: | ---: | ---: |
| Observed provider calls | 4 | 3 | +1 |
| Observed provider tokens | 1,823 | 5,034 | -3,211 |
| Elapsed seconds, including queue/startup | 66.407 | 53.918 | +12.489 |

Both arms used Groq `openai/gpt-oss-20b`, the same two artifact versions and the same ten-test pytest suite in fresh restricted containers. The baseline received known correct files; reuse loaded the active, independently verified version 1 procedure. Both used automatic owner-authorized memory scope and disabled automatic post-run curation. Counts include recorded Groq-adapter agent, memory and admission requests attributed to each verifier. Positive signed differences favor reuse; negative values mean overhead. This is one baseline-first pair with warm shared services, not a randomized performance study or a code-generation savings estimate. Failed calls can have unknown billed tokens; SDK-internal retries are not counted individually.

Backend regression: **34 passed, 1 opt-in credential-dependent test skipped**. This suite result is separate from the actual credential-backed live scenario.

This was a recovered, multi-attempt execution, not a first-attempt or all-Qwen pass. The evidence retains 8 excluded debug comparison pilots and the stopped first replan; only the final matched pair enters the table. The correction was supplied explicitly, not autonomously discovered. Conservative context dependencies invalidated all eight historical fixture runs, so minimal semantic impact analysis is not demonstrated. The earlier exact 800-character Qwen tool-argument probe still failed (496 received); its cause is unresolved. The public Cloudflare demo remains laptop-dependent; permanent hosting is pending. The existing film predates this validation.

Inspect the sanitized report and exact event IDs at `/evidence/live/` on the running app. Portable files: `outputs/submission-live/index.html` and `evidence.json`. Reproduction and scope: [LIVE-DEMO.md](LIVE-DEMO.md).

## Historical records

The following records describe earlier fixtures and their status at the time. They are retained for provenance.


The following records describe earlier fixtures and their status at the time. They are retained for provenance.


The following records describe earlier fixtures and their status at the time. They are retained for provenance.

# Provider verification — 16 October 2026

## Current Qwen demo

The selected model is `qwen/qwen3.8-27b`, with Groq Safeguard and LangSearch. Actual discovery/completion, benign admission, injection quarantine, Mem0 extraction and live research passed. Earlier partial live runs also produced real files, a handoff and independently passing Docker tests. The current complete team objective did not pass: Groq reported daily quota exhaustion before the capacity builder, semantic curation and learned-procedure sequence finished.

A separate tool-argument fidelity probe requested an exact 800-character string and received 496 characters with finish reason `tool_calls`. The underlying cause has not been established. Request quota headers still showed 922 requests remaining, so request count alone is not sufficient capacity evidence. Do not claim that adding a key automatically resolves the argument-fidelity issue. No substitute model was selected.

The user chose to finish the walkthrough and report the live-test blocker. Further credential-backed verification stopped. The film distinguishes architecture, earlier partial live captures and controlled infrastructure scenarios. The latter invoke production tools, actual Docker tests and real databases directly, without model calls or mocked services. Both artifact versions independently passed; v2 has 10 passing tests. Reuse measured zero model tokens and zero execution calls saved in this fixture, not a claimed speedup.

Actual API/worker restarts preserved the live session, 23 memories and three checkpoint threads; a separate infrastructure fixture retained its session, nine memories, four artifact hashes, two active procedure versions and competing claims. Its revised plan remained blocked, as expected. These are separate persistence fixtures, not a complete autonomous workflow.

Runtime changes include episodic goal storage, compact sourced curation, response receipts, completion controls, independent current-byte verification, shared-only memory retrieval and privacy inheritance for replans. PostgreSQL automatic prepared statements are disabled to avoid result-shape failures across live schema changes. The migration-related failed attempt is preserved in the live report.

Reports remain in ignored `data/collective/`: `live-verification.json`, `qwen-tool-fidelity.json`, `film-infrastructure-evidence.json`, `demo-restart-proof.json`, `film-restart-proof.json` and `restart-process-proof.json`. See `docs/DEMO-STATUS.md` for delivery evidence.

## Earlier Safeguard and 20B configuration

The local configuration now selects Groq `openai/gpt-oss-20b` for agents and Mem0, `openai/gpt-oss-safeguard-20b` for policy decisions, and LangSearch for web research. The user explicitly authorized 20B after 120B exhausted its daily account quota. Providers do not switch automatically.

Safeguard's real benign-fact and obvious injection fixtures passed. The integrated admission/Mem0 pipeline produced two facts; actual injection ingestion was quarantined. That preflight used the 120B main model for Mem0 before the switch; it does not establish 20B extraction quality. Safeguard returns policy booleans and rationales, not Jev-style calibrated probabilities.

The 20B researcher completed with persisted web source events. The 20B builder eventually completed after real pytest execution and publication of both requested files. Its handoff was persisted and acknowledged by another verifier. A curator produced a real proposed workflow. These results required several fixes and checkpoint resumes; they are not an uninterrupted successful end-to-end run.

**Full workflow verification is blocked by Groq's daily quota.** The observed 20B rejection reported a 200,000-token daily limit, 197,180 tokens used and a 3,977-token request. The 120B account quota had already blocked that model earlier. No automatic model substitution occurred. Independent 20B verification, semantic curator write-back, procedure activation and later-session procedure execution have not all passed. The current report deliberately contains `passed: false`.

Verification tasks were marked blocked, test-owned containers stopped, and artifact/checkpoint volumes retained. Other queued browser fixtures were cancelled before restoring the normal local worker. The full report is `data/collective/live-verification.json`; the pre-finalization report is preserved alongside it. After increasing the account limit or allowing quota to replenish, `.\scripts\verify-live.ps1 -Resume` resumes real persisted work. Procedure reuse has its own driver, `scripts/verify-procedure-reuse.py`, which refuses to run without a passing team report.

The latest local infrastructure suite passed **22 tests**, with **1 opt-in provider test skipped**. The production frontend build and authenticated Playwright workspace flow passed. A separate real-artifact browser test passed download checksum validation, cross-tenant denial, artifact rendering and graph rendering. A fresh actual API process restart preserved the session, conversation message and graph retrieval. The local app remains dependent on real provider quotas.

The separate `scripts/verify-live-memory.py` run passed using **20B + Safeguard** after tightening Mem0's correction policy: the initial Noor ownership fact was extracted; the correction produced the active Priya ownership fact; the old fact became `superseded`; and a task depending on it became `stale`. The first attempt had deleted the old fact without retaining its replacement and was correctly reported as failed. The new policy instructs the real model to preserve explicit replacements; no replacement fact is synthesized in application code. Report: `data/collective/live-memory-verification.json`.

## Fixes implemented during the Safeguard/20B run

- Versioned Safeguard policy with typed boolean decisions and category choices; tenant permissions and sandbox restrictions remain server checks.
- Shared PostgreSQL token reservations, persisted tokenizer assets, explicit daily-quota errors and bounded retries without substitution.
- Role-filtered optional-tool retrieval, small role-specific core tools and persisted capability discoveries.
- Current execution ledgers and phase guidance, repeated-write protection, fresh-test requirements and matching publication hashes for tracked files.
- Passing Python test evidence distinguished from ordinary successful shell commands; procedure activation uses a verifier's own actual passing tests.
- Separate memory UUID, artifact UUID and integer test-event fields in handoffs, with real ledger-based resource attachment.
- Checksum-validated handoff/procedure files prepared in private sandboxes; preparation is recorded as runtime resource delivery.
- Sourced curator write-back is required; graph-backed proposal state is available to avoid blindly duplicating procedures.
- Mem0 provider failures propagate even when the library catches an exception; partial output is not accepted as successful extraction.

These changes compile and pass the local regression checks. The quota-blocked stages above remain unverified against the complete live provider workflow.

## Earlier Groq / Kev / LangSearch run

Real providers and local model weights were used. No mock decisions, synthetic search results, or substitute models were introduced.

## Provider configuration

- Agents and memory extraction: Groq `openai/gpt-oss-120b`, explicitly selected instead of Anthropic.
- Decisions: local `jaredpalmer/kev-0.8b@v1.0`, CPU PyTorch, served at `127.0.0.1:8009`.
- Search: LangSearch, with an atomic PostgreSQL budget of at most 1,000 attempted requests per UTC database day, shared by local workers.
- Secrets are in the ignored `.env.collective`. The project file takes precedence over unrelated inherited host keys.

Kev source revision: `dd375f27fd61486c52204205e10a0d2e10f3b34a`. The 1,746,942,600-byte Qwen base-weight shard was checked against its official SHA-256: `c2b1e5a17d9c1e27685d92ed9b382911ebb99955ecd89052d1721241adfbab6c`.

## Passed

- Groq authentication and structured relation extraction.
- Direct Mem0 extraction with the supplied Groq key produced the sourced Maya ownership fact. A subsequent correction produced a real DELETE of the old fact and ADD of the new Arun ownership fact. This direct adapter check does not bypass the failed admission stage in the integrated application.
- A real DeepAgents researcher retrieved the owner of ORCHID, stated Maya's name, cited the correct persisted memory ID, and saved its completion.
- A real builder wrote `calculator.py` and `test_calculator.py`, executed pytest successfully in Docker, published both artifacts with checksums, and created a durable handoff.
- An independent Groq verifier resumed the handoff from its persisted checkpoint, copied both artifacts into its own sandbox, and executed pytest: **1 passed**, successful check event **323**. The builder's successful check event was **268**.
- LangSearch returned five actual results. Two requests had been reserved during this verification at the time of writing.
- Local Kev loaded real weights, served its compatible API, and produced typed decisions in approximately 5–6 seconds for the short fixtures.
- The actual injection-ingestion pipeline quarantined the obvious instruction asking for environment API keys.
- Session authentication, conversation history, and graph retrieval survived an actual API process restart.
- Infrastructure suite: **18 passed, 1 credential-gated test skipped**. HTTP isolation checks and the real browser workflow passed.

## Failed: Kev admission quality under the existing policy

Fixture: “Maya owns project ORCHID. Its delivery deadline is Friday at 14:00 UTC.”

Kev returned admission probability **0.4755**, below ENGRAM's existing **0.65** threshold. The observation was archived as `episode_only`; no semantic facts were produced through the integrated pipeline. The category was `critical`, but that does not override admission.

For an obvious instruction injection, the suspicious probability was **0.7478**. This passed that fixture's quarantine threshold, but it is not evidence that the small checkpoint provides broad injection protection.

The earlier full workflow script stopped at the failed fact-admission assertion. Its historical report is in ignored runtime file `data/collective/kev-live-verification.json`; current attempts use `data/collective/live-verification.json`. The threshold was not reduced to force a pass.

## Practical consequence

Groq and LangSearch are usable provider alternatives. Kev is API-compatible and runs locally, but this small checkpoint is not a verified drop-in decision replacement under ENGRAM's current policy. It needs domain-specific evaluation and calibration, or a more suitable checkpoint/provider, before autonomous memory admission can be considered ready.

Consequently, a complete coordinator-to-curator workflow, autonomous semantic consolidation/write-back, and automatic procedure verification/reuse have not all passed the integrated provider run. Service health means the endpoint is running; it does not establish decision quality. Triton and public deployment remain deferred.

## Fixes found through live execution

- Adapted Mem0's pinned provider registration to its actual validation contract.
- Initially separated Groq tool execution from structured final-report formatting. The current runtime constructs identifiers directly from the execution ledger instead of asking another model call to format them.
- Added bounded retries for model-generated malformed tool calls; rejected calls never execute.
- Bounded serialized memory metadata and separated tool descriptions from factual retrieval.
- Persisted discovered capabilities and added scoped exact-memory reads for proposed-procedure inspection.
- Fixed duplicate FalkorDB index creation across fresh processes.
- Corrected PowerShell process timestamp comparisons and managed embeddings through a foreground WSL process.
- Delayed worker claims until local embeddings and Kev are serving.
