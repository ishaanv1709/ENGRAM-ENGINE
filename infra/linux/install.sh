#!/usr/bin/env bash
# Run only on the user's provisioned Ubuntu 24.04 host after uploading this
# source tree to /opt/engram and the real GGUF model. Does not migrate old data.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo on the deployment server.' >&2; exit 1; }
[[ $# -eq 1 ]] || { echo 'Usage: sudo bash infra/linux/install.sh https://YOUR-HOSTNAME' >&2; exit 1; }
cd /opt/engram
[[ -f pyproject.toml && -f uv.lock && -d collective ]] || exit 1
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo 'This installer targets Ubuntu 24.04.' >&2; exit 1; }
[[ -f data/models/mxbai-embed-large-v1_fp32.gguf ]] || { echo 'Upload the real embedding model first.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 caddy python3 python3-venv build-essential cmake libopenblas-dev pkg-config ca-certificates curl nodejs npm
systemctl enable --now docker
id engram >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/engram --shell /usr/sbin/nologin engram
usermod -aG docker engram
python3 -m venv /opt/engram/.bootstrap
/opt/engram/.bootstrap/bin/pip install 'uv==0.11.13'
export UV_CACHE_DIR=/opt/engram/.cache/uv
export UV_PYTHON_INSTALL_DIR=/opt/engram/.python
export UV_PROJECT_ENVIRONMENT=/opt/engram/.venv
/opt/engram/.bootstrap/bin/uv sync --locked --python 3.11 --no-dev
CMAKE_ARGS='-DGGML_NATIVE=OFF -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS' \
  /opt/engram/.bootstrap/bin/uv pip install --python .venv/bin/python --index-strategy unsafe-best-match -r collective/embedding-requirements.txt
.venv/bin/python -m ensurepip
mkdir -p infra/wheels data/collective/artifacts
.venv/bin/python -m pip download --dest infra/wheels --only-binary=:all: -r infra/sandbox-requirements.txt
docker build -f infra/sandbox.Dockerfile -t engram-sandbox:local .
(cd frontend && npm ci && npm run build)
if [[ ! -f .env.collective ]]; then
  .venv/bin/python scripts/production-environment.py --origin "$1" --root /opt/engram
else
  echo 'Preserving existing server environment and database credentials.'
fi
# Generate a proxy only after validating the configured origin in Python.
ENGRAM_EXPECTED_ORIGIN="$1" .venv/bin/python - <<'PY'
import os
from pathlib import Path
from urllib.parse import urlsplit
from collective.settings import base_settings
origin = os.environ['ENGRAM_EXPECTED_ORIGIN'].rstrip('/')
assert base_settings.origins == [origin] and base_settings.cookie_secure
parsed = urlsplit(origin)
assert parsed.scheme == 'https' and parsed.hostname and parsed.path == ''
assert not any(c in parsed.netloc for c in '{}\n\r\t ')
Path('/etc/caddy/Caddyfile').write_text(parsed.netloc + ' {\n  encode zstd gzip\n  reverse_proxy 127.0.0.1:8088\n}\n')
PY
chown -R engram:engram /opt/engram /var/lib/engram
chmod 600 /opt/engram/.env.collective
cat >/etc/systemd/system/engram-stores.service <<'UNIT'
[Unit]
Description=ENGRAM persistent local databases
Requires=docker.service
After=docker.service network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/engram
ExecStart=/usr/bin/docker compose --env-file .env.collective -f infra/linux/compose.yml up -d --wait --wait-timeout 120
ExecStop=/usr/bin/docker compose --env-file .env.collective -f infra/linux/compose.yml stop
[Install]
WantedBy=multi-user.target
UNIT
for service in embeddings api worker; do
  case "$service" in
    embeddings) command='/opt/engram/.venv/bin/python -m collective.embedding_server' ;;
    api) command='/opt/engram/.venv/bin/python -m uvicorn collective.app:app --host 127.0.0.1 --port 8088 --proxy-headers --forwarded-allow-ips 127.0.0.1' ;;
    worker) command='/opt/engram/.venv/bin/python -m collective.agents' ;;
  esac
  cat >"/etc/systemd/system/engram-$service.service" <<UNIT
[Unit]
Description=ENGRAM $service
Requires=engram-stores.service
After=engram-stores.service network-online.target
[Service]
Type=simple
User=engram
Group=engram
SupplementaryGroups=docker
WorkingDirectory=/opt/engram
Environment=HOME=/var/lib/engram
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$command
Restart=on-failure
RestartSec=5
TimeoutStopSec=40
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
done
systemctl daemon-reload
caddy validate --config /etc/caddy/Caddyfile
systemctl enable --now engram-stores engram-embeddings engram-api engram-worker
systemctl enable caddy
systemctl restart caddy
echo 'Services installed. Verify HTTPS, all dependencies, sandboxes and reboot persistence before announcing cutover.'
