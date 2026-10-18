# ENGRAM ENGINE delivery status: 18 October 2026

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

# ENGRAM ENGINE delivery status — 17 October 2026

The walkthrough shows the implemented local project and real validation evidence. **The full autonomous Qwen team workflow has not passed.** The user chose to finish the video and report that blocker rather than supply more provider quota.

The complex-workflow extension is now implemented locally: milestone dependencies, custom specialists, bounded nested delegation, approval/event gates, budgets, source snapshots, real patch artifacts and independent file verification. The latest complete backend suite passed **28 tests with one credential-backed test skipped**. Four browser checks passed, and actual API/worker restarts preserved both a draft and a running workflow waiting for human approval, including source hashes and specialist configuration. No provider inference or external MCP effect was executed for these checks. See [the workflow guide](WORKFLOWS.md) and [verification record](VERIFICATION.md) for scope and limitations. The existing film predates this extension.

## What is implemented

- Causal correction events retain old/new facts and affected tasks. An explicit, idempotent revision creates a new coordinator plan and graph `REPLANS` links. Private affected objectives make the new plan private.
- Immutable competing claims retain their sources, recorded observation timestamps and claimant IDs. Resolution is serialized per subject. A newer active observation wins; equal-time contradictions remain unresolved and invalidate the prior selected fact.
- Procedure families have numbered versions, exact artifact IDs and SHA-256 manifests, sandbox preconditions and source checks. A different run must execute fresh checks on the actual bound bytes before activation. Reuse retains its own checks and signed usage comparison.
- Shared-only task context excludes private memories from retrieval and explicit reads, and is inherited by dispatched children. Existing automatic context behavior remains available.
- The new editable memory-loop logo is applied to authentication, the workspace sidebar, favicon, README and film. Its source and matching-asset manifest are in `assets/brand/`.

## Evidence and its limits

The **infrastructure scenario** invokes production runtime tools, real FalkorDB/PostgreSQL storage and real Docker containers directly. It makes **zero LLM calls** and does not substitute a fake model. Runtime role names in this fixture identify tool permissions and run resources; they are not a claim of autonomous model reasoning.

It passed two artifact versions, separate verifier execution for each, **10 passing tests for v2**, a fresh reuse run, concurrent source-claim submissions, Maya → Priya selection, stale dependent work and creation of a new plan. That plan is explicitly **blocked and unexecuted**. The controlled reuse measured **zero agent-model tokens and zero execution calls saved**, not a speedup. Source timestamps are recorded evidence, not authentication or proof of external truth.

An actual API/worker restart preserved two separate fixtures:

| Fixture | Session | Memories | Published file hashes | LangGraph checkpoint threads |
| --- | --- | ---: | ---: | ---: |
| Partial live Qwen run | Survived | 23 | 0 | 3 |
| Infrastructure scenario | Survived | 9 | 4 | 0 |

The second fixture also retained two active procedure versions, both concurrent claims, the selected winner and the blocked revised plan. These are persistence checks across separate fixtures, not a completed autonomous workflow.

Actual authenticated browser verification passed artifact downloads and SHA-256 checks, version/reuse display, the correction and blocked-plan display, preserved claims, the new logo, and tenant-isolation denials. Final local regression: **25 passed, 1 skipped** in 288.73 seconds. The skipped test is credential-backed. The workspace browser test and the new infrastructure-evidence browser test each passed. All six local infrastructure probes returned ready after rendering.

## Live provider blocker

Groq rejected Qwen calls with daily-quota errors. A nearby successful probe still reported **922 requests remaining**, so remaining request count did not establish sufficient token allowance. Provider selection remained `qwen/qwen3.8-27b`; no substitute was selected.

A separate fidelity probe asked for an exact 800-character tool argument and received **496 characters**, despite a `tool_calls` finish reason. The cause remains unresolved. Actual generated capacity code was incomplete; it was not published as a successful artifact. A funded key alone must not be represented as a proven fix for this issue.

Real admission/injection checks, Mem0 extraction and a Qwen researcher search completed. An earlier partial run produced actual builder artifacts, a handoff and independent passing tests. Current full-team completion, autonomous sourced curation/procedure activation, the post-restart autonomous replan and model-driven reuse savings remain unverified. Earlier partial captures are identified separately in the film's capture manifest.

One debug attempt also failed because a live schema change altered a cached PostgreSQL query result. Automatic prepared statements are now disabled for the app pool. Failed attempts and subsequent resumptions remain in the reports; they are not relabeled as first-attempt success.

## Artifacts and reproduction

