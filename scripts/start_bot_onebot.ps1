param(
    [string]$PythonPath = "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    [string]$BotName = "",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [string]$OneBotApiUrl = "http://127.0.0.1:3000",
    [string]$OneBotToken = "",
    [ValidateSet("base64", "file-uri", "path")]
    [string]$ImageMode = "base64",
    [double]$ApiTimeout = 15,
    [int]$SendRetries = 2,
    [double]$SendRetryDelay = 0.35,
    [string]$RuntimeLog = "logs/onebot-runtime.log"
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
    "--onebot-image-mode", $ImageMode,
    "--onebot-api-timeout", "$ApiTimeout",
    "--onebot-send-retries", "$SendRetries",
    "--onebot-send-retry-delay", "$SendRetryDelay",
    "--onebot-runtime-log", $RuntimeLog
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
Write-Host "Runtime log: $RuntimeLog"
Write-Host ""

& $PythonPath @ArgsList
