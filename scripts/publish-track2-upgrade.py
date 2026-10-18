"""Extend the public evidence with sanitized, measured Track 2 upgrades."""
import hashlib
import html
import json
import runpy
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collective.settings import base_settings, configured  # noqa: E402

source = ROOT / "data/collective/track2-upgrade"
lab = json.loads((source / "reliability.json").read_text())
series = json.loads((source / "live-series.json").read_text())
mission = json.loads((source / "memory-mission.json").read_text())
assert lab["passed"] and series["passed"]
evidence = {
    "title": "ENGRAM ENGINE: memory contracts, durable handoffs and measured reuse",
    "reliability_lab": {k: lab[k] for k in ("method", "provider_calls", "writes", "reads", "correction", "duplicate_delivery", "recovery", "processes_before", "processes_after", "updated_at")},
    "live_series": {k: series[k] for k in ("passed", "status", "model", "code_sha256", "procedure_id", "manifest", "protocol", "orders", "pairs", "summary", "median_paired_savings", "limitations", "updated_at")},
    "extra_fresh_mission": {k: mission[k] for k in (
        "passed", "phase", "model", "root_run", "initial_model", "model_changes", "recovery_attempts",
        "previous_attempts", "completed_team", "writebacks", "handoffs", "uses", "parallel_snapshot",
        "root_checkpoint_rows", "root_checkpoint_rows_after", "conversation_messages_after", "processes_before", "processes_after", "corrected_source", "affected_runs", "affected_states",
        "correction_event", "revised_plan", "mem0_correction", "revised_action", "preserved_verifier_runs",
        "replan_edges", "execution_receipts", "correction_provider_receipts", "final_runtime_digest",
    ) if k in mission},
    "limitations": [
        "The load and recovery lab directly invokes real production functions. It makes zero provider calls and is not autonomous-agent reasoning or model throughput.",
        "Four alternating live pairs are a small local sample. One latency pair was slower; no general latency or cost guarantee is made.",
        "The exact four-pair measured runtime is preserved with its source digest. Later private-reference protection, procedure binding and coordinator context/scope recovery were hardened separately.",
        "Context token counts describe memory projections, not the entire model request. Explicit full reads are separately accounted. Fingerprints are hashes, not cryptographic signatures.",
        "Handoff delivery is idempotent within this application. Exactly-once external side effects and distributed SQL/graph transactions are not claimed.",
        "Local CPU embeddings dominate semantic-write latency. The measured 16-write trial is not a FalkorDB performance benchmark.",
        "The earlier Qwen-to-20B scenario required recovery. The extra mission retains unsuccessful 20B quota and 120B scope/budget attempts; it is not labeled as first-attempt success. Read its explicit current phase and passed flag.",
        "Temporary public hosting depends on the laptop. Permanent hosting and publication of the matching source repository remain pending.",
    ],
    "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source / "reliability.json", source / "live-series.json", source / "memory-mission.json")},
}
verification_file = ROOT / "outputs/submission-live/track2/verification.json"
if verification_file.is_file():
    evidence["verification"] = json.loads(verification_file.read_text())
if mission.get("blocker"):
    evidence["extra_fresh_mission"]["blocker"] = mission["blocker"]
text = json.dumps(evidence, indent=2, default=str)
for name in ("groq_api_key", "anthropic_api_key", "langsearch_api_key", "tavily_api_key", "jev_api_key"):
    value = getattr(base_settings, name)
    assert not configured(value) or value not in text, "Credential found; export refused"

