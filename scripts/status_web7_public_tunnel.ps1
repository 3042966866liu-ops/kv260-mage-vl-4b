$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateRoot = Join-Path $workspace "tmp\web7_public"
$pidFile = Join-Path $stateRoot "cloudflared.pid"
$urlFile = Join-Path $stateRoot "public_url.txt"

if (-not ((Test-Path -LiteralPath $pidFile) -and (Test-Path -LiteralPath $urlFile))) {
    Write-Output "WEB7_TUNNEL_NOT_RUNNING"
    exit 1
}

$recordedPid = [int](Get-Content -Raw -LiteralPath $pidFile)
$publicUrl = (Get-Content -Raw -LiteralPath $urlFile).Trim()
$process = Get-Process -Id $recordedPid -ErrorAction SilentlyContinue
if (-not ($process -and $process.ProcessName -eq "cloudflared")) {
    Write-Output "WEB7_TUNNEL_STALE_STATE"
    exit 1
}

$health = Invoke-RestMethod -TimeoutSec 15 -Uri "$publicUrl/api/health"
Write-Output "WEB7_TUNNEL_RUNNING"
Write-Output "PID=$recordedPid"
Write-Output "PUBLIC_URL=$publicUrl"
Write-Output "REMOTE_STATUS=$($health.status)"
Write-Output "RUNTIME_INSTANCE_ID=$($health.runtime_instance_id)"
Write-Output "BUILD_ID=$($health.build_id)"
Write-Output "CPU_LINEAR_FALLBACK=$($health.cpu_linear_fallback)"
