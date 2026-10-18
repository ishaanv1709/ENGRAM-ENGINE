"""Read account deployment capabilities without exposing OAuth credentials."""
import concurrent.futures
import json
import os
from pathlib import Path
import tomllib
import urllib.error
import urllib.request

ACCOUNT = "0759656c9efc281f7558f048f2b69b85"
config = Path(os.environ["APPDATA"]) / "xdg.config/.wrangler/config/default.toml"
token = tomllib.loads(config.read_text())["oauth_token"]
paths = [
    "workers/scripts", "workers/subdomain", "workers/account-settings",
    "containers/applications", "r2/buckets", "d1/database", "subscriptions",
    "entitlements", "billing/credits",
]

def inspect(path):
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            payload = json.load(response)
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        payload = json.load(error)
    result = payload.get("result")
    if path == "workers/scripts" and isinstance(result, list):
        result = [{key: entry.get(key) for key in ("id", "created_on", "modified_on")} for entry in result]
    return {"path": path, "status": status, "success": payload.get("success"),
            "result": result, "errors": payload.get("errors")}

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(inspect, paths))
destination = Path("data/collective/deploy/cloudflare-inspection.json")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(results, indent=2))
for entry in results:
    summary = dict(entry)
    if entry["path"] == "entitlements":
        summary["result"] = [
            {"id": item["id"], "allocation": item["allocation"]}
            for item in entry["result"] or []
            if any(word in item["id"] for word in ("containers", "cloudchamber", "workers.standard"))
        ]
    print(json.dumps(summary))
