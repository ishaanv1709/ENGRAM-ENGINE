"""Update submission prose from passed live pairs and real final checks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = ROOT / "data/collective/track2-upgrade"
series = json.loads((data / "live-series.json").read_text())
lab = json.loads((data / "reliability.json").read_text())
mission = json.loads((data / "memory-mission.json").read_text())
mission_status = (
    "The additional Groq120B team workflow completed across an actual API/worker restart: checked procedure reuse, researcher-to-curator handoff, real Mem0 write-back and correction, and a replacement plan recommending Priya. The calculator verifier remained completed while the graph invalidated consumers of the changed approval fact. Earlier 20B quota and 120B scope/budget attempts remain recorded; this is not a first-attempt success. Four-pair savings remain Groq20B measurements."
    if mission["passed"] else
    f"The additional team workflow currently has phase `{mission['phase']}` on `{mission['model']}` and is not counted as a pass. Its earlier 20B quota failure and 120B scope/budget recovery attempts remain recorded. No substitute model response or synthetic completion was used."
)
verification = json.loads((ROOT / "outputs/submission-live/track2/verification.json").read_text())
assert series["passed"] and lab["passed"] and verification["passed"]
b, u = series["summary"]["baseline"], series["summary"]["reuse"]
savings = series["median_paired_savings"]
table = f"""| Median metric | Known-file baseline | Memory-capsule reuse |
| --- | ---: | ---: |
| Observed provider calls | {b['provider_calls']:g} | {u['provider_calls']:g} |
| Provider-reported tokens | {b['known_tokens']:,.1f} | {u['known_tokens']:,.1f} |
| Elapsed seconds including queue/startup | {b['elapsed_seconds']:.3f} | {u['elapsed_seconds']:.3f} |
"""
body = f"""## Track 2 upgrade: memory contracts and replay-safe coordination

ENGRAM now binds work to explicit memory references, loads compact context capsules and records durable memory passports with revisions, content hashes, projection fingerprints and budget accounting. Pinned obligations remain included. A reference superseded before startup is rejected; a correction racing with snapshot subscription also fails closed. Replacement plans bind the new active fact rather than treating historical quoted IDs as current instructions. Explicit full historical reads remain possible.

Handoffs use deterministic delivery identities and an unclaimable `awaiting_handoff` state. The envelope and queued transition commit together. Identical retries reuse one receiver; current evidence revisions are checked before acknowledgement, and replay preserves the first acknowledgement. Private references and parents mark tasks private before enqueue. Private-memory correction events are filtered from another member's timeline, including legacy untagged events.

### Four new live matched pairs

All eight verifier sessions passed the same ten real pytest cases with Groq `openai/gpt-oss-20b`, identical artifact hashes, alternating order and no discarded warmup. Both paths disabled automatic post-run curation. The baseline already had known correct files; this measures verification reuse, not avoided code generation.

{table}
Median paired savings: **{savings['provider_calls']:g} calls**, **{savings['known_tokens']:,.1f} observed tokens** and **{savings['elapsed_seconds']:.3f} seconds**. That is 50% fewer median calls and about 20.5% fewer median tokens. Three timing pairs favored reuse; one was slower. Four local pairs cannot establish a general cost or latency guarantee. SDK-internal retries are not separately counted; failed calls can have unknown billed tokens.

The exact measured runtime source is preserved under ignored `data/collective/track2-upgrade/measured-runtime/` with digest `{series['code_sha256']}`. Final private-reference, stale-binding, audit-event and coordinator context/scope recovery changes were tested separately; those changes are not retroactively relabeled as the source of the four-pair measurements.

### Real concurrency and crash recovery

- 128 direct-reference context reads at concurrency 8: **{lab['reads']['operations_per_second']:.1f} operations/s**, p95 **{lab['reads']['p95_ms']:.1f} ms**, zero operation errors. This includes scoped retrieval and durable provenance, not semantic-search embeddings or LLM throughput.
- 16 semantic writes at concurrency 8: **{lab['writes']['elapsed_seconds']:.3f} seconds** total, p95 **{lab['writes']['p95_ms']:.1f} ms**, zero errors. Local CPU embeddings dominate this path; it is not a FalkorDB performance claim.
- Eight competing corrections: one committed replacement, seven stale-revision conflicts. Exactly **one of sixteen** bound consumers was invalidated; fifteen unrelated consumers were preserved at correction time.
- Twenty concurrent identical handoffs: one receiver and one envelope. A deliberately interrupted delivery survived actual API/worker restarts, recovered into the same receiver, and retained one acknowledgement after replay.

These load/recovery fixtures call real production functions and services with **zero provider calls**. They are not described as autonomous model completions. The earlier recovered end-to-end team scenario remains separately documented below.

### Final checks and remaining live blocker

