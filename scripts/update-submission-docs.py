"""Refresh submission prose only from completed, measured live evidence."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / "outputs/submission-live/evidence.json").read_text(encoding="utf-8"))
assert r["passed"]
c = r["comparison"]
b, u = c["trials"]["baseline"], c["trials"]["reuse"]
s = c["signed_savings"]
table = (
    "| Measured metric | Exact artifact bundle | Verified procedure | Baseline minus reuse |\n"
    "| --- | ---: | ---: | ---: |\n"
    f"| Observed provider calls | {b['provider_calls_observed']} | {u['provider_calls_observed']} | {s['provider_calls_observed']:+d} |\n"
    f"| Observed provider tokens | {b['model_tokens_observed']:,} | {u['model_tokens_observed']:,} | {s['model_tokens_observed']:+,d} |\n"
    f"| Elapsed seconds, including queue/startup | {b['elapsed_seconds']:.3f} | {u['elapsed_seconds']:.3f} | {s['elapsed_seconds']:+.3f} |\n"
)
method = (
    "Both arms used Groq `openai/gpt-oss-20b`, the same two artifact versions and the same ten-test pytest suite in fresh restricted containers. "
    "The baseline received known correct files; reuse loaded the active, independently verified version 1 procedure. "
    "Both used automatic owner-authorized memory scope and disabled automatic post-run curation. "
    "Counts include recorded Groq-adapter agent, memory and admission requests attributed to each verifier. "
    "Positive signed differences favor reuse; negative values mean overhead. This is one baseline-first pair with warm shared services, not a randomized performance study or a code-generation savings estimate. "
    "Failed calls can have unknown billed tokens; SDK-internal retries are not counted individually."
)
story = (
    "The real DeepAgents coordinator dispatched researcher and builder work, published two files, acknowledged a handoff, completed independent checks and retained an artifact-bound procedure. "
    "The initial model was Qwen; after its daily token quota was exhausted, the user explicitly authorized Groq 20B to finish. "
    "An agent first recommended routing ORCHID approval to Maya. A supplied newer source named Priya. "
    "FalkorDB dependencies identified old readers and fenced stale work. After an actual API and worker restart, the repaired replacement plan completed and recommended Priya without repeating documentation research or rebuilding code. "
    "The same private session, two conversation messages, both artifact hashes and 40 original coordinator checkpoint rows survived."
)
limits = (
    "This was a recovered, multi-attempt execution, not a first-attempt or all-Qwen pass. "
    f"The evidence retains {len(r['excluded_comparison_pilots'])} excluded debug comparison pilots and the stopped first replan; only the final matched pair enters the table. "
    "The correction was supplied explicitly, not autonomously discovered. Conservative context dependencies invalidated all eight historical fixture runs, so minimal semantic impact analysis is not demonstrated. "
    "The earlier exact 800-character Qwen tool-argument probe still failed (496 received); its cause is unresolved. "
    "The public Cloudflare demo remains laptop-dependent; permanent hosting is pending. The existing film predates this validation."
)
section = (
    "## Completed live evidence: 18 October 2026\n\n" + story + "\n\n" + table + "\n" + method + "\n\n"
    "Backend regression: **34 passed, 1 opt-in credential-dependent test skipped**. "
    "This suite result is separate from the actual credential-backed live scenario.\n\n" + limits + "\n\n"
    "Inspect the sanitized report and exact event IDs at `/evidence/live/` on the running app. "
    "Portable files: `outputs/submission-live/index.html` and `evidence.json`. "
    "Reproduction and scope: [LIVE-DEMO.md](LIVE-DEMO.md).\n"
)


def write(relative, text):
    (ROOT / relative).write_text(text, encoding="utf-8", newline="\n")


write("docs/SUBMISSION.md", """# ENGRAM Collective: The Release That Remembers