runpy.run_path(str(ROOT / "scripts/publish-submission-evidence.py"), run_name="__main__")
out = ROOT / "outputs/submission-live"
(out / "track2-upgrade.json").write_text(text, encoding="utf-8")
esc = html.escape
summaries = series["summary"]
rows = "".join(
    f"<tr><th>{label}</th><td>{summaries['baseline'][key]:,.1f}</td><td>{summaries['reuse'][key]:,.1f}</td><td>{series['median_paired_savings'][key]:+,.1f}</td></tr>"
    for key, label in (("provider_calls", "Provider calls"), ("known_tokens", "Observed tokens"), ("elapsed_seconds", "Elapsed seconds"))
)
trial_rows = "".join(
    f"<tr><td>{p['pair']}</td><td>{' â†’ '.join(p['order'])}</td><td>{p['signed_savings']['known_tokens']:+,}</td><td>{p['signed_savings']['elapsed_seconds']:+.3f}</td></tr>"
    for p in series["pairs"]
)
capsule_receipt = next(e["payload"] for p in series["pairs"] for e in p["trials"]["reuse"]["passport_events"] if e["payload"]["mode"] == "startup_references")
if mission["passed"]:
    mission_section = f"""<section><h2>New 120B team workflow completed across a restart</h2>
<p>The new private-memory team used {esc(mission['model'])}. A verifier reused the checked calculator, a researcher handed sourced approval work to a curator, and real Mem0 write-back completed. After restarting both app processes, a supplied correction changed Maya to Priya, Mem0 reconciled the derived approval knowledge and the replacement plan returned Priya.</p>
<p>The graph returned {len(mission['affected_runs'])} affected approval-context task references, including prior attempt history; actual resulting statuses are retained in the JSON. The {len(mission['preserved_verifier_runs'])} unrelated calculator verifier remained completed. The original root retained {mission['root_checkpoint_rows']} checkpoint rows before restart. Exact packets, acknowledgements, process IDs and model/check receipts are in the JSON.</p>
<p>Earlier quota and scope/budget attempts remain recorded. This is a completed recovered workflow, not a first-attempt success. The four-pair savings above remain measurements of Groq20B, not estimates of 120B performance.</p></section>"""
else:
    mission_section = f"""<section><h2>Additional team workflow: {esc(mission['phase'])}</h2><p>The earlier completed scenario remains valid. The extra workflow currently uses {esc(mission['model'])}; its current passed flag is false. Quota, rejected scopes and retries remain in its history. It is not counted as completed.</p></section>"""
if mission["passed"] and (out / "track2/track2-120b-causal-action.png").is_file():
    mission_section = mission_section.replace("</section>", '<figure><a href="track2/track2-120b-causal-action.png"><img src="track2/track2-120b-causal-action.png" alt="Actual 120B replacement plan changes ASTER approval from Maya to Priya after restart" style="width:100%;max-height:700px;object-fit:contain"></a></figure></section>')