Final real-service regression: **{verification['backend']['passed']} passed, {verification['backend']['skipped']} opt-in provider test skipped**. Provider inference was disabled for that suite. The live pairs above use actual provider inference separately. **{verification['browser']['local_passed']} local browser checks** and **{verification['browser']['public_passed']} public HTTPS checks** passed. Production build and Ruff passed.

{mission_status} The original Qwen long-argument fidelity failure remains unresolved. Permanent hosting and publishing the matching source repository remain pending; the public tunnel depends on its laptop.

Inspect `/evidence/live/` on the running app. `track2-upgrade.json` contains sanitized receipts and every paired observation. The Procedures page exposes Memory passports, Durable handoff receipts and the repeated live comparison without adding navigation destinations.
"""


def update(relative, section, before=None):
    p = ROOT / relative
    text = p.read_text(encoding="utf-8")
    begin, end = "<!-- track2-upgrade:start -->", "<!-- track2-upgrade:end -->"
    if begin in text:
        left, rest = text.split(begin, 1)
        text = left + rest.split(end, 1)[1].lstrip("\n")
    block = begin + "\n" + section.rstrip() + "\n" + end + "\n\n"
    if before and before in text:
        text = text.replace(before, block + before, 1)
    else:
        first, rest = text.split("\n", 1)
        text = first + "\n\n" + block + rest.lstrip("\n")
    p.write_text(text, encoding="utf-8", newline="\n")


for name in ("DEMO-STATUS.md", "VERIFICATION.md", "PROVIDER-VERIFICATION.md", "REUSE-MEASUREMENT.md", "LIVE-DEMO.md"):
    update("docs/" + name, body)
submission = f"""# ENGRAM ENGINE: The Release That Remembers

**ENGRAM ENGINE is a team of AI agents that shares persistent graph memory, coordinates work, and traces how changing knowledge affects its decisions.** Built with DeepAgents and FalkorDB for Track 2.

## One memorable workflow

An engineering team prepares a release: a researcher finds a source, a builder publishes a capacity calculator, a separate verifier runs its tests, and a curator retains an artifact-bound procedure. After an actual process restart, a newer source changes the approver from Maya to Priya. FalkorDB identifies readers of the old fact, execution revisions fence stale work, and an explicitly requested replacement plan produces the corrected approval recommendation. Later sessions reuse the checked procedure instead of rebuilding its files.

The end-to-end scenario completed with recovery, starting on Qwen and finishing on the explicitly authorized Groq20B. It is not a first-attempt or all-Qwen success. Its eight conservative invalidations are preserved in the historical evidence.

## What makes the memory system distinctive

- **Memory contracts and capsules:** exact reference bindings plus pinned obligations, compact actionable procedures and durable passports containing consumed versions and fingerprints. Superseded bindings and racing stale snapshots fail closed; full historical inspection remains possible.
- **Replay-safe handoffs:** deterministic delivery identity, an unclaimable pre-envelope state, revision-bound evidence and a preserved first acknowledgement. Twenty simultaneous duplicate deliveries produced one receiver. A deliberately interrupted envelope recovered across real restarts.
- **Graph-visible impact:** the recovered agent recommendation changed Maya to Priya using current graph evidence. A separate controlled reference fixture invalidated one consumer and preserved fifteen unrelated consumers. This is precise for explicit bindings, not perfect semantic impact analysis for unrestricted recall.

## Measured live reuse, not estimated savings

Four alternating matched pairs, eight successful Groq20B verifier sessions, identical artifact hashes and ten real pytest cases in each session:

{table}
Reuse used **50% fewer median calls** and **about 20.5% fewer median tokens**. Median paired time savings were **2.001 seconds**, with one pair slower. The baseline already had known correct code, so this is verification reuse rather than code-generation avoidance. Four local pairs are not a general performance guarantee. SDK-internal retries and unknown failed-call billing are disclosed.

## Track 2 coverage and verification

| Requirement | Implemented evidence |
| --- | --- |
| Episodic, semantic and procedural memory | Conversation/outcome history, real Mem0 extraction and correction, versioned artifact-bound procedures and tool discovery |
| Persistence across sessions | Actual API/worker restart checks, retained conversations, checkpoint rows and artifact hashes |
| Shared state and handoffs | Scoped team tasks, exact evidence packets, duplicate-delivery recovery and acknowledgements |
| Concurrent reads/writes | 128 scoped reference reads and 16 semantic writes at concurrency 8, zero operation errors; CPU embeddings dominate write latency |
| User/tenant separation | Scoped graphs, private references before enqueue, shared-only reads, artifact permissions and private correction-event filtering |

Final regression: **{verification['backend']['passed']} passed, {verification['backend']['skipped']} opt-in provider test skipped**. **{verification['browser']['local_passed'] + verification['browser']['public_passed']} browser checks passed**. The load/recovery fixture uses real services without provider calls and is labeled separately from model-driven evidence.

