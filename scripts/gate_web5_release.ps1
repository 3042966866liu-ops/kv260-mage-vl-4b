param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$StableBoardRoot = "/home/ubuntu/tellme_qwen25_3b/packetdf_candidate",
    [string]$BoardWebRoot = "/home/ubuntu/tellme_qwen25_3b_web",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [int]$SequentialSamples = 10,
    [int]$MaxNewTokens = 1,
    [int]$RequestTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$webRoot = Join-Path $workspace "deployment\qwen25_3b_web"
$stableHostRoot = Join-Path $workspace "deployment\qwen25_3b_packetdf"
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-5\$Timestamp"
$baseUrl = "http://${BoardIp}:8000"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
$python = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$node = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$expectedBuild = "0x51317342"

New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$failed = [System.Collections.Generic.List[string]]::new()
$blocked = [System.Collections.Generic.List[string]]::new()

function Write-JsonFile([object]$Value, [string]$Path) {
    $Value | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Add-Failure([string]$Message) {
    if (-not $failed.Contains($Message)) { $failed.Add($Message) }
}

function Read-Health {
    $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/api/health"
    if ([int]$response.StatusCode -ne 200) { throw "health returned HTTP $($response.StatusCode)" }
    return ($response.Content | ConvertFrom-Json)
}

function Invoke-RawRequest(
    [string]$Body,
    [string]$ContentType = "application/json; charset=utf-8",
    [int]$TimeoutSeconds = 30
) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck `
        -TimeoutSec $TimeoutSeconds -Method Post -Uri "$baseUrl/api/chat" `
        -ContentType $ContentType -Body ([Text.Encoding]::UTF8.GetBytes($Body))
    $watch.Stop()
    $parsed = $null
    try { $parsed = $response.Content | ConvertFrom-Json } catch {}
    return [pscustomobject]@{
        status = [int]$response.StatusCode
        content = [string]$response.Content
        json = $parsed
        host_wall_ms = $watch.Elapsed.TotalMilliseconds
    }
}

function Test-Proof([object]$Response, [string]$Label, [string]$RuntimeInstance) {
    if ($null -eq $Response) { Add-Failure "$Label returned no JSON body"; return $false }
    if ($null -eq $Response.PSObject.Properties['proof'] -or $null -eq $Response.proof) {
        Add-Failure "$Label returned no FPGA proof"
        return $false
    }
    $proof = $Response.proof
    $ok = $true
    if ($null -eq $proof -or $proof.result -ne "PASS") { Add-Failure "$Label proof result is not PASS"; $ok = $false }
    if ($null -eq $proof -or $proof.build_id -ne $expectedBuild -or $proof.prefill_build_id -ne $expectedBuild) { Add-Failure "$Label Build ID mismatch"; $ok = $false }
    if ($null -eq $proof -or [int64]$proof.pl_kernel_calls -le 0 -or [int64]$proof.pl_macros -le 0) { Add-Failure "$Label lacks positive FPGA counters"; $ok = $false }
    if ($null -eq $proof -or [int]$proof.generated_tokens -le 0 -or [int]$proof.prompt_tokens -le 0) { Add-Failure "$Label lacks positive token counters"; $ok = $false }
    if ($null -eq $proof -or [bool]$proof.cpu_linear_fallback) { Add-Failure "$Label used CPU Linear fallback"; $ok = $false }
    if ($null -eq $proof -or [double]$proof.ttft_ms -le 0 -or [double]$proof.request_wall_ms -lt [double]$proof.ttft_ms) { Add-Failure "$Label timing proof is invalid"; $ok = $false }
    if ($Response.runtime_instance_id -ne $RuntimeInstance -or [int]$Response.model_load_count -ne 1) { Add-Failure "$Label violated runtime singleton"; $ok = $false }
    if ([string]::IsNullOrEmpty([string]$Response.answer)) { Add-Failure "$Label returned an empty answer"; $ok = $false }
    return $ok
}

