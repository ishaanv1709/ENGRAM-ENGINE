"""Select real, explicitly identified capture sources for the walkthrough."""
import json
from pathlib import Path

data = Path("data/collective")
infrastructure = json.loads((data / "film-infrastructure-evidence.json").read_text(encoding="utf-8"))
assert infrastructure["infrastructure_passed"] and not infrastructure["autonomous_team_verified"]
archive = json.loads((data / "live-debug-20261016T011457Z.json").read_text(encoding="utf-8"))
assert any(run["role"] == "builder" and run["status"] == "completed" for run in archive["runs"])
assert any(run["role"] == "verifier" and run["status"] == "completed" for run in archive["runs"])
partial = {"fixture": archive["report"]["fixture"], "credential_kind": "live", "scope": "Earlier partial Qwen run: actual builder, independent verifier and Mem0; complete team workflow did not pass"}
config = {"default": {"fixture": infrastructure["fixture"], "credential_kind": "infrastructure", "scope": infrastructure["execution_mode"]},
    "panels": {"team": partial, "memory": partial}}
(data / "film-capture-fixtures.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
print("Configured real service validation panels and separately identified earlier partial Qwen evidence.")
