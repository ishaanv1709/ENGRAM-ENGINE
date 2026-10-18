"""Stage a reviewed source allowlist in the new public repository checkout."""
from pathlib import Path
import re
import shutil

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/collective/deploy/github-engram-engine"
assert TARGET.is_relative_to(ROOT / "data/collective/deploy") and (TARGET / ".git").is_dir()
folders = ["collective", "src", "tests", "scripts", "frontend/src", "frontend/public", "frontend/e2e",
           "infra", "assets", "examples", "docs", "outputs/submission-live", "video/engram-film"]
names = ["README.md", "MEMORY_SYSTEM_EXPLAINED.md", ".gitignore", ".dockerignore", ".env.example",
         ".env.collective.example", ".env.cloudflare.example", "pyproject.toml", "uv.lock", "requirements.txt",
         "compose.collective.yml", "frontend/package.json", "frontend/package-lock.json", "frontend/index.html",
         "frontend/tsconfig.json", "frontend/tsconfig.app.json", "frontend/tsconfig.node.json",
         "frontend/vite.config.ts", "frontend/playwright.config.ts"]
exclude = {"__pycache__", "node_modules", ".git", ".wrangler", ".hyperframes", ".motion-review", "renders",
           "audio", "capture", ".thumbnails", ".waveform-cache", "wheels", "test-results", "dist", ".pytest_cache"}
paths = [ROOT / name for name in names if (ROOT / name).is_file()]
for folder in folders:
    for path in (ROOT / folder).rglob("*"):
        if not path.is_file() or any(part in exclude for part in path.relative_to(ROOT).parts):
            continue
        if path.name.startswith(".env") or path.suffix in {".pyc", ".log", ".gguf", ".wav", ".tsbuildinfo"}:
            continue
        if path.suffix == ".zip" and not path.relative_to(ROOT).as_posix().startswith("frontend/public/examples/"):
            continue
        if path.stat().st_size > 40_000_000:
            raise RuntimeError("Unexpected large publication file: " + str(path.relative_to(ROOT)))
        paths.append(path)

known = []
for env_file in (".env.collective", ".env.cloudflare", ".env.cloudflare.runtime"):
    for name, value in dotenv_values(ROOT / env_file).items():
        if value and len(value) >= 16 and any(word in name.lower() for word in ("api_key", "service_token", "encryption_key")):
            if "****" not in value:
                known.append(value.encode())
pattern = re.compile(rb"(?:gsk_[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)")
files = sorted(set(paths))
for path in files:
    data = path.read_bytes()
    if pattern.search(data) or any(secret in data for secret in known):
        raise RuntimeError("Secret scan rejected publication file: " + str(path.relative_to(ROOT)))
for path in files:
    destination = TARGET / path.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
print(f"Prepared {len(files)} source, documentation and public evidence files. Private runtime and secrets excluded.")
