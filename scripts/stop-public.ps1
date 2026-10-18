$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$engramManifestPath = Join-Path $engramRoot 'data/collective/public-tunnel.json'
if (-not (Test-Path -LiteralPath $engramManifestPath)) { Write-Host 'No managed public tunnel.'; return }
$engramTunnel = Get-Content -LiteralPath $engramManifestPath -Raw | ConvertFrom-Json
$engramProcess = Get-Process -Id $engramTunnel.Id -ErrorAction SilentlyContinue
if ($engramProcess -and [Math]::Abs(($engramProcess.StartTime.ToUniversalTime() - ([datetime]$engramTunnel.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) { Stop-Process -Id $engramTunnel.Id }
Write-Host 'The managed public tunnel is stopped. Local services remain running.'
