param(
    [string]$LocalUrl = "http://127.0.0.1:18081",
    [int]$StartupTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cloudflared = Join-Path $workspace "tools\cloudflared\cloudflared.exe"
$stateRoot = Join-Path $workspace "tmp\web7_public"
$pidFile = Join-Path $stateRoot "cloudflared.pid"
$urlFile = Join-Path $stateRoot "public_url.txt"
$logFile = Join-Path $stateRoot "cloudflared.log"

if (-not (Test-Path -LiteralPath $cloudflared -PathType Leaf)) {
    throw "cloudflared is missing: $cloudflared"
}

New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null

try {
    $health = Invoke-RestMethod -TimeoutSec 8 -Uri "$LocalUrl/api/health"
} catch {
    throw "Local Web service is not reachable at ${LocalUrl}: $($_.Exception.Message)"
}
if ($health.status -ne "ready") {
    throw "Local Web service is not ready: $($health.status)"
}

if ((Test-Path -LiteralPath $pidFile) -and (Test-Path -LiteralPath $urlFile)) {
    $existingPid = [int](Get-Content -Raw -LiteralPath $pidFile)
    $existing = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($existing -and $existing.ProcessName -eq "cloudflared") {
        $existingUrl = (Get-Content -Raw -LiteralPath $urlFile).Trim()
        Write-Output "WEB7_TUNNEL_ALREADY_RUNNING"
        Write-Output "PID=$existingPid"
        Write-Output "PUBLIC_URL=$existingUrl"
        exit 0
    }
}

Remove-Item -LiteralPath $pidFile,$urlFile,$logFile -Force -ErrorAction SilentlyContinue
$arguments = @(
    "tunnel",
    "--no-autoupdate",
    "--protocol", "http2",
    "--loglevel", "info",
    "--logfile", $logFile,
    "--url", $LocalUrl
)
$process = Start-Process -FilePath $cloudflared -ArgumentList $arguments -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$publicUrl = $null
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) {
        throw "cloudflared exited during startup. Inspect $logFile"
    }
    if (Test-Path -LiteralPath $logFile) {
        $match = Select-String -LiteralPath $logFile -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches |
            Select-Object -Last 1
        if ($match) {
            $publicUrl = $match.Matches[0].Value
            break
        }
    }
    Start-Sleep -Milliseconds 500
}

if (-not $publicUrl) {
    throw "Quick Tunnel URL was not produced within $StartupTimeoutSeconds seconds. Inspect $logFile"
}

Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding ascii
Write-Output "WEB7_TUNNEL_STARTED"
Write-Output "PID=$($process.Id)"
Write-Output "PUBLIC_URL=$publicUrl"
Write-Output "LOCAL_URL=$LocalUrl"
Write-Output "LOG=$logFile"