**ENGRAM Collective is a team of AI agents that shares persistent graph memory, coordinates work, and traces how changing knowledge affects its decisions.** Built on ENGRAM, LangChain DeepAgents and FalkorDB for Track 2: Agent Memory and Coordination.

## One memorable workflow

An engineering team prepares the ORCHID release. A researcher finds a source, a builder creates a capacity calculator, a separate verifier runs its actual tests, and a curator turns the result into a sourced, artifact-bound procedure. A changed approval owner then forces a traceable decision revision across a process restart.

""" + section + """
## Why the graph changes the action

`Task → DEPENDS_ON → Maya fact` records which context the agent read. `Priya fact → SUPERSEDES → Maya fact` preserves the correction. FalkorDB traversals find readers; PostgreSQL expands task dependencies and fences their leases. The completed replacement task retains `REPLANS` links to old work and a dependency on the new fact. Its output changes the approval route to Priya. The graph determines invalidation and supplies the replacement evidence.

Semantic similarity alone does not identify consumers of a specific old fact version. Dependency recording must still be complete, and automatic startup context currently records conservative dependencies.

## Three-minute judge walkthrough

| Time | Show | Evidence |
| --- | --- | --- |
| 0:00–0:25 | One ORCHID objective and specialist tasks | Real dispatch and acknowledged handoff |
| 0:25–0:50 | Calculator, tests and active procedure v1 | Two hashes, independent checks, ten tests |
| 0:50–1:40 | Maya to Priya correction and revised recommendation | Exact dependency and replan edges, completed plan |
| 1:40–2:05 | Restart receipts and retained history | Actual process identities and durable state |
| 2:05–2:40 | Matched live comparison | Actual call, token and elapsed-time receipts |
| 2:40–3:00 | Security boundaries and limitations | Enforced controls separated from model judgments |

## Track 2 coverage

- Episodic conversation and outcome history, semantic facts with source corrections, and procedural tools and versioned workflows.
- PostgreSQL history and checkpoints plus FalkorDB memory survive process restarts.
- Role-specific specialists share authorized state and hand off checked artifacts.
- Leases, serialized claim resolution and database concurrency checks protect coordination. No production-scale throughput claim is made.
- Tenant, project and user visibility controls apply to retrieval, explicit reads, artifacts and execution.

## Security and delivery

Docker enforces no network, non-root execution, a read-only root, dropped capabilities and bounded CPU, memory, processes and command time. It shares the host kernel and currently lacks volume disk quotas. Admission uses real Safeguard judgments, with typed validation and no accept-on-error decision; code separately enforces authorization and leases. Source timestamps select claims under a policy, not proof of source authority.

The browser creates a private session without signup. Each user supplies encrypted provider keys in Profile & settings. The demo owner's credentials are not a visitor fallback. The public static evidence contains no session cookie or API key.

