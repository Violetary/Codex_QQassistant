param(
    [string]$NapCatDir = "",
    [switch]$QuickLogin,
    [switch]$AdminLauncher
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $NapCatDir) {
    $ShellDir = Join-Path $ProjectRoot "tools\napcat\shell"
    $BootDir = Join-Path $ProjectRoot "tools\napcat\bootmain"
    if (Test-Path -LiteralPath $ShellDir) {
        $NapCatDir = $ShellDir
    } else {
        $NapCatDir = $BootDir
    }
}

if (-not (Test-Path -LiteralPath $NapCatDir)) {
    throw "NapCat directory not found: $NapCatDir"
}

if (Test-Path -LiteralPath (Join-Path $NapCatDir "launcher-user.bat")) {
    $BatchName = if ($AdminLauncher) { "launcher.bat" } else { "launcher-user.bat" }
} else {
    $BatchName = if ($QuickLogin) { "napcat.quick.bat" } else { "napcat.bat" }
}

$BatchPath = Join-Path $NapCatDir $BatchName
if (-not (Test-Path -LiteralPath $BatchPath)) {
    throw "NapCat launcher not found: $BatchPath"
}

Write-Host "Starting NapCat launcher: $BatchPath"
Write-Host "If this is the first launch, finish QQ login in the NapCat/QQ window."

Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "`"$BatchPath`"") -WorkingDirectory $NapCatDir
