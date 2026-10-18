param([switch]$Memory, [switch]$Reuse, [switch]$Resume)
$ErrorActionPreference = 'Stop'
if ($Memory -and $Reuse) { throw 'Select either memory correction or procedure reuse verification.' }
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
$engramWasRunning = $false
if (Test-Path -LiteralPath 'data/collective/processes.json') {
    $engramEntry = @(Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json) | Where-Object Module -eq 'collective.agents' | Select-Object -First 1
    if ($engramEntry) {
        $engramProcess = Get-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
        if ($engramProcess -and [Math]::Abs(($engramProcess.StartTime.ToUniversalTime() - ([datetime]$engramEntry.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
            $engramWasRunning = $true
            Get-CimInstance Win32_Process -Filter "ParentProcessId=$($engramEntry.Id)" | Where-Object { $_.CommandLine -like '*-m collective.agents*' } | ForEach-Object { Stop-Process -Id $_.ProcessId }
            Stop-Process -Id $engramEntry.Id
        }
    }
}
$engramVerificationExit = 1
try {
    $engramScript = if ($Memory) { 'scripts/verify-live-memory.py' } elseif ($Reuse) { 'scripts/verify-procedure-reuse.py' } else { 'scripts/verify-live-workflow.py' }
    $engramArguments = @('-u', $engramScript)
    if ($Resume -and -not $Memory -and -not $Reuse) { $engramArguments += '--resume' }
    & '.\.venv-collective311\Scripts\python.exe' @engramArguments
    $engramVerificationExit = $LASTEXITCODE
} finally {
    if ($engramWasRunning) { & '.\scripts\start-local.ps1' }
}
exit $engramVerificationExit
