"""Package explicitly scoped local submission materials, refusing known secrets."""
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collective.settings import base_settings, configured  # noqa: E402

out = ROOT / "outputs/submission-live"
checks = json.loads((out / "track2/verification.json").read_text())
public = json.loads((out / "track2/public-check.json").read_text())
assert checks["passed"] and public["passed"]
secrets = [getattr(base_settings, key) for key in ("groq_api_key", "anthropic_api_key", "langsearch_api_key", "tavily_api_key", "jev_api_key")]
for relative in ("submission-live-2026-10-18/session.json", "track2-upgrade/browser-session.json"):
    secrets.extend(json.loads((ROOT / "data/collective" / relative).read_text(encoding="utf-8-sig")).values())
secrets = [str(s).encode() for s in secrets if s and configured(str(s)) and len(str(s)) > 12]


def safe_bytes(path):
    data = path.read_bytes()
    assert not any(secret in data for secret in secrets), f"Private value in {path.name}; refused"
    return data


blog = ROOT / "docs/blog"
blog_files = sorted(p for p in blog.rglob("*") if p.is_file() and p.suffix not in (".zip", ".pyc") and "__pycache__" not in p.parts and p.name != "manifest.json")
manifest = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Recovered live team workflow, four live reuse pairs and real coordination/recovery fixtures; extra fresh team mission quota-blocked",
    "files": [{"path": p.relative_to(blog).as_posix(), "bytes": p.stat().st_size, "sha256": hashlib.sha256(safe_bytes(p)).hexdigest()} for p in blog_files],
}
(blog / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
blog_files.append(blog / "manifest.json")
with zipfile.ZipFile(ROOT / "outputs/ENGRAM-blog-package.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in blog_files:
        archive.writestr(path.relative_to(ROOT / "docs").as_posix(), safe_bytes(path))
shutil.copyfile(ROOT / "outputs/ENGRAM-blog-package.zip", blog / "ENGRAM-blog-package.zip")

evidence_files = sorted(p for p in out.rglob("*") if p.is_file() and p.suffix in (".html", ".json", ".png", ".svg", ".txt"))
docs = [ROOT / "docs" / name for name in ("SUBMISSION.md", "LIVE-DEMO.md", "REUSE-MEASUREMENT.md", "SECURITY-BOUNDARIES.md", "VERIFICATION.md", "PROVIDER-VERIFICATION.md")]
measured = sorted((ROOT / "data/collective/track2-upgrade/measured-runtime").glob("*.py"))
with zipfile.ZipFile(ROOT / "outputs/ENGRAM-submission-evidence.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in evidence_files + docs:
        name = path.relative_to(ROOT).as_posix()
        if path.parent == out and path.name in {"backend-checks.txt", "verification.json", "public-check.json"}:
            name = "historical/initial-live-verification/" + path.name
        archive.writestr(name, safe_bytes(path))
    for path in measured:
        archive.writestr("measured-runtime/" + path.name, safe_bytes(path))
    archive.writestr("README.txt", "Current verification: outputs/submission-live/track2/verification.json. Current live evidence: outputs/submission-live/track2-upgrade.json, including the completed 120B restart workflow and preserved unsuccessful attempts. Earlier verification logs are under historical/. The six measured-runtime files are the exact source snapshot of the four 20B live pairs, not a standalone application. Later tested changes have separate hashes in current verification. The matching repository still requires publication. No provider keys, visitor cookies or private runtime databases are included.\n")
print(json.dumps({"packaged": True, "blog_files": len(blog_files), "evidence_files": len(evidence_files) + len(docs) + len(measured) + 1, "known_secret_scan": "passed"}))
