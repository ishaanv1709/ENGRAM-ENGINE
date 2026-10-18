$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
if (-not (Test-Path -LiteralPath 'vendor/kev/pyproject.toml')) {
    git clone --depth 1 https://github.com/jaredpalmer/kev.git vendor/kev
    if ($LASTEXITCODE -ne 0) { throw 'Kev source download failed.' }
}
# Source used by this integration; released weights are separately pinned v1.0.
git -C vendor/kev checkout dd375f27fd61486c52204205e10a0d2e10f3b34a
if ($LASTEXITCODE -ne 0) { throw 'Pinned Kev source revision is unavailable; fetch it before proceeding.' }
$env:UV_PROJECT_ENVIRONMENT = Join-Path $engramRoot '.venv-kev'
$env:UV_CACHE_DIR = Join-Path $engramRoot 'data/collective/uv-cache'
Push-Location vendor/kev
try {
    uv sync --extra serve --no-dev --python 3.12 --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
    if ($LASTEXITCODE -ne 0) { throw 'Kev dependency installation failed.' }
} finally { Pop-Location }
Write-Host 'Kev installed. The first start downloads its model and base weights.'
