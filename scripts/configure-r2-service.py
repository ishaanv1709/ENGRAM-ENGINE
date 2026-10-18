"""Provision a deployment secret through stdin, never in shell arguments."""
from pathlib import Path
import secrets
import subprocess

from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[1]
config = root / ".env.cloudflare"
values = dotenv_values(config)
token = values.get("ARTIFACT_SERVICE_TOKEN") or secrets.token_urlsafe(48)
set_key(config, "ARTIFACT_SERVICE_TOKEN", token)
set_key(config, "R2_BUCKET", "engram-collective-artifacts")
wrangler = root / "data/collective/tools/npm-cache/_npx/32026684e21afda6/node_modules/wrangler/bin/wrangler.js"
result = subprocess.run([
    "node", str(wrangler), "secret", "put", "ARTIFACT_SERVICE_TOKEN", "--config", "infra/cloudflare/wrangler.jsonc",
], input=token + "\n", text=True, encoding="utf-8", errors="replace", capture_output=True, cwd=root)
if result.returncode:
    raise SystemExit("Cloudflare secret provisioning failed; credentials were not printed")
print("Private artifact service credential saved locally and installed in Cloudflare secret storage.")
