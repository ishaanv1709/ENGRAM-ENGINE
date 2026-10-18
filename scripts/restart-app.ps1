param([switch]$VerifyDemoState)
$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$engramBefore = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json) | Where-Object { $_.Module -in @('collective.serve','collective.agents') }
foreach ($engramEntry in $engramBefore) {
    $engramProc = Get-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
    if ($engramProc -and [Math]::Abs(($engramProc.StartTime.ToUniversalTime() - ([datetime]$engramEntry.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$($engramEntry.Id)" | Where-Object { $_.CommandLine -like "*-m $($engramEntry.Module)*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
    }
}
& '.\scripts\start-local.ps1'
if ($LASTEXITCODE -ne 0) { throw 'Application restart failed.' }
$engramAfter = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json) | Where-Object { $_.Module -in @('collective.serve','collective.agents') }
foreach ($engramOld in $engramBefore) {
    $engramNew = $engramAfter | Where-Object Module -eq $engramOld.Module | Select-Object -First 1
    if (-not $engramNew -or $engramNew.Id -eq $engramOld.Id) { throw "Process did not restart: $($engramOld.Module)" }
}
@{ before=$engramBefore; after=$engramAfter; actual_app_process_restart=$true; verified_at=(Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath 'data/collective/restart-process-proof.json'
if ($VerifyDemoState) {
    & '.\.venv-collective311\Scripts\python.exe' 'scripts/demo-restart-state.py' verify
    if ($LASTEXITCODE -ne 0) { throw 'Persistent demo state did not survive.' }
}
