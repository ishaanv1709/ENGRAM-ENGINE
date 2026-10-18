"""Package only the explicitly reviewed beginner source files for the guide."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
destination = root / "frontend/public/examples/engram-beginner-python.zip"
destination.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in ("src/capacity.py", "test_capacity.py", "README.md"):
        archive.write(root / "examples/beginner-python" / name, "engram-beginner-python/" + name)
print(destination)
