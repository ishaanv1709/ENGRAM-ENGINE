"""Create a secret-free, allowlisted image context; never copies .env or data trees."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
DESTINATION = ROOT / "data/collective/cloudflare-runtime-build"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox-image-tar", type=Path, required=True)
    args = parser.parse_args()
    sandbox = args.sandbox_image_tar.resolve(strict=True)
    model = ROOT / "data/models/mxbai-embed-large-v1_fp32.gguf"
    if not model.is_file() or model.stat().st_size < 1_000_000_000:
        raise SystemExit("The real FP32 embedding GGUF is required")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    copies = [(ROOT / name, DESTINATION / name) for name in ("pyproject.toml", "uv.lock")]
    copies += [(path, DESTINATION / path.relative_to(ROOT)) for path in sorted((ROOT / "collective").glob("*.py"))]
    copies += [(ROOT / "collective/schema.sql", DESTINATION / "collective/schema.sql"),
               (ROOT / "collective/embedding-requirements.txt", DESTINATION / "collective/embedding-requirements.txt"),
               (Path(__file__).parent / "Dockerfile", DESTINATION / "Dockerfile"),
               (Path(__file__).parent / "supervisor.py", DESTINATION / "runtime/supervisor.py"),
               (sandbox, DESTINATION / "sandbox-image.tar"),
               (model, DESTINATION / "data/models" / model.name)]
    allowed = {destination.resolve() for _, destination in copies}
    for existing in DESTINATION.rglob("*"):
        if existing.is_file() and existing.resolve() not in allowed:
            raise SystemExit("Unexpected file in image context; review it before continuing")
    manifest = []
    for source, destination in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Copying the allowlisted model is intentional; it is never added to Git.
        shutil.copyfile(source, destination)
        digest = hashlib.file_digest(destination.open("rb"), "sha256").hexdigest()
        manifest.append({"path": str(destination.relative_to(DESTINATION)), "bytes": destination.stat().st_size,
                         "sha256": digest})
    print(json.dumps({"context": str(DESTINATION), "files": manifest}, indent=2))


if __name__ == "__main__":
    main()
