"""Allow only the current explicit HTTPS demo origin, preserving local origins."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from collective.settings import settings

origin = sys.argv[1].rstrip("/")
parsed = urlsplit(origin)
if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port not in {None, 443}:
    raise ValueError("Supply an explicit public HTTPS origin")
origins = [value for value in settings.origins if not urlsplit(value).hostname.endswith(".trycloudflare.com")]
origins = list(dict.fromkeys([*origins, origin]))
path = root / ".env.collective"
content = path.read_text(encoding="utf-8-sig")
content = re.sub(r"(?m)^ORIGINS=.*(?:\n|$)", "", content)
path.write_text(content.rstrip() + "\nORIGINS=" + json.dumps(origins) + "\n", encoding="utf-8")
print("Configured explicit HTTPS origin; credential values were preserved.")