function Read-HashMap([string[]]$Lines) {
    $map = @{}
    foreach ($line in $Lines) {
        if ($line -match '^([0-9a-fA-F]{64})\s+(.+)$') {
            $map[$Matches[2]] = $Matches[1].ToLowerInvariant()
        }
    }
    return $map
}

function Get-BoardHashes([string]$Root, [string[]]$RelativeFiles) {
    $quoted = ($RelativeFiles | ForEach-Object { "'$Root/$_'" }) -join " "
    $lines = & ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 `
        -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" "sha256sum $quoted" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "board SHA-256 failed: $($lines -join '; ')" }
    return @($lines | ForEach-Object {
        if ($_ -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') { throw "unexpected board SHA-256 output: $_" }
        $relative = $Matches[2].Substring($Root.Length + 1)
        "$($Matches[1].ToLowerInvariant())  $relative"
    })
}

function Compare-HashManifests([string[]]$Expected, [string[]]$Observed, [string]$Label) {
    $expectedMap = Read-HashMap $Expected
    $observedMap = Read-HashMap $Observed
    $differences = [System.Collections.Generic.List[object]]::new()
    foreach ($name in $expectedMap.Keys | Sort-Object) {
        $actual = $observedMap[$name]
        if ($actual -ne $expectedMap[$name]) {
            $differences.Add([pscustomobject]@{ file=$name; expected=$expectedMap[$name]; observed=$actual })
        }
    }
    foreach ($name in $observedMap.Keys | Sort-Object) {
        if (-not $expectedMap.ContainsKey($name)) {
            $differences.Add([pscustomobject]@{ file=$name; expected=$null; observed=$observedMap[$name] })
        }
    }
    if ($differences.Count -gt 0) { Add-Failure "$Label SHA-256 manifest changed" }
    return @($differences)
}

$boardStableFiles = @(
    "BOARD_GATE_RESULT.json", "run_chat_3b.sh", "overlay/qwen25_shared_l40.xsa",
    "runtime/chat.py", "runtime/qwen_fpga_runtime.py", "runtime/prefill_packet.py",
    "runtime/prefill_native.cpython-310-aarch64-linux-gnu.so", "model/config.json",
    "model/tokenizer.json", "model/tokenizer_config.json", "model/qwen25_3b_mixed_gs_index.json",
    "model/qwen25_3b_linears_w4g64.mgs", "model/qwen25_3b_aux_fp16.bin",
    "lm_head/qwen25_3b_lm_head_w4g64.json", "lm_head/qwen25_3b_lm_head_w4g64.mgs"
)
$hostStableFiles = @(
    "BOARD_GATE_RESULT.json", "run_chat_3b.sh", "overlay/qwen25_shared_l40.xsa",
    "runtime/chat.py", "runtime/qwen_fpga_runtime.py", "runtime/prefill_packet.py",
    "runtime/prefill_native.cpython-310-aarch64-linux-gnu.so"
)
$webSourceFiles = @(
    "README.md", "runtime_adapter.py", "server.py", "start_web.sh", "stop_web.sh",
    "web_config.json", "static/app.js", "static/index.html", "static/style.css",
    "tests/fixed_prompts.json", "tests/test_api_contract.py", "tests/test_static_contract.py"
)

$exactCommands = @(
    "$python -m unittest discover -s deployment/qwen25_3b_web/tests -v",
    "$node --check deployment/qwen25_3b_web/static/app.js",
    "10 x POST $baseUrl/api/chat: Web-0 prompt, argmax, max_new_tokens=$MaxNewTokens",
    "Concurrent request A + request B expecting HTTP 409 BUSY",
    "Invalid JSON/input suite against POST $baseUrl/api/chat",
    "SHA-256 re-check: stable host root + 15-file stable board manifest + Web candidate host/board",
    "GET $baseUrl/, /static/app.js, /static/style.css, /api/health"
)
Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Value $exactCommands -Encoding utf8

$healthBefore = $null
$healthAfter = $null
$sequential = @()
$concurrency = $null
$invalidResults = @()
$stableDiff = $null
$webSourceDiff = $null

try {
    # Prior milestones are release prerequisites.
    $web0 = Get-ChildItem -LiteralPath (Join-Path $workspace "artifacts\WEB-3B\Web-0") -Directory |
        Sort-Object Name -Descending | Where-Object { Test-Path (Join-Path $_.FullName "baseline_manifest.json") } | Select-Object -First 1
    $web3 = Get-ChildItem -LiteralPath (Join-Path $workspace "artifacts\WEB-3B\Web-3") -Directory |
        Sort-Object Name -Descending | Where-Object { Test-Path (Join-Path $_.FullName "web3_gate.json") } | Select-Object -First 1
    $web4 = Get-ChildItem -LiteralPath (Join-Path $workspace "artifacts\WEB-3B\Web-4") -Directory |
        Sort-Object Name -Descending | Where-Object { Test-Path (Join-Path $_.FullName "performance_summary.json") } | Select-Object -First 1
    if ($null -eq $web0 -or $null -eq $web3 -or $null -eq $web4) { throw "required prior Web evidence is missing" }
    $web0Manifest = Get-Content -Raw -LiteralPath (Join-Path $web0.FullName "baseline_manifest.json") | ConvertFrom-Json
    $web3Gate = Get-Content -Raw -LiteralPath (Join-Path $web3.FullName "web3_gate.json") | ConvertFrom-Json
    $web4Summary = Get-Content -Raw -LiteralPath (Join-Path $web4.FullName "performance_summary.json") | ConvertFrom-Json
    if ($web0Manifest.result -ne "PASS") { Add-Failure "Web-0 prerequisite is not PASS" }
    if ($web3Gate.result -ne "PASS" -or $web3Gate.manual_acceptance -ne "PASS") { Add-Failure "Web-3 UI/manual prerequisite is not PASS" }
    if ($web4Summary.result -ne "PASS") { Add-Failure "Web-4 performance prerequisite is not PASS" }
    Copy-Item -LiteralPath (Join-Path $web4.FullName "performance_summary.json") -Destination (Join-Path $evidenceRoot "performance_snapshot.json")
    Copy-Item -LiteralPath (Join-Path $web3.FullName "manual_acceptance.md") -Destination (Join-Path $evidenceRoot "manual_acceptance.md")

    # Host contracts and served UI contract.
    Push-Location $workspace
    try {
        $tests = & $python -m unittest discover -s deployment/qwen25_3b_web/tests -v 2>&1
        Set-Content -LiteralPath (Join-Path $evidenceRoot "host_tests.log") -Value $tests -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Add-Failure "host API/UI contract tests failed" }
        $syntax = & $node --check deployment/qwen25_3b_web/static/app.js 2>&1
        Set-Content -LiteralPath (Join-Path $evidenceRoot "javascript_syntax.log") -Value $syntax -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Add-Failure "app.js syntax check failed" }
    } finally { Pop-Location }

    $served = @{}
    foreach ($item in @(
        @{ key="index"; uri="$baseUrl/"; file="served_index.html" },
        @{ key="app"; uri="$baseUrl/static/app.js"; file="served_app.js" },
        @{ key="style"; uri="$baseUrl/static/style.css"; file="served_style.css" }
    )) {
        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri $item.uri
        if ([int]$response.StatusCode -ne 200) { Add-Failure "GET $($item.uri) did not return HTTP 200" }
        Set-Content -LiteralPath (Join-Path $evidenceRoot $item.file) -Value $response.Content -Encoding utf8
        $served[$item.key] = [string]$response.Content
    }
    $requiredIds = @(
        "system-status","model-name","device-name","chat-history","prompt-input","max-new-tokens",
        "send-button","inference-status","elapsed-time","proof-result","proof-build-id",
        "proof-prefill-build-id","proof-ttft","proof-request-wall","proof-pl-calls","proof-pl-macros",
        "proof-cpu-fallback","proof-tokens","runtime-instance-id","model-load-count","request-count","error-box"
    )
    foreach ($id in $requiredIds) {
        if ($served.index -notmatch "id=[`"']$([regex]::Escape($id))[`"']") { Add-Failure "served HTML missing #$id" }
    }
    foreach ($needle in @('/api/health','/api/chat','response.status===409','renderProof(payload.proof)','Number.parseInt(els.maxTokens.value,10)','max_new_tokens:maxNewTokens')) {
        if (-not $served.app.Contains($needle)) { Add-Failure "served app.js missing contract: $needle" }
    }
    $uiContract = [ordered]@{
        result = if ($failed.Count -eq 0) { "PASS" } else { "FAIL" }
        required_dom_ids = $requiredIds
        output_lengths = @(8,16,32,64,96)
        default_output_tokens = 16
        prior_manual_acceptance = $web3Gate.manual_acceptance
        page_http_200 = $true
        app_http_200 = $true
        style_http_200 = $true
    }
    Write-JsonFile $uiContract (Join-Path $evidenceRoot "ui_contract.json")

    # Stable and Web candidate hashes: host, board, and cross-copy identity.
    $expectedHostStable = Get-Content -LiteralPath (Join-Path $web0.FullName "stable_hashes.sha256")
    $expectedBoardStable = Get-Content -LiteralPath (Join-Path $web0.FullName "board_stable_hashes.sha256")
    Copy-Item -LiteralPath (Join-Path $web0.FullName "stable_hashes.sha256") -Destination (Join-Path $evidenceRoot "stable_host_expected.sha256")
    Copy-Item -LiteralPath (Join-Path $web0.FullName "board_stable_hashes.sha256") -Destination (Join-Path $evidenceRoot "stable_board_expected.sha256")
    $observedHostStable = foreach ($relative in $hostStableFiles) {
        $path = Join-Path $stableHostRoot ($relative -replace '/', '\')
        "$((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant())  $relative"
    }
    $observedBoardStable = Get-BoardHashes $StableBoardRoot $boardStableFiles
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_host_observed.sha256") -Value $observedHostStable -Encoding ascii
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_board_observed.sha256") -Value $observedBoardStable -Encoding ascii
    $hostDiff = @(Compare-HashManifests $expectedHostStable $observedHostStable "stable host candidate")
    $boardDiff = @(Compare-HashManifests $expectedBoardStable $observedBoardStable "stable board candidate")
    $stableDiff = [ordered]@{
        result = if ($hostDiff.Count -eq 0 -and $boardDiff.Count -eq 0) { "PASS" } else { "FAIL" }
        stable_candidate_unchanged = ($hostDiff.Count -eq 0 -and $boardDiff.Count -eq 0)
        host_checked_files = $hostStableFiles.Count
        board_checked_files = $boardStableFiles.Count
        host_differences = @($hostDiff)
        board_differences = @($boardDiff)
    }
    Write-JsonFile $stableDiff (Join-Path $evidenceRoot "stable_diff.json")

    $localWebHashes = foreach ($relative in $webSourceFiles) {
        $path = Join-Path $webRoot ($relative -replace '/', '\')
        "$((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant())  $relative"
    }
    $boardWebHashes = Get-BoardHashes $BoardWebRoot $webSourceFiles
    Set-Content -LiteralPath (Join-Path $evidenceRoot "source_hashes.sha256") -Value $localWebHashes -Encoding ascii
    Set-Content -LiteralPath (Join-Path $evidenceRoot "board_web_hashes.sha256") -Value $boardWebHashes -Encoding ascii
    $webDiff = @(Compare-HashManifests $localWebHashes $boardWebHashes "Web host/board candidate")
    $webSourceDiff = [ordered]@{ result=if ($webDiff.Count -eq 0) { "PASS" } else { "FAIL" }; checked_files=$webSourceFiles.Count; differences=@($webDiff) }
    Write-JsonFile $webSourceDiff (Join-Path $evidenceRoot "web_source_diff.json")

    # Service prerequisites and singleton snapshot.
    $healthBefore = Read-Health
    Write-JsonFile $healthBefore (Join-Path $evidenceRoot "health_before.json")
    if ($healthBefore.status -ne "ready" -or -not [bool]$healthBefore.warmed_up -or [int]$healthBefore.warmup_count -ne 1) { Add-Failure "service is not ready after exactly one warm-up" }
    if ([int]$healthBefore.model_load_count -ne 1) { Add-Failure "model_load_count is not 1 before release requests" }
    if ($healthBefore.build_id -ne $expectedBuild -or $healthBefore.prefill_build_id -ne $expectedBuild) { Add-Failure "health Build ID mismatch" }
    if ([bool]$healthBefore.cpu_linear_fallback) { Add-Failure "health reports CPU Linear fallback" }
    if ($healthBefore.fpga_manager_state -ne "operating") { Add-Failure "FPGA manager is not operating" }
    # Web-4 already proved the code version's warm performance.  Web-5 may
    # deliberately start a fresh singleton so the 32-bit PL proof counters do
    # not wrap during the 10-request release endurance run.

    $reference = Get-Content -Raw -LiteralPath (Join-Path $web0.FullName "cli_fixed_prompt.json") | ConvertFrom-Json
    $payload = [ordered]@{ prompt=[string]$reference.prompt; max_new_tokens=$MaxNewTokens; sampling="argmax" }
    $payloadJson = $payload | ConvertTo-Json -Compress

    # Ten sequential hot requests.
    for ($index = 1; $index -le $SequentialSamples; $index++) {
        $response = Invoke-RawRequest $payloadJson "application/json; charset=utf-8" $RequestTimeoutSeconds
        $body = $response.json
        $label = "sequential request $index"
        if ($response.status -ne 200) { Add-Failure "$label returned HTTP $($response.status)" }
        $proofPass = Test-Proof $body $label $healthBefore.runtime_instance_id
        $hasAnswer = $null -ne $body -and $null -ne $body.PSObject.Properties['answer']
        $hasRuntimeId = $null -ne $body -and $null -ne $body.PSObject.Properties['runtime_instance_id']
        $prefixPass = $false
        if ($hasAnswer) { $prefixPass = ([string]$reference.answer).StartsWith([string]$body.answer, [StringComparison]::Ordinal) }
        if (-not $prefixPass) { Add-Failure "$label output is not a CLI reference prefix" }
        $hasProof = $null -ne $body -and $null -ne $body.PSObject.Properties['proof'] -and $null -ne $body.proof
        $sequential += [pscustomobject]@{
            index=$index; http_status=$response.status; answer=if ($hasAnswer) { $body.answer } else { $null };
            proof_pass=$proofPass; cli_prefix=$prefixPass; host_wall_ms=$response.host_wall_ms;
            ttft_ms=if ($hasProof) { $body.proof.ttft_ms } else { $null };
            request_wall_ms=if ($hasProof) { $body.proof.request_wall_ms } else { $null };
            pl_kernel_calls=if ($hasProof) { $body.proof.pl_kernel_calls } else { $null };
            pl_macros=if ($hasProof) { $body.proof.pl_macros } else { $null };
            generated_tokens=if ($hasProof) { $body.proof.generated_tokens } else { $null };
            cpu_linear_fallback=if ($hasProof) { $body.proof.cpu_linear_fallback } else { $null };
            runtime_instance_id=if ($hasRuntimeId) { $body.runtime_instance_id } else { $null }
        }
        # Preserve partial success/failure rows even if a later request aborts
        # the release run.
        Write-JsonFile $sequential (Join-Path $evidenceRoot "sequential_requests.json")
        $rowResult = if ($response.status -eq 200 -and $proofPass -and $prefixPass) { "PASS" } else { "FAIL" }
        Write-Output "WEB5_SEQUENTIAL_${index}_OF_${SequentialSamples}_$rowResult"
    }
    Write-JsonFile $sequential (Join-Path $evidenceRoot "sequential_requests.json")
    if (@($sequential | Select-Object -ExpandProperty answer -Unique).Count -ne 1) { Add-Failure "sequential outputs are not deterministic" }

    # Concurrency guard: request A holds the FPGA lock while request B must receive 409 BUSY.
    $requestCountBeforeConcurrency = [int](Read-Health).request_count
    $job = Start-Job -ScriptBlock {
        param($Uri, $Body, $Timeout)
        $watch = [Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -TimeoutSec $Timeout `
            -Method Post -Uri $Uri -ContentType "application/json; charset=utf-8" `
            -Body ([Text.Encoding]::UTF8.GetBytes($Body))
        $watch.Stop()
        [pscustomobject]@{ status=[int]$response.StatusCode; content=[string]$response.Content; host_wall_ms=$watch.Elapsed.TotalMilliseconds }
    } -ArgumentList "$baseUrl/api/chat", $payloadJson, $RequestTimeoutSeconds
    $busyObserved = $false
    $busyDeadline = [DateTime]::UtcNow.AddSeconds(15)
    while ([DateTime]::UtcNow -lt $busyDeadline) {
        Start-Sleep -Milliseconds 100
        $probe = Read-Health
        if ($probe.status -eq "busy" -or [bool]$probe.busy) { $busyObserved = $true; break }
        if ($job.State -in @("Completed","Failed","Stopped")) { break }
    }
    $busyResponse = Invoke-RawRequest $payloadJson "application/json; charset=utf-8" 15
    $null = Wait-Job -Job $job -Timeout $RequestTimeoutSeconds
    if ($job.State -ne "Completed") { Stop-Job $job -ErrorAction SilentlyContinue; Add-Failure "concurrency request A did not complete" }
    $jobResult = Receive-Job $job -ErrorAction SilentlyContinue | Select-Object -Last 1
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    $requestAJson = $null
    if ($null -ne $jobResult) { try { $requestAJson = $jobResult.content | ConvertFrom-Json } catch {} }
    $requestAProof = Test-Proof $requestAJson "concurrency request A" $healthBefore.runtime_instance_id
    $busyPass = $busyResponse.status -eq 409 -and $null -ne $busyResponse.json -and $busyResponse.json.status -eq "busy" -and $busyResponse.json.code -eq "BUSY"
    if (-not $busyObserved) { Add-Failure "health never exposed busy during concurrency test" }
    if (-not $busyPass) { Add-Failure "concurrency request B did not return HTTP 409 BUSY" }
    $healthAfterConcurrency = Read-Health
    if ([int]$healthAfterConcurrency.request_count -ne $requestCountBeforeConcurrency + 1) { Add-Failure "concurrency test did not execute exactly one inference" }
    $concurrency = [ordered]@{
        result=if ($busyObserved -and $busyPass -and $requestAProof) { "PASS" } else { "FAIL" }
        busy_observed=$busyObserved
        request_a_http_status=if ($null -ne $jobResult) { [int]$jobResult.status } else { $null }
        request_a_fpga_proof_pass=$requestAProof
        request_b_http_status=$busyResponse.status
        request_b_status=if ($null -ne $busyResponse.json) { $busyResponse.json.status } else { $null }
        request_b_code=if ($null -ne $busyResponse.json) { $busyResponse.json.code } else { $null }
        request_count_before=$requestCountBeforeConcurrency
        request_count_after=[int]$healthAfterConcurrency.request_count
        runtime_instance_id=$healthAfterConcurrency.runtime_instance_id
    }
    Write-JsonFile $concurrency (Join-Path $evidenceRoot "concurrency.json")

    # Invalid requests must fail before inference and leave the service alive.
    $invalidCountBefore = [int](Read-Health).request_count
    $longPrompt = "x" * 4097
    $invalidCases = @(
        @{ name="empty_prompt"; body='{"prompt":"","max_new_tokens":1,"sampling":"argmax"}'; contentType="application/json"; expected=400 },
        @{ name="long_prompt"; body=(@{prompt=$longPrompt;max_new_tokens=1;sampling="argmax"}|ConvertTo-Json -Compress); contentType="application/json"; expected=400 },
        @{ name="invalid_json"; body='{"prompt":'; contentType="application/json"; expected=400 },
        @{ name="zero_tokens"; body='{"prompt":"test","max_new_tokens":0,"sampling":"argmax"}'; contentType="application/json"; expected=400 },
        @{ name="over_max_tokens"; body='{"prompt":"test","max_new_tokens":97,"sampling":"argmax"}'; contentType="application/json"; expected=400 },
        @{ name="unsupported_sampling"; body='{"prompt":"test","max_new_tokens":1,"sampling":"top_p"}'; contentType="application/json"; expected=400 },
        @{ name="json_array"; body='[]'; contentType="application/json"; expected=400 },
        @{ name="wrong_content_type"; body='{"prompt":"test","max_new_tokens":1,"sampling":"argmax"}'; contentType="text/plain"; expected=415 }
    )
    foreach ($case in $invalidCases) {
        $response = Invoke-RawRequest $case.body $case.contentType 20
        $pass = $response.status -eq [int]$case.expected -and $null -ne $response.json -and $response.json.status -eq "error"
        if (-not $pass) { Add-Failure "invalid input '$($case.name)' returned HTTP $($response.status), expected $($case.expected)" }
        $invalidResults += [pscustomobject]@{
            name=$case.name; expected_status=[int]$case.expected; observed_status=$response.status;
            error_code=if ($null -ne $response.json) { $response.json.code } else { $null }; pass=$pass
        }
    }
    $healthAfterInvalid = Read-Health
    if ([int]$healthAfterInvalid.request_count -ne $invalidCountBefore) { Add-Failure "invalid inputs advanced inference request_count" }
    if ($healthAfterInvalid.status -ne "ready") { Add-Failure "service is not ready after invalid input tests" }
    if ($healthAfterInvalid.runtime_instance_id -ne $healthBefore.runtime_instance_id -or [int]$healthAfterInvalid.model_load_count -ne 1) { Add-Failure "invalid inputs changed the runtime singleton" }
    Write-JsonFile ([ordered]@{
        result=if (@($invalidResults | Where-Object {-not $_.pass}).Count -eq 0) { "PASS" } else { "FAIL" }
        request_count_before=$invalidCountBefore; request_count_after=[int]$healthAfterInvalid.request_count;
        service_status_after=$healthAfterInvalid.status; cases=$invalidResults
    }) (Join-Path $evidenceRoot "invalid_inputs.json")

    $healthAfter = Read-Health
    Write-JsonFile $healthAfter (Join-Path $evidenceRoot "health_after.json")
    $expectedAdvance = $SequentialSamples + 1
    if ([int]$healthAfter.request_count -ne [int]$healthBefore.request_count + $expectedAdvance) { Add-Failure "final request_count advance is not $expectedAdvance" }
    if ($healthAfter.runtime_instance_id -ne $healthBefore.runtime_instance_id -or [int]$healthAfter.model_load_count -ne 1) { Add-Failure "runtime singleton changed during Web-5" }
    if ($healthAfter.status -ne "ready" -or [bool]$healthAfter.busy) { Add-Failure "service is not ready after Web-5" }

    # Preserve final board service log.
    $serverLog = & ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 `
        "$BoardUser@$BoardIp" "tail -n 260 '$BoardWebRoot/web3b_server.log'" 2>&1
    Set-Content -LiteralPath (Join-Path $evidenceRoot "server.log") -Value $serverLog -Encoding utf8
} catch {
    $message = $_.Exception.Message
    if ($message -match 'connect|unreachable|timed out|actively refused|No route') { $blocked.Add($message) } else { Add-Failure $message }
}

$result = if ($blocked.Count -gt 0) { "BLOCKED" } elseif ($failed.Count -gt 0) { "FAIL" } else { "PASS" }
$gate = [ordered]@{
    result = $result
    milestone = "Web-5"
    timestamp = $Timestamp
    model = "Qwen2.5-3B-Instruct"
    device = "AMD KV260"
    architecture = "aarch64-cortex-a53"
    web_candidate_host = "deployment/qwen25_3b_web"
    web_candidate_board = $BoardWebRoot
    stable_candidate_host = "deployment/qwen25_3b_packetdf"
    stable_candidate_board = $StableBoardRoot
    build_id = $expectedBuild
    prefill_build_id = $expectedBuild
    sequential_requests_required = $SequentialSamples
    sequential_requests_completed = @($sequential).Count
    sequential_all_fpga_proof_pass = (@($sequential).Count -eq $SequentialSamples -and @($sequential | Where-Object {-not $_.proof_pass}).Count -eq 0)
    sequential_all_deterministic = (@($sequential | Select-Object -ExpandProperty answer -Unique).Count -eq 1)
    concurrency_guard = if ($null -ne $concurrency) { $concurrency.result } else { "NOT_RUN" }
    invalid_input_gate = if (Test-Path (Join-Path $evidenceRoot "invalid_inputs.json")) { (Get-Content -Raw -LiteralPath (Join-Path $evidenceRoot "invalid_inputs.json") | ConvertFrom-Json).result } else { "NOT_RUN" }
    stable_candidate_unchanged = if ($null -ne $stableDiff) { $stableDiff.stable_candidate_unchanged } else { $false }
    web_host_board_sources_match = if ($null -ne $webSourceDiff) { $webSourceDiff.result -eq "PASS" } else { $false }
    web_ui_contract = if (Test-Path (Join-Path $evidenceRoot "ui_contract.json")) { (Get-Content -Raw -LiteralPath (Join-Path $evidenceRoot "ui_contract.json") | ConvertFrom-Json).result } else { "NOT_RUN" }
    warm_performance_gate = if (Test-Path (Join-Path $evidenceRoot "performance_snapshot.json")) { (Get-Content -Raw -LiteralPath (Join-Path $evidenceRoot "performance_snapshot.json") | ConvertFrom-Json).result } else { "NOT_RUN" }
    web4_runtime_instance_id = if (Test-Path (Join-Path $evidenceRoot "performance_snapshot.json")) { (Get-Content -Raw -LiteralPath (Join-Path $evidenceRoot "performance_snapshot.json") | ConvertFrom-Json).runtime_instance_id } else { $null }
    runtime_instance_id = if ($null -ne $healthAfter) { $healthAfter.runtime_instance_id } elseif ($null -ne $healthBefore) { $healthBefore.runtime_instance_id } else { $null }
    model_load_count = if ($null -ne $healthAfter) { [int]$healthAfter.model_load_count } elseif ($null -ne $healthBefore) { [int]$healthBefore.model_load_count } else { $null }
    warmup_count = if ($null -ne $healthAfter) { [int]$healthAfter.warmup_count } elseif ($null -ne $healthBefore) { [int]$healthBefore.warmup_count } else { $null }
    cpu_linear_fallback = if ($null -ne $healthAfter) { [bool]$healthAfter.cpu_linear_fallback } else { $null }
    failed_checks = @($failed)
    blocked_checks = @($blocked)
}
Write-JsonFile $gate (Join-Path $evidenceRoot "WEB_GATE_RESULT.json")

$summary = @"
# Web-5 Release Gate - $result

- Model / device: Qwen2.5-3B-Instruct / AMD KV260
- Build ID / Prefill Build ID: $expectedBuild / $expectedBuild
- Sequential FPGA requests: $(@($sequential).Count)/$SequentialSamples
- Concurrency guard: $($gate.concurrency_guard)
- Invalid input gate: $($gate.invalid_input_gate)
- Stable candidate unchanged: $($gate.stable_candidate_unchanged)
- Web host/board sources match: $($gate.web_host_board_sources_match)
- UI contract / prior manual acceptance: $($gate.web_ui_contract) / PASS
- Warm performance gate: $($gate.warm_performance_gate)
- Runtime singleton / model loads: $($gate.runtime_instance_id) / $($gate.model_load_count)
- CPU Linear fallback: $($gate.cpu_linear_fallback)
- Failed checks: $($failed -join '; ')
- Blocked checks: $($blocked -join '; ')

Go decision: $result. No 7B, DeepSeek-V4, vLLM, streaming, or new FPGA optimization was started.
"@
Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Value $summary -Encoding utf8

Write-Output "WEB5_$result"
Write-Output "EVIDENCE=$evidenceRoot"
if ($result -ne "PASS") { exit 1 }