See [security boundaries](SECURITY-BOUNDARIES.md), [measurement method](REUSE-MEASUREMENT.md) and [delivery status](DEMO-STATUS.md). This package is prepared locally; no hackathon submission or repository push is implied.
""")

for relative, heading in (
    ("docs/DEMO-STATUS.md", "ENGRAM Collective delivery status"),
    ("docs/PROVIDER-VERIFICATION.md", "Provider verification"),
):
    p = ROOT / relative
    old = p.read_text(encoding="utf-8")
    marker = "\n## Historical records\n"
    historical = old.split(marker, 1)[1] if marker in old else old
    write(relative, f"# {heading}: 18 October 2026\n\n" + section + marker + "\nThe following records describe earlier fixtures and their status at the time. They are retained for provenance.\n\n" + historical)

p = ROOT / "docs/REUSE-MEASUREMENT.md"
old = p.read_text(encoding="utf-8")
old = old.replace("That experiment remains deferred while Groq is unavailable.", "The single live pair below is now available; repeated paired evaluation remains future work.")
marker = "\n## Live-model comparison: 18 October 2026\n"
write("docs/REUSE-MEASUREMENT.md", old.split(marker)[0] + marker + "\n" + table + "\n" + method + "\n\n" + limits + "\n\nThe older five-pair, zero-inference experiment above remains a separate measurement. Raw live receipts are in the sanitized evidence export.\n")

p = ROOT / "docs/LIVE-DEMO.md"
old = p.read_text(encoding="utf-8")
marker = "\n## Recorded completed result\n"
write("docs/LIVE-DEMO.md", old.split(marker)[0] + marker + "\n" + table + "\n" + method + "\n\n" + limits + "\n")

p = ROOT / "README.md"
old = p.read_text(encoding="utf-8")
old = old.replace("separates this intended complete workflow from the infrastructure evidence already verified.", "presents the completed live workflow, exact graph evidence and measured reuse comparison.")
paragraph = next(line for line in old.splitlines() if line.startswith("Current infrastructure checks pass")) if "Current infrastructure checks pass" in old else None
if paragraph:
    old = old.replace(paragraph, "**18 October live demo completed with recovery:** the actual team produced independently checked artifacts and an active procedure, survived an API/worker restart, and changed approval routing from Maya to Priya using the corrected graph. Qwen started the work; the explicitly authorized Groq 20B model completed it. The matched live comparison and exact receipts are in [the live evidence guide](docs/LIVE-DEMO.md) and `/evidence/live/` on the running app. Backend regression: **34 passed, 1 skipped**. Single-pair results, conservative invalidation and earlier fidelity/debug failures are disclosed in [delivery status](docs/DEMO-STATUS.md).")
write("README.md", old)

p = ROOT / "docs/blog/engram-collective.md"
old = p.read_text(encoding="utf-8")
old = old.replace("*Engineering notes · 16 October 2026 · Built for Graph Hacks Track 2*", "*Engineering notes · Updated 18 October 2026 · Built for Graph Hacks Track 2*")
old = old.replace("A researcher finds its approval owner, a builder creates a capacity-checking artifact", "A researcher finds official documentation, a builder creates a capacity-checking artifact")
old = old.replace("The local build answers that question with working infrastructure and inspectable graph evidence. Its full autonomous Qwen workflow remains unverified after a daily token limit and a separate tool-argument fidelity failure. The evaluations below distinguish model-backed partial runs from controlled infrastructure experiments.", "The local build now has a completed live team scenario across a real restart, with recovery and an explicitly authorized Qwen-to-20B model change. It also has inspectable graph evidence and matched model-backed reuse measurements. Earlier infrastructure experiments below remain labeled separately.")
old = old.replace("The intended complete workflow is to preserve both claims", "The completed live workflow preserves both claims").replace("That revised plan should survive a restart and reuse an appropriate verified artifact version.", "A replacement plan completed after a real restart, and a separate session reused the exact independently verified procedure version.")
old = old.replace("preserves both claims, select the current observation under an explicit policy, identify tasks that consumed the old fact, and create a revised plan", "preserves both claims, selects the current observation under an explicit policy, identifies tasks that consumed the old fact, and creates a revised plan")
old = old.replace("In the controlled local scenario, the claim resolution, invalidation and creation of a replacement plan have passed against real services. The replacement plan is explicitly **blocked**, rather than presented as an autonomous execution that completed. This distinction keeps the example useful without turning a scripted experiment into an agent capability claim.", "The earlier 16 October infrastructure fixture left its replacement plan blocked. The separate 18 October model-backed scenario completed its repaired replacement plan. These fixtures retain separate IDs and reports; the older blocked fixture has not been relabeled as a success.")
old = old.replace("## Restart persistence and current evaluation", "## Earlier restart persistence and evaluation")
old = old.replace("A model-backed cost experiment still needs matched objectives, equal acceptance tests, repeated trials and accounting for agent, memory and policy requests.", "The new live pair below adds matched objectives, equal tests and actual provider receipts; repeated trials are still needed.")
old = old.replace("These results establish persistence across separate fixtures, not completion of one autonomous story across a restart.", "These 16 October results establish persistence across separate fixtures. The 18 October scenario below adds one completed story across a restart.")
old = old.replace("Earlier partial model-backed runs produced real artifacts, a handoff and passing independent checks. They are retained as partial evidence. They do not turn the complete workflow into a pass.", "These older partial runs remain historical evidence. The separate 18 October result below records the completed recovered workflow.")
old = old.replace("The next milestone is a repeatable full autonomous run across a real restart, followed by a corrected fact and an executed revised plan. Before that, the long tool-argument fidelity failure needs resolution; additional quota alone is not a demonstrated fix.", "The next milestone is repeating the completed workflow from a clean start without manual recovery, followed by randomized multi-pair cost measurements. The long Qwen tool-argument fidelity failure still needs investigation; additional quota alone is not a demonstrated fix.")
old = old.replace("Triton optimization and public deployment remain deferred.", "Triton optimization and permanent hosting remain deferred. A temporary public demo is available while its host laptop is online.")
old = old.replace("Evaluation reflects the local build on 16 October 2026.", "The original evaluation reflects 16 October; the new live section records 18 October 2026.")
live = "## Completed live scenario: 18 October 2026\n\n" + story + "\n\n" + table + "\n" + method + "\n\n![Actual completed replacement plan after the correction and restart](assets/live-causal-graph.png)\n\n![Actual matched live provider comparison, with signed differences](assets/live-reuse-comparison.png)\n\n" + limits + "\n\nThe updated backend suite passed **34 tests with one opt-in credential-dependent test skipped**. Exact run, check and provider-receipt IDs are available in the companion sanitized evidence.\n\n"
if "## Completed live scenario: 18 October 2026" not in old:
    old = old.replace("## What comes next", live + "## What comes next")
write("docs/blog/engram-collective.md", old)

p = ROOT / "docs/blog/build.py"
old = p.read_text(encoding="utf-8").replace("Local engineering results · 16 October 2026 · Latest complete autonomous workflow remains unverified.", "Engineering results · Updated 18 October 2026 · Recovered live scenario and single-pair measurements included.")
write("docs/blog/build.py", old)
write("docs/blog/evaluation-live.json", json.dumps(r, indent=2) + "\n")
write("docs/blog/README.md", """# ENGRAM illustrated blog package

