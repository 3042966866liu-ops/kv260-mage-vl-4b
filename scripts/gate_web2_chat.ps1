param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$StableBoardRoot = "/home/ubuntu/tellme_qwen25_3b/packetdf_candidate",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [int]$RequestTimeoutSeconds = 360
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stableHostRoot = Join-Path $workspace "deployment\qwen25_3b_packetdf"
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-2\$Timestamp"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
$baseUrl = "http://${BoardIp}:8000"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

function Write-JsonFile([object]$Value, [string]$Path) {
    $Value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $Path -Encoding utf8
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

function Read-BoardHashes([string[]]$ReferenceLines) {
    $relativePaths = @($ReferenceLines | ForEach-Object {
        if ($_ -match '^[0-9a-fA-F]{64}\s+(.+)$') { $Matches[1] }
    })
    $quoted = ($relativePaths | ForEach-Object { "'$StableBoardRoot/$_'" }) -join " "
    $output = & ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" "sha256sum $quoted" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "board stable hash command failed: $($output -join [Environment]::NewLine)"
    }
    return @($output | ForEach-Object {
        if ($_ -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') { throw "invalid board hash output: $_" }
        $relative = $Matches[2].Substring($StableBoardRoot.Length + 1)
        "$($Matches[1].ToLowerInvariant())  $relative"
    })
}

function Read-Health() {
    $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/api/health"
    if ([int]$response.StatusCode -ne 200) { throw "health HTTP $($response.StatusCode)" }
    return ($response.Content | ConvertFrom-Json)
}

$failed = [System.Collections.Generic.List[string]]::new()
$blocked = [System.Collections.Generic.List[string]]::new()
$reference = $null
$responseJson = $null
$healthBefore = $null
$healthAfter = $null
$hostWallMs = $null

try {
    $web0Runs = Get-ChildItem -LiteralPath (Join-Path $workspace "artifacts\WEB-3B\Web-0") -Directory | Sort-Object Name -Descending
    $web0Path = $null
    foreach ($run in $web0Runs) {
        $manifestPath = Join-Path $run.FullName "baseline_manifest.json"
        if (Test-Path -LiteralPath $manifestPath) {
            $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
            if ($manifest.result -eq "PASS") { $web0Path = $run.FullName; break }
        }
    }
    if ($null -eq $web0Path) { throw "no PASS Web-0 evidence was found" }
    $reference = Get-Content -Raw -LiteralPath (Join-Path $web0Path "cli_fixed_prompt.json") | ConvertFrom-Json
    Copy-Item -LiteralPath (Join-Path $web0Path "cli_fixed_prompt.json") -Destination (Join-Path $evidenceRoot "cli_reference.json")

    $hostReferenceLines = Get-Content -LiteralPath (Join-Path $web0Path "stable_hashes.sha256")
    $boardReferenceLines = Get-Content -LiteralPath (Join-Path $web0Path "board_stable_hashes.sha256")
    $hostReference = Read-HashMap $hostReferenceLines
    $boardReference = Read-HashMap $boardReferenceLines

    $hostBeforeLines = foreach ($relative in $hostReference.Keys | Sort-Object) {
        $path = Join-Path $stableHostRoot ($relative -replace '/', '\')
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
    $boardBeforeLines = Read-BoardHashes $boardReferenceLines
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_host_hashes_before.sha256") -Value $hostBeforeLines -Encoding ascii
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_board_hashes_before.sha256") -Value $boardBeforeLines -Encoding ascii

    foreach ($entry in (Read-HashMap $hostBeforeLines).GetEnumerator()) {
        if ($hostReference[$entry.Key] -ne $entry.Value) { $failed.Add("stable host changed before request: $($entry.Key)") }
    }
    foreach ($entry in (Read-HashMap $boardBeforeLines).GetEnumerator()) {
        if ($boardReference[$entry.Key] -ne $entry.Value) { $failed.Add("stable board changed before request: $($entry.Key)") }
    }

    $healthBefore = Read-Health
    if ($healthBefore.status -ne "ready") { throw "service is not ready (status=$($healthBefore.status))" }
    $payload = [ordered]@{
        prompt = [string]$reference.prompt
        max_new_tokens = [int]$reference.max_new_tokens
        sampling = "argmax"
    }
    $payloadJson = $payload | ConvertTo-Json -Compress
    Set-Content -LiteralPath (Join-Path $evidenceRoot "request.json") -Value $payloadJson -Encoding utf8
    Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Value "POST $baseUrl/api/chat`nContent-Type: application/json`n$payloadJson" -Encoding utf8

    $watch = [Diagnostics.Stopwatch]::StartNew()
    $httpResponse = Invoke-WebRequest -UseBasicParsing -TimeoutSec $RequestTimeoutSeconds -Method Post -Uri "$baseUrl/api/chat" -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($payloadJson))
    $watch.Stop()
    $hostWallMs = $watch.Elapsed.TotalMilliseconds
    if ([int]$httpResponse.StatusCode -ne 200) { throw "chat HTTP $($httpResponse.StatusCode)" }
    Set-Content -LiteralPath (Join-Path $evidenceRoot "http_response_raw.json") -Value $httpResponse.Content -Encoding utf8
    $responseJson = $httpResponse.Content | ConvertFrom-Json
    $healthAfter = Read-Health

    $proof = $responseJson.proof
    if ([string]$responseJson.answer -cne [string]$reference.answer) { $failed.Add("HTTP answer differs from deterministic CLI reference") }
    if ($proof.result -ne "PASS") { $failed.Add("proof.result is not PASS") }
    if ($proof.build_id -ne "0x51317342" -or $proof.prefill_build_id -ne "0x51317342") { $failed.Add("Build ID mismatch") }
    if ([int64]$proof.pl_kernel_calls -le 0) { $failed.Add("PL kernel calls did not advance") }
    if ([int64]$proof.pl_macros -le 0) { $failed.Add("PL macros did not advance") }
    if ($proof.cpu_linear_fallback -ne $false) { $failed.Add("CPU Linear fallback was not false") }
    if ([int]$proof.generated_tokens -le 0) { $failed.Add("no tokens were generated") }
    if ([double]$proof.ttft_ms -le 0) { $failed.Add("TTFT was not positive") }
    if ([double]$proof.request_wall_ms -lt [double]$proof.ttft_ms) { $failed.Add("runtime request wall was smaller than TTFT") }
    if ($healthAfter.runtime_instance_id -ne $healthBefore.runtime_instance_id) { $failed.Add("runtime instance changed during request") }
    if ([int]$healthAfter.model_load_count -ne 1) { $failed.Add("model_load_count is not one") }
    if ([int]$healthAfter.request_count -ne ([int]$healthBefore.request_count + 1)) { $failed.Add("request_count did not advance exactly once") }

    $hostAfterLines = foreach ($relative in $hostReference.Keys | Sort-Object) {
        $path = Join-Path $stableHostRoot ($relative -replace '/', '\')
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
    $boardAfterLines = Read-BoardHashes $boardReferenceLines
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_host_hashes_after.sha256") -Value $hostAfterLines -Encoding ascii
    Set-Content -LiteralPath (Join-Path $evidenceRoot "stable_board_hashes_after.sha256") -Value $boardAfterLines -Encoding ascii
    if (@(Compare-Object $hostBeforeLines $hostAfterLines).Count -ne 0) { $failed.Add("stable host files changed during request") }
    if (@(Compare-Object $boardBeforeLines $boardAfterLines).Count -ne 0) { $failed.Add("stable board files changed during request") }
} catch {
    $message = $_.Exception.Message
    if ($message -match 'connect|unreachable|timed out') { $blocked.Add($message) } else { $failed.Add($message) }
}

if ($null -ne $healthBefore) { Write-JsonFile $healthBefore (Join-Path $evidenceRoot "health_before.json") }
if ($null -ne $healthAfter) { Write-JsonFile $healthAfter (Join-Path $evidenceRoot "health_after.json") }
if ($null -ne $responseJson) { Write-JsonFile $responseJson (Join-Path $evidenceRoot "http_fixed_prompt.json") }

$result = if ($blocked.Count -gt 0) { "BLOCKED" } elseif ($failed.Count -gt 0) { "FAIL" } else { "PASS" }
$gate = [ordered]@{
    result = $result
    milestone = "Web-2"
    timestamp = $Timestamp
    deterministic_answer_match = ($null -ne $responseJson -and $null -ne $reference -and [string]$responseJson.answer -ceq [string]$reference.answer)
    comparison_basis = "answer text (stable runtime does not expose generated token IDs)"
    build_id = if ($null -ne $responseJson) { $responseJson.proof.build_id } else { $null }
    prefill_build_id = if ($null -ne $responseJson) { $responseJson.proof.prefill_build_id } else { $null }
    cpu_linear_fallback = if ($null -ne $responseJson) { $responseJson.proof.cpu_linear_fallback } else { $null }
    pl_kernel_calls = if ($null -ne $responseJson) { $responseJson.proof.pl_kernel_calls } else { $null }
    pl_macros = if ($null -ne $responseJson) { $responseJson.proof.pl_macros } else { $null }
    prompt_tokens = if ($null -ne $responseJson) { $responseJson.proof.prompt_tokens } else { $null }
    generated_tokens = if ($null -ne $responseJson) { $responseJson.proof.generated_tokens } else { $null }
    ttft_ms = if ($null -ne $responseJson) { $responseJson.proof.ttft_ms } else { $null }
    runtime_request_wall_ms = if ($null -ne $responseJson) { $responseJson.proof.request_wall_ms } else { $null }
    host_request_wall_ms = $hostWallMs
    runtime_instance_id = if ($null -ne $healthAfter) { $healthAfter.runtime_instance_id } else { $null }
    model_load_count = if ($null -ne $healthAfter) { $healthAfter.model_load_count } else { $null }
    stable_candidate_unchanged = (@($failed | Where-Object { $_ -match 'stable .* changed' }).Count -eq 0)
    failed_checks = @($failed)
    blocked_checks = @($blocked)
}
Write-JsonFile $gate (Join-Path $evidenceRoot "web2_gate.json")

$summary = @"
# Web-2 HTTP Chat FPGA Closure - $result

- Deterministic CLI/HTTP answer match: $($gate.deterministic_answer_match)
- Build / Prefill Build: $($gate.build_id) / $($gate.prefill_build_id)
- PL calls / macros: $($gate.pl_kernel_calls) / $($gate.pl_macros)
- CPU Linear fallback: $($gate.cpu_linear_fallback)
- Prompt / generated tokens: $($gate.prompt_tokens) / $($gate.generated_tokens)
- TTFT / runtime wall / host wall: $($gate.ttft_ms) / $($gate.runtime_request_wall_ms) / $($gate.host_request_wall_ms) ms
- Runtime singleton: $($gate.runtime_instance_id), load count $($gate.model_load_count)
- Stable candidate unchanged: $($gate.stable_candidate_unchanged)
- Failed checks: $($failed -join '; ')
- Blocked checks: $($blocked -join '; ')
"@
Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Value $summary -Encoding utf8

Write-Output "WEB2_$result"
Write-Output "EVIDENCE=$evidenceRoot"
if ($result -ne "PASS") { exit 1 }
