param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$env:TEMP = Join-Path $engramRoot 'data/collective/tmp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $engramRoot 'data/collective/tools/npm-cache'
$env:WRANGLER_SEND_METRICS = 'false'
$engramArgs = @('exec', '--yes', '--package=wrangler@4.151.1', '--', 'wrangler', 'deploy', '--config', 'infra/cloudflare/wrangler.jsonc')
if ($DryRun) { $engramArgs += '--dry-run' }
& npm.cmd @engramArgs
if ($LASTEXITCODE -ne 0) { throw 'Cloudflare deployment failed.' }
