param([ValidateSet('prepare','complete','versions','infrastructure','showcase','showcase-checks','workflow-checks','all-checks','track2-prepare','track2-recover')][string]$Stage = 'prepare')
$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$engramWasRunning = $false
$engramEntry = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json) | Where-Object Module -eq 'collective.agents' | Select-Object -First 1
if ($engramEntry) {
    $engramProc = Get-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
    if ($engramProc -and [Math]::Abs(($engramProc.StartTime.ToUniversalTime() - ([datetime]$engramEntry.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
        $engramWasRunning = $true
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$($engramEntry.Id)" | Where-Object { $_.CommandLine -like '*-m collective.agents*' } | ForEach-Object { Stop-Process -Id $_.ProcessId }
        Stop-Process -Id $engramEntry.Id
    }
}
$engramExit = 1
$engramPreviousProviderTests = $env:ENGRAM_PROVIDER_TESTS
try {
    # These stages exercise real infrastructure without provider inference.
    $env:ENGRAM_PROVIDER_TESTS = '0'
    if ($Stage -in @('track2-prepare','track2-recover')) {
        & '.\.venv-collective311\Scripts\python.exe' -u 'scripts/track2-evaluation.py' ($Stage.Replace('track2-',''))
    } elseif ($Stage -eq 'all-checks') {
        & '.\.venv-collective311\Scripts\python.exe' 'scripts/test-local.py'
    } elseif ($Stage -eq 'workflow-checks') {
        & '.\.venv-collective311\Scripts\python.exe' 'scripts/test-local.py' 'collective/tests/test_workflows.py'
    } elseif ($Stage -eq 'showcase-checks') {
        & '.\.venv-collective311\Scripts\python.exe' 'scripts/test-local.py' 'collective/tests/test_coordination.py'
    } elseif ($Stage -eq 'showcase') {
        & '.\.venv-collective311\Scripts\python.exe' -u 'scripts/measure-showcase.py'
    } elseif ($Stage -eq 'infrastructure') {
        & '.\.venv-collective311\Scripts\python.exe' -u 'scripts/prepare-film-evidence.py'
    } elseif ($Stage -eq 'versions') {
        & '.\.venv-collective311\Scripts\python.exe' -u 'scripts/verify-versioned-demo.py'
    } else {
        & '.\.venv-collective311\Scripts\python.exe' -u 'scripts/verify-causal-demo.py' $Stage
    }
    $engramExit = $LASTEXITCODE
} finally {
    $env:ENGRAM_PROVIDER_TESTS = $engramPreviousProviderTests
    if ($engramWasRunning) { & '.\scripts\start-local.ps1' }
}
exit $engramExit
