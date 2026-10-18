"""Build ENGRAM's illustrated article from measured data and editable vectors."""
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

import markdown
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
BG, PANEL, BORDER = "#0b1510", "#14231b", "#39523f"
FG, MUTED, SAGE, GOLD = "#eff3ea", "#b4c4b6", "#c5e6ad", "#e4b982"


def text(x, y, value, size=23, color=FG, weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(value)}</text>'


def card(x, y, w, h, title, lines=(), accent=SAGE):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{PANEL}" stroke="{BORDER}"/>' + text(x+25, y+43, title, 25, accent, 650) + ''.join(text(x+25, y+79+i*30, line, 20, MUTED) for i, line in enumerate(lines))


def arrow(x1, y1, x2, y2, label="", color=SAGE):
    part = f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="2.2" marker-end="url(#arrow)"/>'
    if label:
        part += text((x1+x2)/2, (y1+y2)/2-12, label, 17, MUTED, anchor="middle")
    return part


def svg(name, height, title, subtitle, body):
    output = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="{height}" viewBox="0 0 1500 {height}">
<title>{html.escape(title)}</title><desc>{html.escape(subtitle)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="{SAGE}"/></marker></defs>
<rect width="1500" height="{height}" rx="28" fill="{BG}"/>
<g font-family="Arial, sans-serif">{text(60,65,'ENGRAM ENGINE / ENGINEERING NOTES',18,MUTED,600)}{text(60,125,title,38,FG,700)}{text(60,168,subtitle,22,MUTED)}{body}{text(60,height-35,'16 OCT 2026  Â·  LOCAL BUILD  Â·  DIAGRAMS DESCRIBE IMPLEMENTATION',15,MUTED)}</g></svg>'''
    (ASSETS/f"{name}.svg").write_text(output, encoding="utf-8")


body = ''
body += text(72,285,"When knowledge changes,",60,FG,700)
body += text(72,363,"work needs a memory.",60,SAGE,700)
body += text(75,430,"Persistent agents. Connected evidence.",26,MUTED)
body += text(75,470,"A traceable reason to revise the plan.",26,MUTED)
body += '<g transform="translate(1110 270) scale(.6)" fill="none" stroke="#c5e6ad" stroke-width="18" stroke-linecap="round"><path d="M208 68a100 100 0 1 0 0 120 M188 128a60 60 0 1 0-60 60h80 M104 128h120"/></g>'
body += card(75,550,395,125,"OLD FACT",["Approval owner: Maya"],GOLD)
body += card(555,550,395,125,"CONNECTED WORK",["Reader becomes stale"])
body += card(1035,550,390,125,"NEW EVIDENCE",["Approval owner: Priya"])
body += arrow(470,612,550,612)+arrow(1030,612,955,612)
svg("cover",760,"Building Persistent Agent Teams","ENGRAM ENGINE  /  The release that remembers",body)

body = card(60,215,310,140,"WORKSPACE",["Conversations + evidence", "Authenticated project access"])
body += card(465,215,570,140,"DEEPAGENTS TEAM",["Coordinator / researcher / builder", "Verifier / curator â€” explicit role tools"])
body += card(1130,215,310,140,"POSTGRESQL",["Tasks, leases + audit", "History + checkpoints"])
body += arrow(370,285,455,285)+arrow(1040,285,1120,285)
body += card(465,435,570,140,"MEMORY MANAGER",["Types + scope + revision-aware retrieval", "Source links + dependency registration"])
body += arrow(750,355,750,425)
body += card(60,655,390,140,"FALKORDB",["Canonical memory + relationships", "DEPENDS_ON / SUPERSEDES"])
body += card(555,655,390,140,"MEM0 + QDRANT",["Fact extraction + derived index", "Local GGUF embeddings"])
body += card(1050,655,390,140,"RESTRICTED DOCKER",["Per-run files + fresh checks", "Published artifact hashes"])
body += arrow(600,575,255,645)+arrow(750,575,750,645)
body += '<path d="M1035,335 L1080,335 L1080,600 L1245,645" fill="none" stroke="#c5e6ad" stroke-width="2.2" marker-end="url(#arrow)"/>'
body += text(1100,595,"execute tools",18,MUTED)
body += text(60,860,"Host-side Safeguard admission and authorized web tools are separate from sandbox networking.",22,MUTED)
svg("architecture",935,"Shared context with separate execution","FalkorDB shapes memory and invalidation; PostgreSQL coordinates durable work.",body)

body = card(60,220,300,125,"OBSERVATION",["Persist pending episode"])
body += card(465,220,400,125,"ADMISSION",["Typed policy decisions"])
body += card(1035,220,400,125,"QUARANTINE / ARCHIVE",["Suspicious input or noise"],GOLD)
body += arrow(360,280,455,280)+arrow(865,280,1025,280,"flag / reject")
body += card(465,430,400,160,"EPISODIC",["What happened", "Source and outcome history"])
body += card(1035,430,400,160,"SEMANTIC",["Mem0 facts + source links", "Corrections retain history"])
body += arrow(665,345,665,420,"admit")+arrow(865,510,1025,510,"extract")
body += card(60,430,300,160,"PROCEDURAL",["Tool descriptions", "Versioned workflows"])
body += card(260,690,980,130,"RETRIEVAL TIERS",["Pinned context â†’ revision-aware recent cache â†’ persistent graph retrieval"])
body += arrow(210,590,450,680)+arrow(665,590,750,680)+arrow(1235,590,1050,680)
body += text(60,875,"Memory type describes meaning. Retrieval tier describes how context is loaded.",22,MUTED)
svg("memory-flow",945,"Memory types and retrieval tiers","Semantic extraction follows admission; verified outcomes can become procedural memory.",body)

body = card(60,230,380,140,"OLD FACT",["ORCHID approver: Maya", "Retained as superseded"],GOLD)
body += card(60,535,380,140,"NEW FACT",["ORCHID approver: Priya", "Selected active observation"])
body += card(565,230,380,140,"PRIOR TASK",["Read Maya's fact", "Marked stale; lease fenced"],GOLD)
body += card(1060,535,380,140,"REVISED PLAN",["Depends on Priya's fact", "Created; execution blocked"])
body += arrow(555,300,450,300,"DEPENDS_ON")
body += arrow(250,525,250,380)+text(285,452,"SUPERSEDES",17,MUTED)
body += arrow(1050,605,450,605,"DEPENDS_ON")
body += '<path d="M1250,525 L1250,300 L955,300" fill="none" stroke="#c5e6ad" stroke-width="2.2" marker-end="url(#arrow)"/>'
body += text(1100,280,"REPLANS",20,MUTED)
body += text(60,770,"Observed graph result: 1 direct reader; supersession and revision edges confirmed.",25,SAGE,600)
body += text(60,815,"Graph readers seed invalidation; SQL expands task dependencies and parent coordinators.",22,MUTED)
svg("causal-graph",895,"The graph changes which work remains valid","Controlled ORCHID scenario â€” real graph and runtime; no model-selected replan completion.",body)

body = card(60,230,400,150,"PROPOSE VERSION",["Actual artifacts + SHA-256", "Source check event IDs"])
body += card(550,230,400,150,"VERIFY SEPARATELY",["Different run, fresh container", "Execute checks + hash bytes"])
body += card(1040,230,400,150,"ACTIVATE",["Bind version and manifest", "Keep verification evidence"])
body += arrow(460,305,540,305)+arrow(950,305,1030,305)
body += card(550,535,400,150,"REUSE EXACT VERSION",["Prepare bound artifacts", "Fresh checks + reuse receipt"])
body += '<path d="M1240,390 L1240,610 L960,610" fill="none" stroke="#c5e6ad" stroke-width="2.2" marker-end="url(#arrow)"/>'
body += card(60,535,400,150,"MEASURE",["Calls, tokens, execution time", "Keep zero / negative deltas"])
body += arrow(540,610,470,610)
body += text(60,775,"A passing test is evidence for its assertions; it is not proof of complete correctness.",22,MUTED)
svg("procedure-flow",855,"Procedures remember the exact checked bytes","Two active versions in the local fixture; version 2 passes the same ten-test suite.",body)

for name in ["DM-Sans.ttf","Manrope.ttf","DM-Sans-OFL.txt","Manrope-OFL.txt"]:
    shutil.copyfile(ROOT/"video/engram-film/assets"/name, ASSETS/name)
shutil.copyfile(ROOT/"assets/brand/engram-mark.svg", ASSETS/"engram-mark.svg")

report_path = ROOT/"data/collective/showcase-measurement-latest.json"
raw = json.loads(report_path.read_text(encoding="utf-8"))
assert len(raw["benchmark"]["trials"]) == 10 and raw["provider_calls"] == 0
data = {"observed_date":"2026-10-16", "experiment":"Five paired fresh-container trials, alternating order",
    "source_report_sha256":hashlib.sha256(report_path.read_bytes()).hexdigest(),
    "method":raw["benchmark"]["method"],"timing_scope":raw["benchmark"]["timing_scope"],
    "limitations":raw["benchmark"]["limitations"],"summary":raw["benchmark"]["summary"],
    "trials":[{k:v for k,v in t.items() if k not in {"run_id","check_event_id"}} for t in raw["benchmark"]["trials"]],
    "container_probes":raw["container_security"]["behavior"],
    "identity_note":"Internal task and event identifiers omitted; measured values and artifact hashes preserved."}
(HERE/"evaluation-data.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
with (HERE/"evaluation-trials.csv").open("w",newline="",encoding="utf-8") as file:
    keys=["pair","mode","total_ms","prepare_ms","execute_ms","validation_ms","tool_calls","tool_executions","file_writes","model_calls","model_tokens","tests_passed"]
    writer=csv.DictWriter(file,fieldnames=keys,extrasaction="ignore");writer.writeheader();writer.writerows(data["trials"])

font_manager.fontManager.addfont(str(ASSETS/"DM-Sans.ttf"))
plt.rcParams.update({"font.family":"DM Sans","font.size":12,"axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none"})
baseline=sorted([t for t in data["trials"] if t["mode"]=="baseline"],key=lambda t:t["pair"])
reuse=sorted([t for t in data["trials"] if t["mode"]=="reuse"],key=lambda t:t["pair"])
fig,(left,right)=plt.subplots(1,2,figsize=(14.5,6.2),gridspec_kw={"width_ratios":[1.1,1]},facecolor="#f7f6ef")
for ax in (left,right):
    ax.set_facecolor("#f7f6ef");ax.spines[["left","bottom"]].set_color("#a2aca0");ax.tick_params(colors="#394a3c")
for i,(b,r) in enumerate(zip(baseline,reuse)):
    left.plot([1,2],[b["total_ms"]/1000,r["total_ms"]/1000],color="#b8c3b3",lw=1.5,zorder=1)
    left.scatter([1,2],[b["total_ms"]/1000,r["total_ms"]/1000],c=["#8f6a3d","#386247"],s=70,zorder=2)
for x,rows,label_x,align in [(1,baseline,.84,"right"),(2,reuse,2.16,"left")]:
    previous = -100
    for trial in sorted(rows,key=lambda t:t["total_ms"]):
        point=trial["total_ms"]/1000
        label_y=max(point,previous+.12)
        left.annotate(str(trial["pair"]),(x,point),xytext=(label_x,label_y),textcoords="data",ha=align,va="center",fontsize=10,
            arrowprops={"arrowstyle":"-","lw":.65,"color":"#8c9a87"})
        previous=label_y
left.set_xlim(.6,2.4);left.set_ylim(5.3,7.5);left.set_xticks([1,2],["Exact artifact\nbundle","Verified\nprocedure"]);left.set_ylabel("Elapsed seconds");left.set_title("Every paired observation",loc="left",weight="bold",pad=20)
left.grid(axis="y",alpha=.16)
diff=[b["total_ms"]-r["total_ms"] for b,r in zip(baseline,reuse)]
right.barh(range(1,6),diff,color=["#386247" if d>=0 else "#9b6746" for d in diff],height=.54)
right.axvline(0,color="#546451",lw=1);right.set_yticks(range(1,6),[f"Pair {i}" for i in range(1,6)]);right.invert_yaxis();right.set_xlim(-360,1130);right.set_xlabel("Baseline minus reuse, milliseconds");right.set_title("Three pairs faster, two slower",loc="left",weight="bold",pad=20)
for i,value in enumerate(diff,1):
    right.text(value+(18 if value>=0 else -18),i,f"{value:+.1f}",va="center",ha="left" if value>=0 else "right",fontsize=11)
fig.suptitle("Reuse latency showed mixed local results",x=.07,ha="left",fontsize=23,weight="bold",color="#14231b",y=.98)
fig.text(.07,.018,"5 pairs Â· identical hashes and 10-test suite Â· no inference Â· no reliable speedup established",fontsize=12,color="#52634f")
fig.subplots_adjust(left=.08,right=.96,top=.80,bottom=.19,wspace=.42)
fig.savefig(ASSETS/"reuse-evaluation.png",dpi=180,facecolor=fig.get_facecolor())
fig.savefig(ASSETS/"reuse-evaluation.svg",facecolor=fig.get_facecolor())
plt.close(fig)


def render_article():
    source=(HERE/"engram-collective.md").read_text(encoding="utf-8")
    title=source.splitlines()[0].removeprefix("# ")
    body=markdown.markdown("\n".join(source.splitlines()[2:]),extensions=["tables","fenced_code","toc"])
    # Images stay semantic and self-contained assets remain portable in the ZIP.
    body=re.sub(r'<p>(<img [^>]+>)</p>',r'<figure>\1</figure>',body)
    body=re.sub(r'<figure><img alt="([^"]*)"([^>]+)></figure>',r'<figure><img alt="\1"\2><figcaption>\1</figcaption></figure>',body)
    content=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="How ENGRAM connects agent memory, graph dependencies and verified procedures, with real local evaluations."><title>{html.escape(title)}</title><style>
@font-face{{font-family:DM;src:url('assets/DM-Sans.ttf')}}@font-face{{font-family:Manrope;src:url('assets/Manrope.ttf')}}
:root{{--ink:#15261a;--muted:#586555;--paper:#f7f6ef;--line:#d7ddcf}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:18px/1.85 DM,Arial,sans-serif}}a{{color:#286540;text-underline-offset:4px}}.masthead{{display:flex;justify-content:space-between;align-items:center;max-width:1200px;margin:auto;padding:26px 34px;border-bottom:1px solid var(--line);font-size:13px;letter-spacing:2px}}.brand{{display:flex;align-items:center;gap:14px;font-weight:750}}.brand img{{width:35px;background:#14231b;border-radius:10px;padding:4px}}header{{max-width:1080px;margin:70px auto 30px;padding:0 34px}}.kicker{{color:#4f6c43;font-size:13px;letter-spacing:3px;font-weight:700}}h1{{font:750 clamp(38px,5.1vw,65px)/1.16 Manrope,Arial,sans-serif;letter-spacing:-2px;margin:22px 0}}.deck{{font-size:23px;line-height:1.6;color:var(--muted);max-width:780px}}main{{max-width:1080px;margin:auto;padding:0 34px 80px}}article>p,article>ul,article>ol,article>h2,article>h3,article>pre{{max-width:820px;margin-left:auto;margin-right:auto}}article>p:first-child{{font-size:14px;color:var(--muted);margin-bottom:32px}}h2{{font:720 32px/1.3 Manrope,Arial,sans-serif;letter-spacing:-.7px;padding-top:32px;margin-bottom:22px}}h3{{font-size:23px}}p{{margin-top:24px;margin-bottom:24px}}strong{{font-weight:750}}figure{{margin:42px -12px}}figure img{{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:18px}}figcaption{{color:var(--muted);font-size:13px;line-height:1.6;max-width:820px;margin:13px auto 0}}table{{width:100%;border-collapse:collapse;font-size:15px;line-height:1.65;margin:32px 0}}th{{text-align:left;background:#e9edde;color:#1b371f;font-weight:750}}td,th{{padding:15px 17px;border-bottom:1px solid var(--line);vertical-align:top}}td:not(:first-child){{font-variant-numeric:tabular-nums}}code{{overflow-wrap:anywhere;font-size:.88em;background:#e9eddf;border-radius:4px;padding:2px 5px}}pre{{background:#132119;color:#e2ecdc;padding:25px;border-radius:15px;overflow:auto;line-height:1.65}}pre code{{overflow-wrap:normal;background:none;padding:0}}footer{{border-top:1px solid var(--line);max-width:1080px;margin:auto;padding:28px 34px 60px;color:var(--muted);font-size:13px}}.resources{{display:flex;gap:22px;flex-wrap:wrap}}@media(max-width:650px){{body{{font-size:17px}}.masthead{{padding:18px 20px;letter-spacing:1px}}.masthead>span{{display:none}}header{{margin:40px auto 20px;padding:0 22px}}h1{{letter-spacing:-1.2px}}.deck{{font-size:20px}}main{{padding:0 22px 40px}}h2{{font-size:26px}}figure{{margin:30px -10px}}table{{font-size:12px;line-height:1.55}}th,td{{padding:10px 7px}}footer{{padding:22px}}}}@media print{{.masthead{{padding:10px}}header{{margin:30px auto}}figure,table,pre{{break-inside:avoid}}h2{{break-after:avoid}}body{{font-size:12px}}a{{text-decoration:none}}}}
</style></head><body><div class="masthead"><div class="brand"><img src="assets/engram-mark.svg" alt="ENGRAM ENGINE logo">ENGRAM ENGINE</div><span>MEMORY / COORDINATION / EVIDENCE</span></div><header><div class="kicker">GRAPH HACKS Â· TRACK 2</div><h1>{html.escape(title)}</h1><p class="deck">A release changes owner. The graph shows which work must change with it.</p></header><main><article>{body}</article></main><footer><div class="resources"><a href="engram-collective.md">Editable article</a><a href="evaluation-trials.csv">Trial data CSV</a><a href="evaluation-data.json">Evaluation details</a><a href="diagrams.md">Mermaid source</a></div><p>Engineering results Â· Updated 18 October 2026 Â· Recovered live scenario, four-pair reuse and concurrency/recovery measurements included.</p></footer></body></html>'''
    (HERE/"index.html").write_text(content,encoding="utf-8")


render_article()
print("Built five original SVG figures, measured chart, data exports and article HTML.")
