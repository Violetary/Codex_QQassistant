param(
    [string]$PythonPath = 'C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [int]$Port = 8000,
    [string]$OneBotApiUrl = 'http://127.0.0.1:3000',
    [ValidateSet('base64', 'file-uri', 'path')]
    [string]$ImageMode = 'base64',
    [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw ('Python runtime not found: ' + $PythonPath)
}

function CheckLastExit {
    param([string]$Title)
    if ($LASTEXITCODE -ne 0) {
        throw ('Step failed: ' + $Title)
    }
}

Write-Host ''
Write-Host '==> Build pet database'
& $PythonPath 'scripts\build_pet_database.py'
CheckLastExit 'Build pet database'

Write-Host ''
Write-Host '==> Build PVP recommendations'
& $PythonPath 'scripts\build_pvp_database.py'
CheckLastExit 'Build PVP recommendations'

Write-Host ''
Write-Host '==> Sync BWiki body data'
& $PythonPath 'scripts\sync_body_from_bwiki.py' '--workers' '1' '--delay' '0.25' '--retries' '5' '--allow-errors'
CheckLastExit 'Sync BWiki body data'

Write-Host ''
Write-Host '==> Pre-render cards'
& $PythonPath 'scripts\pre_render_cards.py' '--force'
CheckLastExit 'Pre-render cards'

Write-Host ''
Write-Host '==> Run unit tests'
& $PythonPath '-m' 'unittest' 'discover' '-s' 'tests' '-v'
CheckLastExit 'Run unit tests'

Write-Host ''
Write-Host '==> Verify every local query'
& $PythonPath 'scripts\verify_all_queries.py'
CheckLastExit 'Verify every local query'

Write-Host ''
Write-Host '==> Verify BWiki index'
& $PythonPath 'scripts\verify_bwiki_index.py'
CheckLastExit 'Verify BWiki index'

if ($NoRestart) {
    Write-Host ''
    Write-Host 'Update complete. Restart skipped by -NoRestart.'
    exit 0
}

Write-Host ''
Write-Host ('==> Restart bot bridge on port ' + [string]$Port)
$listeners = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq 'Listen' } |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($processId in $listeners) {
    Write-Host ('Stopping process ' + [string]$processId)
    Stop-Process -Id $processId -Force
}

Start-Sleep -Seconds 1
$startScript = Join-Path $PSScriptRoot 'start_bot_onebot.ps1'
$startArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $startScript,
    '-Port', [string]$Port,
    '-OneBotApiUrl', $OneBotApiUrl,
    '-ImageMode', $ImageMode
)
Start-Process -FilePath powershell.exe -ArgumentList $startArgs -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Start-Sleep -Seconds 2
$healthUrl = 'http://127.0.0.1:' + [string]$Port + '/health'
$health = Invoke-RestMethod -Uri $healthUrl
if (-not $health.ok) {
    throw 'Bot bridge health check failed.'
}

Write-Host ''
Write-Host ('Update complete. Bot bridge is healthy on http://127.0.0.1:' + [string]$Port)
