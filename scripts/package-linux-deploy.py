"""Prepare a source-only server upload, never copying runtime credentials/data."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collective.settings import base_settings, configured  # noqa: E402

files = []
for folder in ("collective", "src", "scripts", "frontend/src", "frontend/public", "infra/linux", "examples"):
    for path in (ROOT / folder).rglob("*"):
        if path.is_file() and not any(part in {"__pycache__", "node_modules", ".git"} for part in path.parts) and path.suffix not in {".pyc", ".zip"}:
            files.append(path)
for name in ("pyproject.toml", "uv.lock", "README.md", ".env.collective.example", ".dockerignore", "infra/sandbox.Dockerfile", "infra/sandbox-requirements.txt", "frontend/package.json", "frontend/package-lock.json", "frontend/index.html", "frontend/tsconfig.json", "frontend/tsconfig.app.json", "frontend/tsconfig.node.json", "frontend/vite.config.ts", "docs/FREE-HOSTING.md"):
    path = ROOT / name
    if path.is_file():
        files.append(path)
known = [getattr(base_settings, field) for field in ("groq_api_key", "anthropic_api_key", "jev_api_key", "tavily_api_key", "langsearch_api_key")]
known = [value.encode() for value in known if configured(value)]
manifest = []
target = ROOT / "outputs/ENGRAM-linux-deploy.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        data = path.read_bytes()
        assert not any(secret in data for secret in known), "Refusing a source file containing an operator key"
        name = path.relative_to(ROOT).as_posix()
        archive.writestr(name, data)
        manifest.append({"file": name, "sha256": hashlib.sha256(data).hexdigest()})
    archive.writestr("deployment-manifest.json", json.dumps({"scope": "Fresh Linux installation source; no runtime data, provider keys, private deployment keys or embedding weights", "files": manifest}, indent=2))
print(json.dumps({"bundle": str(target), "files": len(manifest), "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
