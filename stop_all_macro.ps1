$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EscapedRoot = [regex]::Escape($ProjectRoot)
$PidPath = Join-Path $ProjectRoot "macro.pid"

Write-Host "Stopping Korail macro processes..."

$matches = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    ($_.CommandLine -match $EscapedRoot) -and
    ($_.CommandLine -match "run_macro.ps1|korail_cancel_macro.main|native_host.py")
}

$count = 0
foreach ($process in $matches) {
    try {
        Write-Host ("Stopping PID {0}: {1}" -f $process.ProcessId, $process.Name)
        Stop-Process -Id $process.ProcessId -Force
        $count++
    } catch {
        Write-Host ("Could not stop PID {0}" -f $process.ProcessId)
    }
}

if (Test-Path $PidPath) {
    Remove-Item $PidPath -Force
}

Write-Host ("Stopped processes: {0}" -f $count)
Write-Host "Done."

