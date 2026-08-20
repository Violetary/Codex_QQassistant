param(
    [string]$BotName = "",
    [int]$BotPort = 8000,
    [string]$OneBotApiUrl = "http://127.0.0.1:3000",
    [string]$OneBotToken = "",
    [switch]$QuickLogin
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BotScript = Join-Path $PSScriptRoot "start_bot_onebot.ps1"
$NapCatScript = Join-Path $PSScriptRoot "start_napcat.ps1"

if (-not (Test-Path -LiteralPath $BotScript)) {
    throw "Bot script not found: $BotScript"
}
if (-not (Test-Path -LiteralPath $NapCatScript)) {
    throw "NapCat script not found: $NapCatScript"
}

$BotArgs = @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $BotScript,
    "-Port", "$BotPort",
    "-OneBotApiUrl", $OneBotApiUrl
)

if ($BotName) {
    $BotArgs += @("-BotName", $BotName)
}

if ($OneBotToken) {
    $BotArgs += @("-OneBotToken", $OneBotToken)
}

$NapCatArgs = @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $NapCatScript
)
if ($QuickLogin) {
    $NapCatArgs += "-QuickLogin"
}

Write-Host "Opening bot service window..."
Start-Process -FilePath "powershell.exe" -ArgumentList $BotArgs -WorkingDirectory $ProjectRoot

Start-Sleep -Seconds 2

Write-Host "Opening NapCat login window..."
Start-Process -FilePath "powershell.exe" -ArgumentList $NapCatArgs -WorkingDirectory $ProjectRoot

Write-Host ""
Write-Host "After NapCat is online, configure OneBot:"
Write-Host "  Event POST URL: http://127.0.0.1:$BotPort/onebot"
Write-Host "  HTTP API URL:   $OneBotApiUrl"
Write-Host ""
Write-Host "Then test in QQ:"
Write-Host "  @友哈巴赫 水蓝蓝 查蛋"
Write-Host "  @友哈巴赫 波波拉 pvp"
