"""Prepare the static, Medium-importable article and its allowlisted images."""
from pathlib import Path
import html
import re
import shutil
import zipfile

import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
SOURCES = {
    "architecture.png": ROOT / "docs/architecture/engram-engine-architecture.png",
    "memory-flow.png": ROOT / "docs/blog/assets/memory-flow.png",
    "causal-action.png": ROOT / "docs/blog/assets/track2-120b-causal-action.png",
    "procedure-flow.png": ROOT / "docs/blog/assets/procedure-flow.png",
    "reuse-results.png": ROOT / "docs/blog/assets/track2-live-series.png",
}
for name, source in SOURCES.items():
    if not source.is_file():
        raise FileNotFoundError(source)
    shutil.copy2(source, ASSETS / name)

source_text = (HERE / "article.md").read_text(encoding="utf-8")
assert "\u2014" not in source_text, "Article must not contain em dashes"
assert not re.search(r"ENGRAM\s+COLLECTIVE", source_text, flags=re.I)
for asset in re.findall(r"!\[[^]]*\]\(([^)]+)\)", source_text):
    assert (HERE / asset).is_file(), asset

body = markdown.markdown(source_text, extensions=["tables", "fenced_code"])
body = re.sub(r'<p>(<img [^>]+>)</p>\s*<p><em>(.*?)</em></p>',
              r'<figure>\1<figcaption>\2</figcaption></figure>', body,
              flags=re.S)
title = "The Best Agent Team Remembers Why"
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | ENGRAM ENGINE</title>
<meta name="description" content="How ENGRAM ENGINE coordinates persistent agent teams, follows corrected facts through FalkorDB, and measures procedural memory reuse.">
<link rel="canonical" href="https://engram-collective.spring-cherry-c778.workers.dev/blog/medium/">
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f6f7f1;color:#18251d;font-family:Georgia,serif;line-height:1.8}}header,article,footer{{max-width:900px;margin:auto;padding:28px}}header{{font:700 13px/1.5 system-ui;letter-spacing:.14em}}header a{{text-decoration:none;color:#213b2c}}article{{padding-top:12px}}h1{{font:700 clamp(40px,7vw,72px)/1.05 system-ui;letter-spacing:-.05em;margin:0 0 22px}}h2{{font:650 clamp(24px,4vw,32px)/1.25 system-ui;letter-spacing:-.025em;margin:52px 0 20px}}h1+h2{{font:400 23px/1.45 system-ui;color:#546356;letter-spacing:0;margin:0 0 38px}}p,li{{font-size:20px}}a{{color:#275c3f;text-underline-offset:4px;overflow-wrap:anywhere}}figure{{margin:38px -28px}}img{{display:block;width:100%;height:auto;border-radius:12px}}figcaption{{font:14px/1.6 system-ui;color:#546356;padding:14px 28px}}table{{border-collapse:collapse;width:100%;font:16px/1.5 system-ui}}td,th{{border-bottom:1px solid #cdd5c9;text-align:left;padding:15px 10px}}code{{font-size:.82em;overflow-wrap:anywhere;background:#e8ede3;padding:2px 5px;border-radius:4px}}footer{{border-top:1px solid #cdd5c9;font:14px/1.7 system-ui}}@media(max-width:600px){{header,article,footer{{padding-left:22px;padding-right:22px}}p,li{{font-size:18px}}figure{{margin-left:0;margin-right:0}}figcaption{{padding:12px 0}}table{{font-size:13px}}td,th{{padding:12px 5px}}}}
</style></head><body><header><a href="/">ENGRAM ENGINE</a> / BUILD NOTES</header><main><article>{body}</article></main><footer>Original article and measured project evidence. Prepared for Medium import, not automatically published to a Medium account.</footer></body></html>'''
(HERE / "index.html").write_text(page, encoding="utf-8")
bundle = ROOT / "outputs/ENGRAM-ENGINE-Medium-kit.zip"
bundle.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in ("article.md", "index.html", "PUBLISHING.md"):
        archive.write(HERE / name, f"medium/{name}")
    for name in SOURCES:
        archive.write(ASSETS / name, f"medium/assets/{name}")
print(f"Prepared {len(source_text.split())} words, {len(SOURCES)} images: {HERE}")
print(f"Medium kit: {bundle}")
