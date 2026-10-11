[CmdletBinding()]
param(
    [string]$BoardUrl = 'http://192.168.0.2:8001',
    [int]$StartupTimeoutSeconds = 75
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cloudflared = Join-Path $workspace 'tools\cloudflared\cloudflared.exe'
$stateRoot = Join-Path $workspace 'tmp\m212_public'
$pidFile = Join-Path $stateRoot 'cloudflared.pid'
$urlFile = Join-Path $stateRoot 'public_url.txt'
$logFile = Join-Path $stateRoot 'cloudflared.log'

if (-not (Test-Path -LiteralPath $cloudflared -PathType Leaf)) {
    throw "cloudflared is missing: $cloudflared"
}

$health = Invoke-RestMethod -TimeoutSec 15 -Uri "$BoardUrl/api/health"
if ($health.build_id -ne '0x4D395832') { throw "M212 build identity mismatch: $($health.build_id)" }
if ($health.mode -ne 'continuous-latest-only') { throw "M212 mode mismatch: $($health.mode)" }
if ($health.source_is_unbounded -ne $true) { throw 'M212 unbounded-source contract is not active' }
if ($health.status -notin @('idle','loading','ready','busy')) { throw "M212 health is not tunnel-safe: $($health.status)" }

New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
if ((Test-Path -LiteralPath $pidFile) -and (Test-Path -LiteralPath $urlFile)) {
    $existingPid = [int](Get-Content -Raw -LiteralPath $pidFile)
    $existing = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($existing -and $existing.ProcessName -eq 'cloudflared') {
        $existingUrl = (Get-Content -Raw -LiteralPath $urlFile).Trim()
        Write-Output 'M214_TUNNEL_ALREADY_RUNNING'
        Write-Output "PID=$existingPid"
        Write-Output "PUBLIC_URL=$existingUrl"
        exit 0
    }
}

Remove-Item -LiteralPath $pidFile,$urlFile,$logFile -Force -ErrorAction SilentlyContinue
$arguments = @(
    'tunnel', '--no-autoupdate', '--protocol', 'http2',
    '--loglevel', 'info', '--logfile', $logFile, '--url', $BoardUrl
)
$process = Start-Process -FilePath $cloudflared -ArgumentList $arguments -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$publicUrl = $null
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) { throw "M214 cloudflared exited; inspect $logFile" }
    if (Test-Path -LiteralPath $logFile) {
        $match = Select-String -LiteralPath $logFile -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches | Select-Object -Last 1
        if ($match) { $publicUrl = $match.Matches[0].Value; break }
    }
    Start-Sleep -Milliseconds 500
}
if (-not $publicUrl) { throw "M214 public URL was not produced; inspect $logFile" }

Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding ascii
Write-Output 'M214_M212_PUBLIC_TUNNEL_STARTED'
Write-Output "PID=$($process.Id)"
Write-Output "PUBLIC_URL=$publicUrl"
Write-Output "BOARD_URL=$BoardUrl"
Write-Output "LOG=$logFile"
