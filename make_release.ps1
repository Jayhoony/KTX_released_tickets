param(
    [string]$Version = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path $PSScriptRoot).Path
$releaseName = "KTX_released_tickets-$Version"
$distDir = Join-Path $root "dist"
$stageDir = Join-Path $distDir $releaseName
$zipPath = Join-Path $distDir "$releaseName.zip"

$excludedDirs = @(
    ".git",
    ".venv",
    "dist",
    "__pycache__"
)

$excludedFiles = @(
    "config.ini",
    "macro.log",
    "macro.pid",
    "native_host\com.ktx_released_tickets.macro.json"
)

$excludedExtensions = @(
    ".pyc",
    ".pyo",
    ".log",
    ".pid"
)

function Test-ExcludedPath {
    param([string]$Path)

    $relative = [System.IO.Path]::GetRelativePath($root, $Path)
    $parts = $relative -split '[\\/]'

    foreach ($dir in $excludedDirs) {
        if ($parts -contains $dir) {
            return $true
        }
    }

    foreach ($file in $excludedFiles) {
        if ($relative -ieq $file) {
            return $true
        }
    }

    if ($excludedExtensions -contains ([System.IO.Path]::GetExtension($Path))) {
        return $true
    }

    return $false
}

if (Test-Path -LiteralPath $stageDir) {
    Remove-Item -LiteralPath $stageDir -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

Get-ChildItem -Path $root -Recurse -Force -File |
    Where-Object { -not (Test-ExcludedPath $_.FullName) } |
    ForEach-Object {
        $relative = [System.IO.Path]::GetRelativePath($root, $_.FullName)
        $target = Join-Path $stageDir $relative
        $targetDir = Split-Path -Parent $target
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $stageDir -Recurse -Force

Write-Host "Release package created:"
Write-Host $zipPath
