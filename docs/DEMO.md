# ENGRAM ENGINE: a team that remembers

Lead with **The Release That Remembers**, the single ORCHID correction-and-revision story in [the submission script](SUBMISSION.md). The causal view exposes live FalkorDB dependency witnesses; the procedure view shows controlled baseline/reuse measurements separately from prior observational deltas. See [measurement scope](REUSE-MEASUREMENT.md) and [security boundaries](SECURITY-BOUNDARIES.md). The existing film predates these new panels and remains an architecture walkthrough.

The local demo combines real LangChain DeepAgents, Qwen `qwen/qwen3.8-27b` on Groq, Safeguard admission, Mem0, FalkorDB, PostgreSQL, Qdrant, GGUF embeddings, LangSearch and Docker sandboxes. Triton remains deferred. No substitute model or simulated service is selected when a dependency fails.

## New evidence surfaces

**Causal timeline:** correcting a graph memory follows `Task → DEPENDS_ON → Memory`, expands affected coordinators and dependent tasks, fences old leases and marks results stale. A revision action creates an idempotent new coordinator task with `REPLANS` edges and a dependency on the corrected memory. Prior tasks remain inspectable. Replanning is explicit; arbitrary edits do not silently trigger new agent spending.

**Competing claims:** agent tools `claim_submit` and `claims_resolve` preserve immutable claim rows, claimant identities, source-memory IDs, recorded source observation timestamps and graph conflict edges. The resolver serializes decisions per tenant/project/subject/predicate. Its policy selects the latest *active source observation*. Equal-time contradictory values remain unresolved and the previous selected fact becomes disputed. This policy does not authenticate an external document or establish universal truth. A caller cannot change a source's timestamp while submitting a claim.

**Versioned procedures:** proposals receive a family/version number and a manifest of actual artifact IDs and SHA-256 hashes. Preconditions include the configured sandbox image, no-network execution, exact artifact hashes and declared workflow conditions. A separate agent run must execute fresh passing tests on the bound files; the runtime reads and hashes the actual verifier sandbox files before activation. Procedures load their manifest, rather than whichever file happens to have the same name today. Declared natural-language conditions remain a verifier responsibility; they are not formal predicates.

**Measured reuse:** every active-version reuse records its own run, execution evidence and actual model token usage. The UI compares source execution with reuse using signed deltas. Zero and negative savings are valid results. This is an observed run comparison, not a controlled speed benchmark. Independent execution does not prove complete test coverage.

Token metrics count DeepAgents model responses, excluding the separate Mem0 and policy-model calls. Wall time comes from persisted start/completion timestamps. Task instructions are preserved as episodes; they are not promoted directly into established world facts.

**Provider coordination:** token requests share a PostgreSQL budget and FIFO queue. A coordinator yields after observing pending children instead of continually polling them with paid model calls. Successful exact-query web responses are retained per run for subsequent reuse. A crash between an external operation and recording its receipt can still repeat that operation; ENGRAM does not claim distributed exactly-once execution.

## Reproduce

1. Start services with `scripts/start-local.ps1` and configure real provider keys in the ignored `.env.collective`.
2. Run `scripts/verify-live.ps1` for the real team, web research, sandbox artifacts, handoff, independent checks and Mem0 write-back. `-Resume` resumes the saved fixture and checkpoints after correcting a visible failure.
3. `scripts/demo-restart-state.py prepare` records the current fixture's session, graph IDs, file hashes and checkpoint threads. Restart the actual API and agent process, then run the same script with `verify`. Its cookie-bearing state file stays ignored in `data/collective`.
4. With the normal worker paused, `scripts/verify-causal-demo.py prepare` runs two real claimant agents, resolves their sources, and confirms that a prior dependent task becomes stale. After restart, `complete` loads that persistent evidence and executes the revised plan. These commands require the team report to have passed first.
5. `scripts/verify-live.ps1 -Reuse` independently executes an active artifact-bound procedure in a new agent session.
6. `scripts/verify-advanced.ps1 -Stage versions` creates a real artifact upgrade with reserved release headroom, proposes a new version explicitly on the user's behalf and requires a separate agent to activate it with fresh tests. Repeat `-Reuse` to measure the highest active version.

The verification scheduler uses the same `claim`, heartbeat, `execute_run`, checkpoint and sandbox implementation as the normal worker. Pause the normal worker when using that scheduler so the two do not claim each other's fixture tasks. Restore the normal worker afterward with `scripts/start-local.ps1`.

## Film

`video/engram-film` contains a nine-scene, 1920×1080 motion-graphics project. `TIMING.json` records measured local Kokoro narration durations and hashes (157.033333 seconds for the current cut). Captions are authored sentence groups aligned proportionally to measured clips; they are not ASR word timestamps. `frontend/capture-demo.mjs` captures the authenticated local app without mocked routes. The current export uses explicitly identified earlier partial Qwen captures and the direct-tool infrastructure scenario; see `DEMO-STATUS.md`. It does not claim a successful autonomous end-to-end run.

The film's HTML, design brief, storyboard, narration script, assembly script and subtitle file remain editable. Start its local preview with `npx hyperframes@0.8.162 preview --port 3017 --background --no-open`; render with the pinned CLI after its `check` gate passes.

The generated memory-loop logo has an editable geometric production SVG in `assets/brand/engram-mark.svg`. Matching copies serve the app, browser icon and film. Its manifest records matching hashes; generated concept artwork is preserved alongside it. New captures include the actual updated app branding.

Motion guidance was downloaded from [motion-graphics-skills](https://github.com/imMamdouhaboammar/motion-graphics-skills) (`motion-design`, `video-review-loop`) and [HyperFrames](https://github.com/heygen-com/hyperframes). Fonts come from the Google Fonts DM Sans and Manrope repositories. The local speech model is the official [Kokoro ONNX model-files-v1.0 release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0). Runtime evidence is local; no public deployment or submission is performed by these commands.
