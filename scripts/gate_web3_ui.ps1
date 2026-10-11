param(
    [string]$BoardIp = "192.168.77.2",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$ManualAccepted
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$webRoot = Join-Path $workspace "deployment\qwen25_3b_web"
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-3\$Timestamp"
$baseUrl = "http://${BoardIp}:8000"
$python = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$node = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$failed = [System.Collections.Generic.List[string]]::new()
$blocked = [System.Collections.Generic.List[string]]::new()
$health = $null
$exact = @(
    "$python -m unittest discover -s deployment/qwen25_3b_web/tests -v",
    "$node --check deployment/qwen25_3b_web/static/app.js",
    "GET $baseUrl/",
    "GET $baseUrl/static/app.js",
    "GET $baseUrl/static/style.css",
    "GET $baseUrl/api/health"
)
Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Value $exact -Encoding utf8

try {
    Push-Location $workspace
    try {
        $tests = & $python -m unittest discover -s deployment/qwen25_3b_web/tests -v 2>&1
        Set-Content -LiteralPath (Join-Path $evidenceRoot "host_tests.log") -Value $tests -Encoding utf8
        if ($LASTEXITCODE -ne 0) { $failed.Add("host UI/API contract tests failed") }
        $syntax = & $node --check deployment/qwen25_3b_web/static/app.js 2>&1
        Set-Content -LiteralPath (Join-Path $evidenceRoot "javascript_syntax.log") -Value $syntax -Encoding utf8
        if ($LASTEXITCODE -ne 0) { $failed.Add("app.js syntax check failed") }
    } finally { Pop-Location }

    $responses = @{}
    foreach ($item in @(
        @{ Name = "index"; Uri = "$baseUrl/"; File = "served_index.html" },
        @{ Name = "app"; Uri = "$baseUrl/static/app.js"; File = "served_app.js" },
        @{ Name = "style"; Uri = "$baseUrl/static/style.css"; File = "served_style.css" }
    )) {
        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri $item.Uri
        if ([int]$response.StatusCode -ne 200) { $failed.Add("GET $($item.Uri) did not return HTTP 200") }
        Set-Content -LiteralPath (Join-Path $evidenceRoot $item.File) -Value $response.Content -Encoding utf8
        $responses[$item.Name] = [string]$response.Content
    }
    $healthResponse = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/api/health"
    $health = $healthResponse.Content | ConvertFrom-Json
    $health | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $evidenceRoot "health.json") -Encoding utf8
    if ($health.status -ne "ready" -or [int]$health.model_load_count -ne 1) { $failed.Add("service was not ready with one model load") }

    $requiredIds = @("system-status","model-name","device-name","chat-history","prompt-input","send-button","inference-status","elapsed-time","proof-build-id","proof-prefill-build-id","proof-ttft","proof-pl-calls","proof-pl-macros","proof-cpu-fallback","proof-tokens","error-box")
    foreach ($id in $requiredIds) { if ($responses.index -notmatch "id=[`"']$([regex]::Escape($id))[`"']") { $failed.Add("served HTML missing #$id") } }
    foreach ($needle in @('/api/health','/api/chat','/api/chat/stream','response.status===409','els.send.disabled=true','renderProof(completed.proof)','paragraph.textContent=text','readSse')) {
        if (-not $responses.app.Contains($needle)) { $failed.Add("served app.js missing contract: $needle") }
    }
    if (-not $ManualAccepted) { $blocked.Add("manual browser visual/interaction acceptance is pending") }
} catch {
    if ($_.Exception.Message -match 'connect|unreachable|timed out') { $blocked.Add($_.Exception.Message) } else { $failed.Add($_.Exception.Message) }
}

$hashRows = foreach ($file in Get-ChildItem -LiteralPath $webRoot -Recurse -File | Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' }) {
    $relative = $file.FullName.Substring($webRoot.Length + 1).Replace('\','/')
    "$((Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant())  $relative"
}
Set-Content -LiteralPath (Join-Path $evidenceRoot "source_hashes.sha256") -Value $hashRows -Encoding ascii

$manual = if ($ManualAccepted) {
@"
# Web-3 Manual Acceptance - PASS

User confirmed the visible browser test after opening `$baseUrl`:

- READY state visible
- prompt can be submitted
- inference progress and elapsed timer visible
- answer rendered
- FPGA PASS evidence panel rendered
"@
} else {
@"
# Web-3 Manual Acceptance - PENDING

Open `$baseUrl`, confirm READY, submit the prefilled prompt, and verify the
progress timer, returned answer, FPGA PASS, Build IDs, PL calls/macros, token
counts, TTFT/request wall and CPU fallback=false.
"@
}
Set-Content -LiteralPath (Join-Path $evidenceRoot "manual_acceptance.md") -Value $manual -Encoding utf8

$result = if ($failed.Count -gt 0) { "FAIL" } elseif ($blocked.Count -gt 0) { "BLOCKED" } else { "PASS" }
$gate = [ordered]@{
    result = $result; milestone = "Web-3"; timestamp = $Timestamp; url = $baseUrl
    automated_contract = if ($failed.Count -eq 0) { "PASS" } else { "FAIL" }
    manual_acceptance = if ($ManualAccepted) { "PASS" } else { "PENDING" }
    service_status = if ($null -ne $health) { $health.status } else { $null }
    runtime_instance_id = if ($null -ne $health) { $health.runtime_instance_id } else { $null }
    model_load_count = if ($null -ne $health) { $health.model_load_count } else { $null }
    failed_checks = @($failed); blocked_checks = @($blocked)
}
$gate | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $evidenceRoot "web3_gate.json") -Encoding utf8
Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Encoding utf8 -Value "# Web-3 UI - $result`n`n- Automated contract: $($gate.automated_contract)`n- Manual acceptance: $($gate.manual_acceptance)`n- URL: $baseUrl`n- Failed: $($failed -join '; ')`n- Blocked: $($blocked -join '; ')`n"
Write-Output "WEB3_$result"
Write-Output "EVIDENCE=$evidenceRoot"
if ($result -ne "PASS") { exit 1 }
