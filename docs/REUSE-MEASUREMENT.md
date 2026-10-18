# Procedure reuse measurement

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

Run `scripts/verify-advanced.ps1 -Stage showcase` from the repository root. It pauses the normal model worker, executes five paired real-container trials and restores the worker afterward. It invokes no LLM, Safeguard, Mem0 extraction or web-search provider. Groq DNS attempts in the measurement process are explicitly rejected rather than receiving substitute responses.

## Fair comparison

The baseline receives an already known exact v2 artifact bundle. It reads those published artifacts, verifies their hashes, copies them to a fresh sandbox and runs the real ten-test suite. The reuse arm loads the active procedure through production `prepare_resources`, enforces its manifest and preconditions, copies the same bytes, runs the same suite and records the fresh verification/reuse receipt. Both arms receive the same artifact identities. No failed attempts or extra discovery calls are invented to make the baseline look worse.

Each pair alternates execution order. Timing uses a monotonic clock, from resource preparation through execution and final hash/receipt validation. This includes container startup and reuse validation overhead; it excludes task creation, task completion and container cleanup. Preparation, execution and validation durations are retained separately. All passing checks have real audit event IDs. The sample is five local pairs, not a broad latency guarantee.

## Interpret the result

- Time saved is the median of the five **paired** baseline-minus-reuse durations, in milliseconds. Positive means faster reuse; negative means overhead. Separate baseline/reuse medians and ranges are also shown.
- Tool calls are actual `RunTools` invocations, including automatic artifact preparation. Container CLI operations are not counted as agent tool calls. Execution-call and file-write counts come from persisted events.
- Model calls and model tokens come from actual `model.usage` records for those runs. Both are zero because neither arm invokes a model. Zero-minus-zero is **zero savings**, not an estimated saving.
- The execution baseline already has known correct code. This experiment measures procedure execution overhead and safety checks; it cannot establish savings from avoiding autonomous code generation, debugging, research or planning.
- Prior source-run versus reuse deltas remain available separately in the UI. They are observational comparisons and must not be mixed with these paired measurements.

The immutable raw report records each pair, ordering, task ID, exact file hashes, checks and timings. A `procedure.benchmark` audit event makes its summary available only within its authorized project. Rerunning creates new reports rather than replacing old observations; the `latest` pointer is only a convenience copy.

For a future model-backed savings claim, run multiple paired objectives with the same provider/model, limits and acceptance tests, include all model requests across agent, memory and admission paths, and publish both success rate and cost. The single live pair below is now available; repeated paired evaluation remains future work.

## Recorded local result — 16 October 2026

Event `1674`; five pairs, all ten real container trials passed the same ten-test suite.

| Path | Median elapsed | Trials | Tool calls per trial | Pytest executions | Model calls | Model tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact artifact bundle | 5.957 s | 5 | 3 | 1 | 0 | 0 |
| Verified procedure | 6.090 s | 5 | 3 | 1 | 0 | 0 |

Median paired baseline-minus-reuse time: **60.1 ms**. Baseline range: **5.897–7.229 s**; reuse range: **5.556–6.388 s**. Three pairs favored reuse; two favored the bundle. The separate reuse median was slower. These small, mixed differences do **not** demonstrate a reliable latency advantage.

**Measured tool-call savings: 0. Measured model-call savings: 0. Measured model-token savings: 0.** The demonstrated value is version-bound execution and independently verified reuse, not a proven cost reduction. No Groq request was made for this work.

## Live-model comparison: 18 October 2026

| Measured metric | Exact artifact bundle | Verified procedure | Baseline minus reuse |
| --- | ---: | ---: | ---: |
| Observed provider calls | 4 | 3 | +1 |
| Observed provider tokens | 1,823 | 5,034 | -3,211 |
| Elapsed seconds, including queue/startup | 66.407 | 53.918 | +12.489 |

Both arms used Groq `openai/gpt-oss-20b`, the same two artifact versions and the same ten-test pytest suite in fresh restricted containers. The baseline received known correct files; reuse loaded the active, independently verified version 1 procedure. Both used automatic owner-authorized memory scope and disabled automatic post-run curation. Counts include recorded Groq-adapter agent, memory and admission requests attributed to each verifier. Positive signed differences favor reuse; negative values mean overhead. This is one baseline-first pair with warm shared services, not a randomized performance study or a code-generation savings estimate. Failed calls can have unknown billed tokens; SDK-internal retries are not counted individually.

This was a recovered, multi-attempt execution, not a first-attempt or all-Qwen pass. The evidence retains 8 excluded debug comparison pilots and the stopped first replan; only the final matched pair enters the table. The correction was supplied explicitly, not autonomously discovered. Conservative context dependencies invalidated all eight historical fixture runs, so minimal semantic impact analysis is not demonstrated. The earlier exact 800-character Qwen tool-argument probe still failed (496 received); its cause is unresolved. The public Cloudflare demo remains laptop-dependent; permanent hosting is pending. The existing film predates this validation.

The older five-pair, zero-inference experiment above remains a separate measurement. Raw live receipts are in the sanitized evidence export.