Read `index.html` for the styled article or edit `engram-collective.md` for publication. Updated 18 October 2026 with the recovered live workflow and actual single-pair provider measurements. The previously created private ChatGPT Page remains an older draft and has not been updated by this local build.

## Included

- Original branded diagrams, Mermaid flowcharts and measured provider-free evaluation chart.
- Actual app captures, including the completed correction/replan and matched live comparison.
- `evaluation-live.json`: sanitized live evidence with exact run, check and provider-receipt IDs.
- `evaluation-data.json` and `evaluation-trials.csv`: the separate older five-pair zero-inference experiment.
- Portable HTML, editable article, local fonts and licenses.

## Publish

1. Publish the matching code revision separately. This package does not push the repository.
2. Paste the article into your blog editor and upload its referenced assets.
3. Keep recovery history, measurement scope, signed results and security boundaries beside the claims.
4. Preview and publish from your account. No external blog publication or hackathon submission is implied.

## Rebuild

Use `.venv-video/Scripts/python.exe docs/blog/build.py` for figures and HTML. Fresh live screenshots come from `frontend/e2e/submission-live.spec.ts` with `ENGRAM_LIVE_DEMO_UI=1`, after the live report passes. Preserve its screenshot files before another Playwright run. The old `render-assets.mjs` captures the older infrastructure fixture, so it must not overwrite the newer screenshots as live evidence.

The earlier chart and evaluation remain historical measurements. A single matched live pair does not establish reliable cost or latency savings, and no first-attempt workflow success is claimed.
""")
print(json.dumps({"updated": True, "comparison": {"baseline": b["run_id"], "reuse": u["run_id"]}}))
