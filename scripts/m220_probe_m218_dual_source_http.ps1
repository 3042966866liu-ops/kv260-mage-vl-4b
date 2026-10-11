[CmdletBinding()]
param(
    [string]$BoardUrl = 'http://192.168.0.2:8001',
    [string]$StateRoot = 'tmp\m212_public',
    [string]$ResultPath = 'deployment\mage_vl4b\M220_M218_DUAL_SOURCE_HTTP_RESULT.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$state = Join-Path $workspace $StateRoot
$publicUrl = (Get-Content -Raw -LiteralPath (Join-Path $state 'public_url.txt')).Trim()
$tunnelPid = [int](Get-Content -Raw -LiteralPath (Join-Path $state 'cloudflared.pid'))
$tunnelProcess = Get-Process -Id $tunnelPid -ErrorAction Stop

$localHealth = Invoke-RestMethod -Uri "$BoardUrl/api/health" -TimeoutSec 20
$localPage = Invoke-WebRequest -Uri "$BoardUrl/" -TimeoutSec 20
$localApp = Invoke-WebRequest -Uri "$BoardUrl/app.js" -TimeoutSec 20
$publicHealth = Invoke-RestMethod -Uri "$publicUrl/api/health" -TimeoutSec 30
$publicPage = Invoke-WebRequest -Uri "$publicUrl/" -TimeoutSec 30
$publicApp = Invoke-WebRequest -Uri "$publicUrl/app.js" -TimeoutSec 30

$checks = [ordered]@{
    local_page_http_200 = ($localPage.StatusCode -eq 200)
    local_app_js_http_200 = ($localApp.StatusCode -eq 200)
    public_page_http_200 = ($publicPage.StatusCode -eq 200)
    public_app_js_http_200 = ($publicApp.StatusCode -eq 200)
    cloudflared_process_alive = ($tunnelProcess.ProcessName -eq 'cloudflared')
    public_https_url = ($publicUrl -match '^https://[a-z0-9-]+\.trycloudflare\.com$')
    camera_ui_retained = ($localPage.Content -match '打开摄像头')
    local_video_picker_present = (($localPage.Content -match 'id="video-file"') -and ($localPage.Content -match 'video/mp4'))
    camera_api_retained = ($localApp.Content -match 'getUserMedia')
    local_object_url_present = ($localApp.Content -match 'URL\.createObjectURL')
    local_file_loop_present = ($localApp.Content -match 'video\.loop=true')
    no_whole_video_form_upload = ($localApp.Content -notmatch 'FormData|/upload')
    sampled_rgb_frame_endpoint = ($localApp.Content -match '/api/4b/video/live/frame')
    sse_client_present = ($localApp.Content -match 'EventSource')
    local_public_page_exact = ($localPage.Content -ceq $publicPage.Content)
    local_public_app_exact = ($localApp.Content -ceq $publicApp.Content)
    build_id_exact = ($localHealth.build_id -eq '0x4D395832')
    kernel_exact = ($localHealth.kernel -eq 'mage_m120_m89x2_0')
    latest_only_mode = ($localHealth.mode -eq 'continuous-latest-only')
    source_unselected_before_user_action = ($localHealth.source_mode -eq 'unselected')
    finite_content_false_before_selection = ($localHealth.source_content_is_finite -eq $false)
    runtime_not_loaded = ($localHealth.board_runtime_loaded -eq $false)
    local_public_health_consistent = (($localHealth | ConvertTo-Json -Compress -Depth 12) -eq ($publicHealth | ConvertTo-Json -Compress -Depth 12))
}
$pass = -not ($checks.Values -contains $false)
$payload = [ordered]@{
    date = '2026-09-01'
    gate = 'M220-M218-real-KV260-dual-source-local-and-public-HTTP-control-plane'
    status = $(if ($pass) { 'PASS' } else { 'FAIL' })
    classification = 'Real-KV260 M218 camera/local-file-loop page, API and public HTTPS reachability only; no video was selected, no frame was transmitted, runtime was not loaded, and no FPGA complete window or latency is claimed.'
    board_url = $BoardUrl
    public_url = $publicUrl
    cloudflared_pid = $tunnelPid
    checks = $checks
    health = $localHealth
    page_bytes = $localPage.RawContentLength
    app_js_bytes = $localApp.RawContentLength
    video_selected = $false
    video_frames_transmitted = $false
    continuous_stream_inference_executed = $false
    stable_rollback_preserved = $true
    next_gate = 'Obtain action-time user confirmation, then select the local MP4 in the browser, start one M218 uploaded-file-loop session, and preserve the first FPGA-backed complete-window event.'
}
$result = Join-Path $workspace $ResultPath
$partial = "$result.partial"
$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $partial -Encoding utf8
Move-Item -LiteralPath $partial -Destination $result -Force
if (-not $pass) { throw "M220 dual-source HTTP gate failed; evidence preserved at $result" }
Write-Output 'M220_M218_DUAL_SOURCE_HTTP_PASS'
Write-Output "PUBLIC_URL=$publicUrl"
Write-Output "RESULT=$result"
