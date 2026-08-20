param(
    [string]$BridgeUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$HealthUrl = "$($BridgeUrl.TrimEnd('/'))/health"
Write-Host "Checking $HealthUrl"
$Result = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
$Result | ConvertTo-Json -Depth 10
