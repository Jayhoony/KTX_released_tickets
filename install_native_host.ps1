param(
    [Parameter(Mandatory = $true)]
    [string]$ExtensionId
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$HostDir = Join-Path $ProjectRoot "native_host"
$LauncherPath = Join-Path $HostDir "native_host_launcher.cmd"
$ManifestPath = Join-Path $HostDir "com.ktx_released_tickets.macro.json"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

function Get-SystemPython {
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @($pyLauncher.Source, "-3")
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }

    return $null
}

function Invoke-SystemPython {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$PythonCommand,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$PythonArgs
    )

    if ($PythonCommand.Length -gt 1) {
        & $PythonCommand[0] $PythonCommand[1] @PythonArgs
    } else {
        & $PythonCommand[0] @PythonArgs
    }
}

function Test-VenvPython {
    if (!(Test-Path $VenvPython)) {
        return $false
    }

    & $VenvPython --version *> $null
    return ($LASTEXITCODE -eq 0)
}

if (!(Test-VenvPython)) {
    $VenvDir = Join-Path $ProjectRoot ".venv"
    if (Test-Path $VenvDir) {
        Write-Host "Virtual environment is broken. Recreating..."
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }

    $PythonCommand = Get-SystemPython
    if ($null -eq $PythonCommand) {
        Write-Host "ERROR: Python was not found."
        Write-Host "Install Python 3.11+ first, then run this installer again."
        Write-Host "Download: https://www.python.org/downloads/windows/"
        exit 1
    }

    Write-Host "Creating virtual environment..."
    Invoke-SystemPython $PythonCommand -m venv .venv
}

Write-Host "Installing packages..."
& $VenvPython -m pip install -r requirements.txt

$manifest = @{
    name = "com.ktx_released_tickets.macro"
    description = "Korail macro native launcher"
    path = $LauncherPath
    type = "stdio"
    allowed_origins = @("chrome-extension://$ExtensionId/")
} | ConvertTo-Json -Depth 5

Set-Content -Path $ManifestPath -Value $manifest -Encoding UTF8

$RegistryPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.ktx_released_tickets.macro"
New-Item -Path $RegistryPath -Force | Out-Null
Set-ItemProperty -Path $RegistryPath -Name "(default)" -Value $ManifestPath

Write-Host "Native host installed:"
Write-Host $ManifestPath
Write-Host ""
Write-Host "You can now use the Run Macro button in the Chrome extension popup."
