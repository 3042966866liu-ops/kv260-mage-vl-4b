[CmdletBinding()]
param(
    [string]$BoardUrl = 'http://192.168.0.2:8001',
    [string]$ResultPath = 'deployment\mage_vl4b\M214_M212_WINDOWS_HTTP_RESULT.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$result = Join-Path $workspace $ResultPath
$partial = "$result.partial"

$health = Invoke-RestMethod -Uri "$BoardUrl/api/health" -TimeoutSec 15
$status = Invoke-RestMethod -Uri "$BoardUrl/api/4b/video/live/status" -TimeoutSec 15
$page = Invoke-WebRequest -Uri "$BoardUrl/" -TimeoutSec 15
$checks = [ordered]@{
    page_http_200 = ($page.StatusCode -eq 200)
    page_has_camera_ui = ($page.Content -match 'camera|摄像|视频流')
    build_id_exact = ($health.build_id -eq '0x4D395832')
    kernel_exact = ($health.kernel -eq 'mage_m120_m89x2_0')
    latest_only_mode = ($health.mode -eq 'continuous-latest-only')
    unbounded_source_contract = ($health.source_is_unbounded -eq $true)
    status_endpoint_consistent = (($status | ConvertTo-Json -Compress -Depth 12) -eq ($health | ConvertTo-Json -Compress -Depth 12))
}
$pass = -not ($checks.Values -contains $false)
$payload = [ordered]@{
    date = '2026-09-01'
    gate = 'M214-Windows-to-real-KV260-M212-HTTP-control-plane'
    status = $(if($pass){'PASS'}else{'FAIL'})
    classification = 'Windows-to-real-KV260 HTTP page and API reachability only; no camera frames, continuous model inference, FPGA video proof, public HTTPS or latency acceptance.'
    board_url = $BoardUrl
    checks = $checks
    page_bytes = $page.RawContentLength
    health = $health
    continuous_stream_inference_executed = $false
    public_https_deployed = $false
    stable_rollback_preserved = $true
    next_gate = 'After explicit public-camera exposure authorization, create HTTPS tunnel and submit a real continuous browser-camera stream.'
}
New-Item -ItemType Directory -Force -Path (Split-Path $result) | Out-Null
$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $partial -Encoding utf8
Move-Item -LiteralPath $partial -Destination $result -Force
if(-not $pass){ throw "M214 Windows HTTP gate failed; evidence preserved at $result" }
Write-Output 'M214_M212_WINDOWS_HTTP_PASS'
Write-Output "RESULT=$result"
