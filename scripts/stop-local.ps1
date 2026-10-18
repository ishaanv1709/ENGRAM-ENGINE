$ErrorActionPreference = 'Stop'
$engramRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $engramRoot
if (Test-Path -LiteralPath 'data/collective/processes.json') {
    foreach ($engramEntry in (Get-Content -LiteralPath 'data/collective/processes.json' -Raw | ConvertFrom-Json)) {
        $engramProc = Get-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
        if ($engramProc -and [Math]::Abs(($engramProc.StartTime.ToUniversalTime() - ([datetime]$engramEntry.Started).ToUniversalTime()).TotalSeconds) -lt 0.01) {
            if ($engramEntry.Module -ne 'collective.wsl-anchor') {
                $engramChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($engramEntry.Id)" | Where-Object { $_.CommandLine -like "*$($engramEntry.Module)*" }
                foreach ($engramChild in $engramChildren) { Stop-Process -Id $engramChild.ProcessId -ErrorAction SilentlyContinue }
            }
            Stop-Process -Id $engramEntry.Id -ErrorAction SilentlyContinue
        }
    }
}
$engramLinuxRoot = '/mnt/' + $engramRoot.Substring(0,1).ToLower() + $engramRoot.Substring(2).Replace('\','/')
wsl -d Ubuntu-22.04 --exec bash "$engramLinuxRoot/scripts/embedding-service.sh" stop
Write-Host 'Managed app processes stopped. Database containers and persistent data were preserved.'
