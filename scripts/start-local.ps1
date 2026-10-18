param([switch]$Install, [switch]$RebuildSandbox)
$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$engramLinuxRoot = '/mnt/' + $engramRoot.Substring(0,1).ToLower() + $engramRoot.Substring(2).Replace('\','/')
if (-not (Test-Path -LiteralPath '.env.collective')) { Copy-Item -LiteralPath '.env.collective.example' -Destination '.env.collective' }
New-Item -ItemType Directory -Force -Path 'data/collective/logs' | Out-Null
$engramAnchorEntry = $null
if (Test-Path -LiteralPath 'data/collective/processes.json') {
    $engramPriorAnchor = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json) | Where-Object { $_.Module -eq 'collective.wsl-anchor' } | Select-Object -First 1
    if ($engramPriorAnchor) {
        $engramAnchorProcess = Get-Process -Id $engramPriorAnchor.Id -ErrorAction SilentlyContinue
        if ($engramAnchorProcess -and [Math]::Abs(($engramAnchorProcess.StartTime.ToUniversalTime() - ([datetime]$engramPriorAnchor.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) { $engramAnchorEntry = $engramPriorAnchor }
    }
}
if (-not $engramAnchorEntry) {
    $engramAnchorProcess = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu-22.04','--exec','/bin/sleep','infinity') -WindowStyle Hidden -PassThru
    $engramAnchorEntry = @{ Id=$engramAnchorProcess.Id; Module='collective.wsl-anchor'; Started=$engramAnchorProcess.StartTime.ToUniversalTime().ToString('o') }
}
if ($Install) {
    $env:UV_CACHE_DIR = Join-Path $engramRoot 'data/collective/uv-cache'
    $env:UV_PROJECT_ENVIRONMENT = '.venv-collective311'
    uv sync --locked --python 3.11
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    try { npm ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }; npm run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' } } finally { Pop-Location }
    wsl -d Ubuntu-22.04 --exec sh -lc "cd '$engramLinuxRoot' && UV_PROJECT_ENVIRONMENT=.venv-collective-linux ~/.local/bin/uv sync --locked --python 3.11 && ~/.local/bin/uv pip install --python .venv-collective-linux/bin/python --index-strategy unsafe-best-match -r collective/embedding-requirements.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Linux embedding environment installation failed.' }
    & '.\.venv-collective311\Scripts\python.exe' -m ensurepip
    & '.\.venv-collective311\Scripts\python.exe' -m pip download --dest infra/wheels --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: -r infra/sandbox-requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Sandbox dependency download failed.' }
}
wsl -d Ubuntu-22.04 -u root --exec /usr/sbin/service docker start
if ($LASTEXITCODE -ne 0) { throw 'Docker inside WSL could not start.' }
wsl -d Ubuntu-22.04 --exec sh -lc "cd '$engramLinuxRoot' && docker compose --progress quiet -f compose.collective.yml up -d --wait --wait-timeout 60"
if ($LASTEXITCODE -ne 0) { throw 'Local containers failed to start.' }
wsl -d Ubuntu-22.04 --exec sh -lc 'docker image inspect engram-sandbox:local >/dev/null 2>&1'
$engramSandboxExists = $LASTEXITCODE -eq 0
if ($Install -or $RebuildSandbox -or -not $engramSandboxExists) {
    wsl -d Ubuntu-22.04 --exec sh -lc "cd '$engramLinuxRoot' && docker build --quiet -f infra/sandbox.Dockerfile -t engram-sandbox:local ."
    if ($LASTEXITCODE -ne 0) { throw 'Sandbox image build failed.' }
} else {
    Write-Host 'Using the installed engram-sandbox:local image. Use -RebuildSandbox after changing its Dockerfile or dependencies.'
}
$engramManifest = @($engramAnchorEntry)
$engramModules = @('collective.embeddings-wsl','collective.serve','collective.agents')
if (Select-String -LiteralPath '.env.collective' -Pattern '^DECISION_PROVIDER=kev\s*$' -Quiet) {
    if (-not (Test-Path '.venv-kev/Scripts/python.exe')) { throw 'Install Kev first with scripts/install-kev.ps1.' }
    $engramModules += 'kev.serve'
}
foreach ($engramModule in $engramModules) {
    if (Test-Path -LiteralPath 'data/collective/processes.json') {
        $engramOldEntries = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json)
        $engramOldEntry = $engramOldEntries | Where-Object { $_.Module -eq $engramModule } | Select-Object -First 1
        if ($engramOldEntry) {
            $engramOldProcess = Get-Process -Id $engramOldEntry.Id -ErrorAction SilentlyContinue
            if ($engramOldProcess -and [Math]::Abs(($engramOldProcess.StartTime.ToUniversalTime() - ([datetime]$engramOldEntry.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
                $engramManifest += $engramOldEntry
                continue
            }
        }
    }
    $engramLogName = $engramModule.Replace('.','-')
    $engramExecutable = Join-Path $engramRoot '.venv-collective311/Scripts/python.exe'
    $engramArguments = @('-m',$engramModule)
    $engramWorking = $engramRoot
    if ($engramModule -eq 'collective.embeddings-wsl') {
        $engramExecutable = 'wsl.exe'
        $engramArguments = @('-d','Ubuntu-22.04','--exec','bash',"$engramLinuxRoot/scripts/embedding-service.sh",'run')
    }
    if ($engramModule -eq 'kev.serve') {
        $engramExecutable = Join-Path $engramRoot '.venv-kev/Scripts/python.exe'
        $engramArguments += @('--run','jaredpalmer/kev-0.8b@v1.0','--device','cpu','--port','8009')
        $engramWorking = Join-Path $engramRoot 'vendor/kev'
        $env:HF_HOME = Join-Path $engramRoot 'data/collective/huggingface'
        $env:HF_HUB_DISABLE_XET = '1'
        $env:OMP_NUM_THREADS = '4'
        $env:MKL_NUM_THREADS = '4'
    }
    $engramProc = Start-Process -FilePath $engramExecutable -ArgumentList $engramArguments -WorkingDirectory $engramWorking -WindowStyle Hidden -PassThru -RedirectStandardOutput "$engramRoot/data/collective/logs/$engramLogName.out.log" -RedirectStandardError "$engramRoot/data/collective/logs/$engramLogName.err.log"
    $engramManifest += @{ Id=$engramProc.Id; Module=$engramModule; Started=$engramProc.StartTime.ToUniversalTime().ToString('o') }
}
$engramManifest | ConvertTo-Json | Set-Content -LiteralPath 'data/collective/processes.json'
$engramDeadline = (Get-Date).AddMinutes(5)
$engramReady = $false
Write-Host 'Waiting for local services, including the GGUF embedding model...'
while ((Get-Date) -lt $engramDeadline) {
    try {
        $engramHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8088/api/health' -TimeoutSec 15
        $engramMissing = @('postgres','falkordb','qdrant','embeddings','worker','sandbox') | Where-Object { $engramHealth.services.$_.state -ne 'ready' }
        if ($engramModules -contains 'kev.serve' -and $engramHealth.services.kev.state -ne 'ready') { $engramMissing += 'kev' }
        if (-not $engramMissing) { $engramReady = $true; break }
    } catch { }
    Start-Sleep -Seconds 3
}
if (-not $engramReady) { throw 'Local services did not become ready. Inspect data/collective/logs and /api/health.' }
Write-Host 'ENGRAM Collective is ready at http://127.0.0.1:8088'
Write-Host 'Provider keys go in .env.collective. Restart the API and worker after editing keys.'
