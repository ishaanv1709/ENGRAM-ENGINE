"""Publish only completed, sanitized live evidence. Never includes sessions/keys."""

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collective.settings import base_settings, configured  # noqa: E402

source = ROOT / "data/collective/submission-live-2026-10-18/report.json"
report = json.loads(source.read_text(encoding="utf-8"))
assert report.get("passed") is True and report["phase"] == "completed", "Live evidence is not complete"
comparison = report["comparison"]
evidence = {
    "title": "ENGRAM ENGINE: The Release That Remembers",
    "completed_at": report["updated_at"],
    "model": report["model"],
    "initial_model": report.get("initial_model", report["model"]),
    "model_changes": report.get("model_changes", []),
    "passed": True,
    "source_report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "ingestion": report["ingestion"],
    "team_before_correction": report["team_before_correction"],
    "workflow_completion_events": report["workflow_completion_events"],
    "artifacts": report["artifacts"],
    "recovery_attempts": report.get("recovery_attempts", []),
    "replan_recovery_history": report.get("replan_recovery_history", []),
    "excluded_comparison_pilots": [
        {
            "reason": p["reason"],
            "baseline_run": p["comparison"]["baseline_run"],
            "reuse_run": p["comparison"].get("reuse_run"),
            "event_ids": [e["id"] for e in p["events"]],
        }
        for p in report.get("excluded_comparison_pilots", [])
    ],
    "graph": {
        key: report[key]
        for key in (
            "direct_reader_path",
            "claims",
            "correction",
            "original_action",
            "stale_action",
            "replan_path",
            "revised_action",
        )
    },
    "restart": report["restart"],
    "persistence": report["persistence"],
    "persisted_messages": report["persisted_messages"],
    "handoffs": report["handoffs"],
    "comparison": comparison,
    "limitations": report["limitations"],
    "security_boundaries": [
        "Docker containers enforce no network, non-root execution, read-only root and resource limits; shared host kernel is not a VM boundary.",
        "Model admission is separate from code-enforced session, tenant, tool and task-lease authorization.",
        "Source observation timestamps select a claim under an explicit policy; they do not prove source authority or truth.",
        "Procedure hashes establish exact file versions; passing tests establish only the tested behavior.",
    ],
}
serialized = json.dumps(evidence, indent=2, default=str)
for name in ("groq_api_key", "anthropic_api_key", "langsearch_api_key", "tavily_api_key", "jev_api_key"):
    secret = getattr(base_settings, name)
    assert not configured(secret) or secret not in serialized, (
        "A credential appeared in the export; publication refused"
    )
# Only the explicit allowlist above can reach a shareable artifact. Exclude
# credential/session storage, user identity, host paths and raw provider errors.
output = ROOT / "outputs/submission-live"
output.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / "assets/brand/engram-mark.svg", output / "brand.svg")
(output / "evidence.json").write_text(serialized, encoding="utf-8")


def esc(value):
    return html.escape(str(value))


