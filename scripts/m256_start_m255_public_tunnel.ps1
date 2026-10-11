[CmdletBinding()]
param(
    [string]$BoardUrl = 'http://192.168.0.2:8001',
    [int]$StartupTimeoutSeconds = 90,
    [switch]$ExternalVerificationPending
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$expectedBuildId = '0x4D395832'
$expectedMode = 'M254-dual-path-latest-only'
$expectedAppSha256 = 'c36d64f6a83aec7468af0b1f1c6a4c7ad5ec6d9280d642f86d35214d2f8fdd59'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cloudflared = Join-Path $workspace 'tools\cloudflared\cloudflared.exe'
$stateRoot = Join-Path $workspace 'tmp\m256_public'
$pidFile = Join-Path $stateRoot 'cloudflared.pid'
$urlFile = Join-Path $stateRoot 'public_url.txt'
$logFile = Join-Path $stateRoot 'cloudflared.log'
$originApp = Join-Path $stateRoot 'origin_app.js'
$publicApp = Join-Path $stateRoot 'public_app.js'
$resultPath = Join-Path $workspace 'deployment\mage_vl4b\M256_M255_PUBLIC_WEB_RESULT.json'
$startedProcess = $null
$gatePassed = $false

function Assert-M255Status {
    param([Parameter(Mandatory)]$Status, [Parameter(Mandatory)][string]$Where)
    if ($Status.build_id -ne $expectedBuildId) { throw "$Where build identity mismatch: $($Status.build_id)" }
    if ($Status.mode -ne $expectedMode) { throw "$Where mode mismatch: $($Status.mode)" }
    if ($Status.source_is_unbounded -ne $true) { throw "$Where unbounded-source contract is inactive" }
    if ($Status.status -ne 'running') { throw "$Where service is not running: $($Status.status)" }
    if ($Status.runtime_load_count -ne 1) { throw "$Where semantic runtime load count is not one: $($Status.runtime_load_count)" }
    if ($Status.fast_path.runtime_load_count -ne 1) { throw "$Where fast runtime load count is not one: $($Status.fast_path.runtime_load_count)" }
    if ($Status.worker_alive -ne $true) { throw "$Where worker is not alive" }
}

function Get-HttpFileSha256 {
    param([Parameter(Mandatory)][string]$Uri, [Parameter(Mandatory)][string]$Destination)
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 -Uri $Uri -OutFile $Destination
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash.ToLowerInvariant()
}

try {
    if (-not (Test-Path -LiteralPath $cloudflared -PathType Leaf)) {
        throw "cloudflared is missing: $cloudflared"
    }

    New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null

    $originStatus = Invoke-RestMethod -TimeoutSec 15 -Uri "$BoardUrl/api/4b/video/live/status"
    Assert-M255Status -Status $originStatus -Where 'origin'
    $originAppSha256 = Get-HttpFileSha256 -Uri "$BoardUrl/app.js?m256=origin" -Destination $originApp
    if ($originAppSha256 -ne $expectedAppSha256) {
        throw "origin M255 app.js hash mismatch: $originAppSha256"
    }

    if ((Test-Path -LiteralPath $pidFile) -and (Test-Path -LiteralPath $urlFile)) {
        $existingPid = [int](Get-Content -Raw -LiteralPath $pidFile)
        $existing = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($existing -and $existing.ProcessName -eq 'cloudflared') {
            throw "M256 tunnel is already running as PID $existingPid; use the recorded URL or stop it with m256_stop_m255_public_tunnel.ps1"
        }
    }

    Remove-Item -LiteralPath $pidFile,$urlFile,$logFile,$publicApp -Force -ErrorAction SilentlyContinue
    $arguments = @(
        'tunnel', '--no-autoupdate', '--protocol', 'http2',
        '--loglevel', 'info', '--logfile', $logFile, '--url', $BoardUrl
    )
    $startedProcess = Start-Process -FilePath $cloudflared -ArgumentList $arguments -PassThru -WindowStyle Hidden
    Set-Content -LiteralPath $pidFile -Value $startedProcess.Id -Encoding ascii

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $publicUrl = $null
    while ((Get-Date) -lt $deadline) {
        if ($startedProcess.HasExited) { throw "cloudflared exited early; inspect $logFile" }
        if (Test-Path -LiteralPath $logFile) {
            $match = Select-String -LiteralPath $logFile -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches | Select-Object -Last 1
            if ($match) { $publicUrl = $match.Matches[0].Value; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $publicUrl) { throw "public URL was not produced; inspect $logFile" }

    Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding ascii
    if ($ExternalVerificationPending) {
        $gatePassed = $true
        Write-Output 'M256_PUBLIC_TUNNEL_STARTED_EXTERNAL_VERIFICATION_PENDING'
        Write-Output "PUBLIC_URL=$publicUrl"
        Write-Output "PID=$($startedProcess.Id)"
        Write-Output "ORIGIN_BUILD_ID=$($originStatus.build_id)"
        Write-Output "ORIGIN_APP_JS_SHA256=$originAppSha256"
        exit 0
    }

    $publicStatus = $null
    $publicPage = $null
    $verifyDeadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $verifyDeadline) {
        try {
            $publicPage = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$publicUrl/?m256=verify"
            $publicStatus = Invoke-RestMethod -TimeoutSec 15 -Uri "$publicUrl/api/4b/video/live/status?m256=verify"
            break
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if ($null -eq $publicPage -or $null -eq $publicStatus) { throw 'public endpoint did not become reachable in time' }
    if ($publicPage.StatusCode -ne 200) { throw "public page returned HTTP $($publicPage.StatusCode)" }
    if ($publicPage.Content -notmatch '人物动作与刀具安全监控') { throw 'public page identity text is missing' }
    Assert-M255Status -Status $publicStatus -Where 'public'

    $publicAppSha256 = Get-HttpFileSha256 -Uri "$publicUrl/app.js?m256=public" -Destination $publicApp
    if ($publicAppSha256 -ne $expectedAppSha256) {
        throw "public M255 app.js hash mismatch: $publicAppSha256"
    }
    if ($publicStatus.fast_path.processed_frames -ne $originStatus.fast_path.processed_frames) {
        Write-Warning 'Processed-frame count changed during tunnel verification; this is allowed because the active source can keep sending frames.'
    }

    $result = [ordered]@{
        date = (Get-Date).ToString('yyyy-MM-dd')
        gate = 'M256-M255-public-HTTPS-access'
        status = 'PASS'
        classification = 'Temporary public HTTPS reachability and exact M255 static/runtime identity PASS; no new model inference, accuracy, performance, or complete L7 Web acceptance claim.'
        public_url = $publicUrl
        tunnel_pid = $startedProcess.Id
        tunnel_provider = 'Cloudflare Quick Tunnel'
        temporary_url = $true
        authentication_enabled = $false
        origin_url = $BoardUrl
        build_id = $publicStatus.build_id
        mode = $publicStatus.mode
        service_status = $publicStatus.status
        worker_alive = $publicStatus.worker_alive
        semantic_runtime_load_count = $publicStatus.runtime_load_count
        fast_runtime_load_count = $publicStatus.fast_path.runtime_load_count
        served_app_js_sha256 = $publicAppSha256
        expected_m255_app_js_sha256 = $expectedAppSha256
        model_or_fpga_restarted = $false
        board_boot_dtb_cma_partitions_changed = $false
        stable_rollback_preserved = $true
        security_note = 'Anyone holding the URL can access the page. Stop the tunnel after the remote demonstration.'
        state_directory = 'tmp/m256_public'
    }
    $json = $result | ConvertTo-Json -Depth 8
    $temporaryResult = "$resultPath.partial"
    [IO.File]::WriteAllText($temporaryResult, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporaryResult -Destination $resultPath -Force
    $resultSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resultPath).Hash.ToLowerInvariant()

    $gatePassed = $true
    Write-Output 'M256_M255_PUBLIC_WEB_PASS'
    Write-Output "PUBLIC_URL=$publicUrl"
    Write-Output "PID=$($startedProcess.Id)"
    Write-Output "BUILD_ID=$($publicStatus.build_id)"
    Write-Output "APP_JS_SHA256=$publicAppSha256"
    Write-Output "RESULT=$resultPath"
    Write-Output "RESULT_SHA256=$resultSha256"
} finally {
    if (-not $gatePassed -and $null -ne $startedProcess) {
        $live = Get-Process -Id $startedProcess.Id -ErrorAction SilentlyContinue
        if ($live -and $live.ProcessName -eq 'cloudflared') {
            Stop-Process -Id $startedProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $pidFile,$urlFile -Force -ErrorAction SilentlyContinue
    }
}
