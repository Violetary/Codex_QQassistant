param(
    [string]$PythonPath = "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    [string]$BotName = "",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [string]$OneBotApiUrl = "http://127.0.0.1:3000",
    [string]$OneBotToken = "",
    [ValidateSet("base64", "file-uri", "path")]
    [string]$ImageMode = "base64"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python runtime not found: $PythonPath"
}

$ArgsList = @(
    "-m", "rockbot.cli",
    "--serve",
    "--onebot",
    "--host", $HostAddress,
    "--port", "$Port",
    "--local-db", "data/pets.seed.json",
    "--no-sample",
    "--onebot-api-url", $OneBotApiUrl,
    "--onebot-image-mode", $ImageMode
)

if ($BotName) {
    $ArgsList += @("--bot-name", $BotName)
}

if ($OneBotToken) {
    $ArgsList += @("--onebot-token", $OneBotToken)
}

Write-Host "Starting Rock Kingdom bot..."
Write-Host "Bridge: http://$HostAddress`:$Port/onebot"
Write-Host "OneBot API: $OneBotApiUrl"
Write-Host "Image mode: $ImageMode"
Write-Host ""

& $PythonPath @ArgsList
