$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$engramManifestPath = Join-Path $engramRoot 'data/collective/public-tunnel.json'
if (Test-Path -LiteralPath $engramManifestPath) {
    $engramPrior = Get-Content -LiteralPath $engramManifestPath -Raw | ConvertFrom-Json
    $engramExisting = Get-Process -Id $engramPrior.Id -ErrorAction SilentlyContinue
    if ($engramExisting -and [Math]::Abs(($engramExisting.StartTime.ToUniversalTime() - ([datetime]$engramPrior.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
        Write-Host $engramPrior.url
        return
    }
}
$engramBinary = Join-Path $engramRoot 'data/collective/tools/cloudflared.exe'
if (-not (Test-Path -LiteralPath $engramBinary)) { throw 'Install the official cloudflare/cloudflared Windows amd64 executable at data/collective/tools/cloudflared.exe first.' }
$engramOutput = Join-Path $engramRoot 'data/collective/logs/public-tunnel.out.log'
$engramError = Join-Path $engramRoot 'data/collective/logs/public-tunnel.err.log'
$engramTunnel = Start-Process -FilePath $engramBinary -ArgumentList @('tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:8088','--metrics','127.0.0.1:20246') -WorkingDirectory $engramRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $engramOutput -RedirectStandardError $engramError
$engramDeadline = (Get-Date).AddSeconds(55)
$engramUrl = $null
while ((Get-Date) -lt $engramDeadline) {
    Start-Sleep -Seconds 1
    if ($engramTunnel.HasExited) { throw 'Tunnel exited; inspect data/collective/logs/public-tunnel.err.log.' }
    $engramMatch = [regex]::Match((Get-Content -LiteralPath $engramError -Raw -ErrorAction SilentlyContinue), 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($engramMatch.Success) { $engramUrl = $engramMatch.Value; break }
}
if (-not $engramUrl) { Stop-Process -Id $engramTunnel.Id; throw 'No public URL was issued within 55 seconds.' }
@{ Id=$engramTunnel.Id; Started=$engramTunnel.StartTime.ToUniversalTime().ToString('o'); url=$engramUrl; kind='temporary_https_tunnel'; origin='http://127.0.0.1:8088'; executable_sha256=(Get-FileHash -LiteralPath $engramBinary -Algorithm SHA256).Hash } | ConvertTo-Json | Set-Content -LiteralPath $engramManifestPath
& '.\.venv-collective311\Scripts\python.exe' 'scripts/configure-public.py' $engramUrl
if ($LASTEXITCODE -ne 0) { throw 'Origin configuration failed; stop the tunnel with scripts/stop-public.ps1.' }
Write-Host "Public URL: $engramUrl"
Write-Host 'Restart the API to load the explicit origin. The computer and tunnel must remain running.'