trials = comparison["trials"]
rows = "".join(
    f"<tr><th>{label}</th><td>{esc(trials['baseline'][key])}</td><td>{esc(trials['reuse'][key])}</td><td>{esc(comparison['signed_savings'][key])}</td></tr>"
    for key, label in [
        ("provider_calls_observed", "Observed provider calls"),
        ("model_tokens_observed", "Observed provider tokens"),
        ("elapsed_seconds", "Elapsed seconds"),
    ]
)
graph = evidence["graph"]
captures = "".join(
    f'<figure><a href="{filename}"><img src="{filename}" alt="{label}" style="width:100%;max-height:650px;object-fit:contain"></a><figcaption>{label}. Open for full resolution.</figcaption></figure>'
    for filename, label in (
        ("live-causal-graph.png", "Actual completed correction and replacement plan"),
        ("live-reuse-comparison.png", "Actual matched live provider comparison"),
    )
    if (output / filename).is_file()
)
page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ENGRAM ENGINE | Live submission evidence</title>
<style>body{{margin:0;background:#0d1511;color:#e3e8de;font:17px/1.65 system-ui}}main{{max-width:1050px;margin:auto;padding:48px 24px}}h1{{font-size:clamp(34px,6vw,64px);line-height:1.1}}h2{{color:#c1dda7;margin-top:48px}}.kicker{{color:#c1dda7;letter-spacing:.12em}}section,article{{border:1px solid #354331;border-radius:16px;padding:24px;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;border-bottom:1px solid #354331;padding:12px}}.scroll{{overflow:auto}}pre{{white-space:pre-wrap;word-break:break-word;font-size:13px}}a{{color:#c1dda7}}.flow{{display:flex;gap:12px;flex-wrap:wrap}}.flow span{{border:1px solid #76956b;padding:12px;border-radius:12px}}small{{color:#a7b3a2;overflow-wrap:anywhere}}</style>
<main><img src="brand.svg" width="56" height="56" alt="ENGRAM ENGINE memory loop"><p class="kicker">TRACK 2 / AGENT MEMORY AND COORDINATION</p><h1>The release that remembers.</h1>
<p>A real agent team, a persisted correction, a process restart and a measured procedure comparison.</p>
<p><strong>Evidence checks passed.</strong> Initial model: {esc(evidence["initial_model"])}. Completion and comparison model: {esc(evidence["model"])}. Completed: {esc(evidence["completed_at"])}.</p>
<section><h2>One fact changes the action</h2><div class="flow"><span>Agent routes approval to Maya</span><span>New source names Priya</span><span>Graph finds old readers</span><span>Old action becomes stale</span><span>Restart</span><span>New agent plan routes to Priya</span></div>
<p>The source correction is supplied explicitly. The agent recommendations and their execution receipts are real.</p>
<details><summary>Original recommendation</summary><pre>{esc(json.dumps(graph["original_action"], indent=2))}</pre></details>
<details><summary>Actual dependency and replacement edges</summary><pre>{esc(json.dumps({"reader": graph["direct_reader_path"], "replan": graph["replan_path"], "stale": graph["stale_action"]}, indent=2))}</pre></details>
<details><summary>Revised recommendation after restart</summary><pre>{esc(json.dumps(graph["revised_action"], indent=2))}</pre></details></section>
<section><h2>Observed reuse comparison</h2><p>{esc(comparison["method"])}</p><div class="scroll"><table><thead><tr><th>Metric</th><th>Known artifacts</th><th>Verified procedure</th><th>Signed savings</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Positive differences favor reuse. Negative differences mean overhead. One pair does not establish a reliable speedup. Failed requests can have unknown billed usage; SDK retry attempts are not counted individually.</p>
<details><summary>Exact checks, provider receipts and artifact hashes</summary><pre>{esc(json.dumps(comparison, indent=2))}</pre></details></section>
<section><h2>Persistence and coordination</h2><p>{evidence["persisted_messages"]} conversation messages survived. Handoffs have actual acknowledgements.</p><details><summary>Process identities and handoff receipts</summary><pre>{esc(json.dumps({"restart": evidence["restart"], "handoffs": evidence["handoffs"]}, indent=2))}</pre></details></section>
{('<section><h2>Actual workspace views</h2>' + captures + '</section>') if captures else ''}
<section><h2>Security boundaries</h2><ul>{"".join("<li>" + esc(x) + "</li>" for x in evidence["security_boundaries"])}</ul></section>
<section><h2>Limits of this demonstration</h2><ul>{"".join("<li>" + esc(x) + "</li>" for x in evidence["limitations"])}</ul></section>
<p><a href="evidence.json">Download the sanitized evidence JSON</a></p><small>Source report SHA-256: {esc(evidence["source_report_sha256"])}</small></main></html>"""
(output / "index.html").write_text(page, encoding="utf-8")
print(json.dumps({"html": str(output / "index.html"), "evidence": str(output / "evidence.json"), "passed": True}))
