param(
    [Parameter(Mandatory = $true)]
    [string]$QQ,
    [string]$NapCatConfigDir = "",
    [string]$PostUrl = "http://127.0.0.1:8000/onebot",
    [int]$HttpPort = 3000,
    [string]$Token = ""
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot

if (-not $NapCatConfigDir) {
    $Candidates = @(
        (Join-Path $ProjectRoot "tools\napcat\config"),
        (Join-Path $env:USERPROFILE "NapCat\config"),
        (Join-Path $env:APPDATA "NapCat\config")
    )
    $NapCatConfigDir = ($Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
    if (-not $NapCatConfigDir) {
        $NapCatConfigDir = Join-Path $ProjectRoot "tools\napcat\config"
    }
}

New-Item -ItemType Directory -Path $NapCatConfigDir -Force | Out-Null

$Config = [ordered]@{
    network = [ordered]@{
        httpServers = @(
            [ordered]@{
                name = "rockbot_http_api"
                enable = $true
                host = "127.0.0.1"
                port = $HttpPort
                token = $Token
                enableCors = $true
            }
        )
        httpClients = @(
            [ordered]@{
                name = "rockbot_event_post"
                enable = $true
                url = $PostUrl
                token = $Token
                messagePostFormat = "array"
                reportSelfMessage = $false
            }
        )
        websocketServers = @()
        websocketClients = @()
    }
}

$OutputPath = Join-Path $NapCatConfigDir "onebot11_$QQ.json"
$Config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

Write-Host "Wrote NapCat OneBot config:"
Write-Host $OutputPath
Write-Host ""
Write-Host "If NapCat WebUI shows a different config directory, rerun with:"
Write-Host ".\scripts\write_napcat_onebot_config.ps1 -QQ $QQ -NapCatConfigDir '<that config folder>'"