- Film: `video/engram-film/renders/ENGRAM-Collective-demo.mp4`, successfully rendered: **157.033333 seconds, 1920×1080, 30 fps, H.264 + AAC stereo, 31,378,912 bytes**. SHA-256: `07d3a8cd8db4b752eefa5b57752fd8d89a79032a21fe6139d9ddc4bb24ff0d30`. Editable source: `video/engram-film/index.html`, `SCENES.json`, `SCRIPT.md`, `TIMING.json`, `subtitles.srt` and `compositions/frames/`.
- Final encoded-media audit: zero hard technical findings; 4,711 frames decoded with no detected flashes or extreme luma jumps. Sampled review inspected 37 frames across all nine scenes and eight seams, including the corrected sage intro logo. Audio measured -20.5 LUFS and -1.6 dBTP. The 85 subtle-motion/silence warning candidates were not all individually cleared; no full normal-speed audiovisual audition is claimed. Report: `video/engram-film/renders/ENGRAM-Collective-QA.json`.
- Logo: `assets/brand/engram-mark.svg`; generated concept retained alongside it.
- Ignored runtime reports: `data/collective/live-verification.json`, `qwen-tool-fidelity.json`, `film-infrastructure-evidence.json`, `demo-restart-proof.json`, `film-restart-proof.json`, `restart-process-proof.json`.
- Real capture provenance: `video/engram-film/assets/capture-manifest.json`. It distinguishes earlier partial Qwen evidence from the direct-tool infrastructure scenario.
- Infrastructure scenario: `scripts/verify-advanced.ps1 -Stage infrastructure` requires no existing fixture report and real running local services. Existing evidence is preserved rather than silently overwritten.
- Provider verification should first pass `scripts/probe-qwen-tools.py`, then a complete live workflow, followed by the separate causal restart/replan and version/reuse drivers. No further provider tests are scheduled automatically.

Procedure conditions bind a configured image tag and actual artifact hashes; the environment tag is not an immutable image digest. Natural-language conditions remain a verifier responsibility. Cross-store writes do not claim distributed atomicity or exactly-once external operations. Triton remains deferred; deployment remains local.

## Motion tooling

Downloaded and applied [motion-design](https://github.com/imMamdouhaboammar/motion-graphics-skills/tree/main/skills/motion-design), [video-review-loop](https://github.com/imMamdouhaboammar/motion-graphics-skills/tree/main/skills/video-review-loop), and [HyperFrames](https://github.com/heygen-com/hyperframes). Copies and provenance are under `video/skills/`. Narration uses the actual local Kokoro model; fonts are DM Sans and Manrope. No external media-generation credential is required.

## Focused submission improvements — no Groq

The README and `SUBMISSION.md` now center one ORCHID release-correction workflow. The causal UI exposes actual FalkorDB dependency queries, direct readers, supersession and revision edges; backend regressions check that unrelated tasks remain unaffected and hidden task IDs are excluded. The procedure UI displays the five-pair benchmark separately from source-run deltas. All ten trials passed ten checks each, with zero model calls, zero tokens and three tool calls per arm. Timing was mixed; no dependable speedup or token saving is claimed. Detailed raw reports remain in `data/collective/showcase-measurement-1674.json`.

`SECURITY-BOUNDARIES.md` and the sandbox UI distinguish Docker isolation and server authorization from probabilistic admission. Actual container inspection and bounded behavior/path probes passed. They do not establish kernel-escape resistance or Safeguard accuracy. The prior full autonomous Qwen blockers remain unchanged. The existing 2:37 video predates the new witness and paired-benchmark panels; no new render is claimed.

Validation for these changes: the three real coordination/procedure/budget regressions passed in 41.73 seconds; the expanded authenticated browser flow passed in 3.5 seconds. Browser checks exercised graph witnesses, benchmark trial counts and zero-provider metrics, security text, actual artifact hashes and cross-tenant 404 responses. Production UI build and targeted Ruff checks passed. Actual rendered screenshots were inspected for the three updated surfaces. No new full autonomous run was attempted.

## Interface clarity

The workspace now leads with the one-sentence project description and a goal form, followed by a short guide and project statistics. Navigation groups Work and Memory separately from the expandable Inspect & manage tools. All eleven feature areas remain available. Roles, memory settings, graph queries, workflow manifests and reuse history, benchmarks, file checksums and sign-in connection diagnostics are progressively disclosed. Memory filters and page headings use plain-language descriptions while retaining the underlying types and actions.

Production build and two real browser flows passed (12.1 seconds), covering all feature destinations, expandable evidence, private-context controls, file details and mobile layout. The clarity flow asserted that its interactions made no POST requests after login; no AI task or provider inference was initiated. Desktop and mobile screenshots were visually inspected.
