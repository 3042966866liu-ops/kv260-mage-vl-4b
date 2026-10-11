[CmdletBinding()]
param(
    [string]$StateRoot = 'tmp\m212_public',
    [string]$ResultPath = 'deployment\mage_vl4b\M216_M212_PUBLIC_HTTPS_RESULT.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$state = Join-Path $workspace $StateRoot
$publicUrl = (Get-Content -Raw -LiteralPath (Join-Path $state 'public_url.txt')).Trim()
$pidValue = [int](Get-Content -Raw -LiteralPath (Join-Path $state 'cloudflared.pid'))
$process = Get-Process -Id $pidValue -ErrorAction Stop
$health = Invoke-RestMethod -Uri "$publicUrl/api/health" -TimeoutSec 25
$page = Invoke-WebRequest -Uri "$publicUrl/" -TimeoutSec 25
$app = Invoke-WebRequest -Uri "$publicUrl/app.js" -TimeoutSec 25
$checks = [ordered]@{
    https_quick_tunnel_url = ($publicUrl -match '^https://[a-z0-9-]+\.trycloudflare\.com$')
    cloudflared_process_alive = ($process.ProcessName -eq 'cloudflared')
    public_page_http_200 = ($page.StatusCode -eq 200)
    public_app_js_http_200 = ($app.StatusCode -eq 200)
    camera_ui_present = ($page.Content -match 'camera|摄像|视频流')
    browser_camera_api_present = ($app.Content -match 'getUserMedia')
    sse_client_present = ($app.Content -match 'EventSource')
    build_id_exact = ($health.build_id -eq '0x4D395832')
    kernel_exact = ($health.kernel -eq 'mage_m120_m89x2_0')
    latest_only_mode = ($health.mode -eq 'continuous-latest-only')
    unbounded_source_contract = ($health.source_is_unbounded -eq $true)
}
$pass = -not ($checks.Values -contains $false)
$payload = [ordered]@{
    date = '2026-09-01'
    gate = 'M216-M212-public-HTTPS-control-plane'
    status = $(if($pass){'PASS'}else{'FAIL'})
    classification = 'Public HTTPS page/API/static-client reachability for the real KV260 M212 service; no camera permission, camera frame, continuous inference, FPGA-backed complete window or latency acceptance is claimed.'
    public_url = $publicUrl
    cloudflared_pid = $pidValue
    checks = $checks
    health = $health
    page_bytes = $page.RawContentLength
    app_js_bytes = $app.RawContentLength
    web_control_plane_deployed = $pass
    browser_camera_permission_verified = $false
    continuous_stream_inference_executed = $false
    stable_rollback_preserved = $true
    next_gate = 'Open the public URL in a camera-capable browser, allow camera access, start the stream and preserve the first complete FPGA-backed window event.'
}
$result = Join-Path $workspace $ResultPath
$partial = "$result.partial"
$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $partial -Encoding utf8
Move-Item -LiteralPath $partial -Destination $result -Force
if(-not $pass){throw "M216 public HTTPS gate failed; evidence preserved at $result"}
Write-Output 'M216_M212_PUBLIC_HTTPS_PASS'
Write-Output "PUBLIC_URL=$publicUrl"
Write-Output "RESULT=$result"