## Honest limits

{mission_status} The exact measured source digest is retained, and final privacy/binding hardening was tested separately. The original Qwen long-argument fidelity issue remains unresolved. Existing video footage predates these new measurements.

Docker enforces non-root execution, no network, a read-only root, dropped capabilities and bounded CPU/memory/processes/time. It shares the host kernel and lacks a workspace disk quota. Safeguard is a typed model judgment; authorization and leases are enforced separately. No distributed SQL/graph atomicity, exactly-once external action or comprehensive injection protection is claimed.

Start building creates a private session. Users bring encrypted personal provider keys; visitors receive no operator fallback key. The public Cloudflare demo still depends on the laptop. Permanent hosting, matching repository publication and actual hackathon submission remain pending.

Inspect `/evidence/live/` for the public receipts. See [verification](VERIFICATION.md), [measurement method](REUSE-MEASUREMENT.md), [live protocol](LIVE-DEMO.md) and [security boundaries](SECURITY-BOUNDARIES.md).
"""
(ROOT / "docs/SUBMISSION.md").write_text(submission, encoding="utf-8", newline="\n")
short = f"""## Track 2 upgrades, verified

Memory capsules and durable provenance receipts now bind tasks to exact memory versions. Replay-safe handoffs commit their envelope before a receiver becomes claimable. Real tests cover stale-context rejection, private-reference inheritance and private correction-event isolation.

Four alternating live Groq20B pairs all passed: **4 → 2 median provider calls**, **1,782 → 1,416.5 median tokens**. Median paired time savings were **2.001 seconds**, with one pair slower. A separate real-store lab verified 128 scoped reads, 16 concurrent writes, selective invalidation of one consumer while preserving fifteen, and duplicate-delivery recovery across a real process restart.

Final regression: **{verification['backend']['passed']} passed, {verification['backend']['skipped']} skipped**; **{verification['browser']['local_passed'] + verification['browser']['public_passed']} browser checks passed**. {mission_status} See [the submission](docs/SUBMISSION.md), [verification scope](docs/VERIFICATION.md), and `/evidence/live/` on the running app.
"""
update("README.md", short, before="## Run locally")
security = """## Memory contracts, delivery and timeline isolation

Startup/retrieval capsules use a configured budget counted with `o200k_base`; this is a projection accounting unit, not native billing tokens for every supported provider. Explicit full reads are separately accounted. Durable passports retain selected IDs/revisions and hashes without treating a hash as a signature or proof of truth. Required context cannot be silently dropped to fit a budget. Superseded action bindings are rejected; historical reads still expose their superseded status.

Context snapshot validation and graph dependency attachment use the same per-memory PostgreSQL advisory locks as correction. A stale snapshot is rejected. These locks do not turn SQL and FalkorDB into one distributed transaction, and cannot cancel a provider request already in flight. Reference-focused tasks avoid unrelated broad recall; unrestricted retrieval can still record conservative dependencies.

Delivery identities deduplicate equivalent envelopes within ENGRAM. Receivers are unclaimable before envelope commit; acknowledgement validates current evidence and keeps its first timestamp. This does not establish exactly-once external tool effects. Private references, private parents and private replan evidence set task visibility before enqueue. Timeline responses recheck visibility for memory references in correction, claim and handoff events; hidden events still advance pagination/stream cursors. This is scoped hardening, not an exhaustive security audit.
"""
update("docs/SECURITY-BOUNDARIES.md", security)
article = body.replace("## Track 2 upgrade: memory contracts and replay-safe coordination", "## The next iteration: less context, stronger delivery")
article += "\n![Actual memory passports and recovered handoff receipts](assets/track2-passports-desktop.png)\n\n![Actual four-pair live comparison in the application](assets/track2-live-series.png)\n"
mission_capture = ROOT / "outputs/submission-live/track2/track2-120b-causal-action.png"
if mission["passed"] and mission_capture.is_file():
    article += "\n![Actual completed 120B replacement plan after restart, changing Maya to Priya](assets/track2-120b-causal-action.png)\n"
update("docs/blog/engram-collective.md", article, before="## What comes next")
for name in ("track2-passports-desktop.png", "track2-live-series.png"):
    import shutil
    shutil.copyfile(ROOT / "outputs/submission-live/track2" / name, ROOT / "docs/blog/assets" / name)
if mission["passed"] and mission_capture.is_file():
    shutil.copyfile(mission_capture, ROOT / "docs/blog/assets/track2-120b-causal-action.png")
(ROOT / "docs/blog/evaluation-track2.json").write_text((ROOT / "outputs/submission-live/track2-upgrade.json").read_text(), encoding="utf-8")
print(json.dumps({"updated": True, "backend_passed": verification['backend']['passed']}))
