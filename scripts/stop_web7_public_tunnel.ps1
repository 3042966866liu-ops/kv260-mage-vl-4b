$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateRoot = Join-Path $workspace "tmp\web7_public"
$pidFile = Join-Path $stateRoot "cloudflared.pid"
$urlFile = Join-Path $stateRoot "public_url.txt"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "WEB7_TUNNEL_NOT_RUNNING"
    exit 0
}

$recordedPid = [int](Get-Content -Raw -LiteralPath $pidFile)
$process = Get-Process -Id $recordedPid -ErrorAction SilentlyContinue
if ($process -and $process.ProcessName -eq "cloudflared") {
    Stop-Process -Id $recordedPid
    $process.WaitForExit(10000) | Out-Null
    Write-Output "WEB7_TUNNEL_STOPPED"
    Write-Output "PID=$recordedPid"
} else {
    Write-Output "WEB7_TUNNEL_PROCESS_ALREADY_EXITED"
}

Remove-Item -LiteralPath $pidFile,$urlFile -Force -ErrorAction SilentlyContinue