section = f"""
<section><p class="kicker">NEW / TRACK 2 MEMORY AND COORDINATION</p><h2>Remember less. Preserve the exact reason.</h2>
<p>Final local regression: 40 backend checks passed; one optional provider test skipped. Eight local browser checks and one public HTTPS browser check passed. The provider-backed 120B workflow and four live 20B pairs are documented separately below.</p>
<p>Tasks can bind to explicit memory references and pinned obligations. A compact memory capsule carries actionable instructions, versions, source IDs and artifact hashes. Durable passports record the selected revisions and context fingerprint. A correction racing with context preparation is rejected before that stale snapshot reaches the next model step.</p>
<details><summary>Inspect an actual startup passport</summary><pre>{esc(json.dumps(capsule_receipt, indent=2))}</pre></details>
<h3>Four real matched live pairs, eight successful verifier sessions</h3><p>Groq {esc(series['model'])}; identical bound files and ten passing pytest cases per session. Alternating order, no discarded warmup, zero failed adapter receipts; SDK-internal retry attempts are not individually counted. Automatic post-run curation is disabled in both arms.</p>
<div class="scroll"><table><tr><th>Metric</th><th>Baseline median</th><th>Capsule reuse median</th><th>Median paired savings</th></tr>{rows}</table></div>
<p>50% fewer provider calls and about 20.5% fewer median tokens. Three latency pairs favored reuse; one was slower. The median paired time difference was {series['median_paired_savings']['elapsed_seconds']:.3f} seconds. This is stronger evidence for call/token efficiency than for general speed.</p>
<details><summary>Every paired observation</summary><div class="scroll"><table><tr><th>Pair</th><th>Order</th><th>Token savings</th><th>Time savings, s</th></tr>{trial_rows}</table></div><p>{esc(series['protocol'])}</p></details></section>
<section><h2>A correction changes one consumer, not all sixteen</h2>
<p>In the controlled real-store fixture, eight competing corrections produced one committed replacement and seven stale-revision conflicts. The graph identified exactly one consumer of the changed fact. Fifteen consumers bound to other references were preserved.</p>
<svg viewBox="0 0 920 240" role="img" aria-label="One approval fact changes one dependent consumer; fifteen unrelated reference consumers are preserved" style="width:100%;height:auto"><g fill="none" stroke="#76956b" stroke-width="2"><rect x="15" y="20" width="340" height="80" rx="14"/><rect x="560" y="20" width="345" height="80" rx="14"/><path d="M355 60H560"/><rect x="15" y="145" width="340" height="80" rx="14"/><rect x="560" y="145" width="345" height="80" rx="14"/><path d="M355 185H560"/></g><g fill="#e3e8de" font-family="system-ui" font-size="19"><text x="35" y="55">Approval: Maya â†’ Priya</text><text x="35" y="82">Supplied source correction</text><text x="580" y="55">1 exact dependent consumer</text><text x="580" y="82">Marked stale; lease fenced</text><text x="35" y="180">15 other reference records</text><text x="35" y="207">Different consumed evidence</text><text x="580" y="180">15 unrelated consumers</text><text x="580" y="207">Preserved at correction time</text></g></svg>
<p>This fixture directly invokes production functions without model inference. It establishes selective dependency handling; it does not claim perfect semantic relevance for unrestricted retrieval.</p></section>
<section><h2>One handoff, even when delivery repeats</h2><div class="flow"><span>Awaiting envelope</span><span>Packet committed</span><span>Receiver becomes claimable</span><span>Revision checks</span><span>One preserved acknowledgement</span></div>
<p>20 concurrent identical delivery attempts produced one receiver and one envelope. A deliberately interrupted delivery survived a real API/worker restart, resumed into the same receiver, and retained its first acknowledgement when replayed. The fixture was then cancelled for cleanup; this is delivery/recovery evidence, not a fabricated model completion.</p>
<details><summary>Actual restart and acknowledgement receipts</summary><pre>{esc(json.dumps(lab['recovery'], indent=2))}</pre></details></section>
<section><h2>Measured store concurrency</h2><div class="scroll"><table><tr><th>Operation</th><th>Count</th><th>Concurrency</th><th>Total seconds</th><th>p95 ms</th></tr><tr><td>Direct-reference context reads</td><td>128</td><td>8</td><td>{lab['reads']['elapsed_seconds']:.3f}</td><td>{lab['reads']['p95_ms']:.1f}</td></tr><tr><td>Semantic writes with CPU embeddings</td><td>16</td><td>8</td><td>{lab['writes']['elapsed_seconds']:.3f}</td><td>{lab['writes']['p95_ms']:.1f}</td></tr></table></div>
<p>Zero operation errors. The read trial measured {lab['reads']['operations_per_second']:.1f} direct-reference reads/second on this workstation, including provenance registration. It is not full semantic-search or LLM throughput. CPU embeddings dominate write time.</p></section>
{mission_section}
<section><h2>Inspect the new working interface</h2><p>The existing Procedures page now includes compact memory passports and durable handoff receipts, without adding more navigation destinations.</p><figure><a href="track2/track2-passports-desktop.png"><img src="track2/track2-passports-desktop.png" alt="Actual persisted memory passports and recovered handoff receipts" style="width:100%;max-height:650px;object-fit:contain"></a></figure></section>
<p><a href="track2-upgrade.json">Download the new sanitized measurements, actual test output and provider receipts</a></p>
"""
page = (out / "index.html").read_text(encoding="utf-8")
marker = "<section><h2>One fact changes the action</h2>"
assert marker in page
page = page.replace(marker, section + "<h2>Earlier recovered end-to-end scenario</h2>" + marker, 1)
page = page.replace("<h2>Observed reuse comparison</h2>", "<h2>Historical single-pair comparison before capsules</h2>")
(out / "index.html").write_text(page, encoding="utf-8")
for target in (ROOT / "frontend/public/evidence/live", ROOT / "frontend/dist/evidence/live"):
    target.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "track2-upgrade.json"):
        shutil.copyfile(out / name, target / name)
    for name in ("track2-passports-desktop.png", "track2-passports-mobile.png", "track2-live-series.png", "track2-120b-causal-action.png", "track2-120b-causal-mobile.png"):
        capture = out / "track2" / name
        if capture.is_file():
            (target / "track2").mkdir(exist_ok=True)
            shutil.copyfile(capture, target / "track2" / name)
print(json.dumps({"published": True, "live_pairs": len(series['pairs']), "extra_mission_passed": mission["passed"]}))
