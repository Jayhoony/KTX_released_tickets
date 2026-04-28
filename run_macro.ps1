$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ConfigPath = Join-Path $ProjectRoot "config.ini"
$ExampleConfigPath = Join-Path $ProjectRoot "config.example.ini"

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

if (!(Test-Path $ConfigPath)) {
    Copy-Item $ExampleConfigPath $ConfigPath
    Write-Host "config.ini was missing, so it was created from config.example.ini."
}

if (!(Test-Path $VenvPython)) {
    $PythonCommand = Get-SystemPython
    if ($null -eq $PythonCommand) {
        Write-Host "ERROR: Python was not found."
        Write-Host "Install Python 3.11+ first, then run this again."
        Write-Host "Download: https://www.python.org/downloads/windows/"
        exit 1
    }

    Write-Host "Creating virtual environment..."
    Invoke-SystemPython $PythonCommand -m venv .venv
}

Write-Host "Checking packages..."
& $VenvPython -m pip install --upgrade --force-reinstall -r requirements.txt

Write-Host "Running macro..."
& $VenvPython -m korail_cancel_macro.main --config config.ini

Write-Host ""
Read-Host "Press Enter to close"
