param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$StableBoardRoot = "/home/ubuntu/tellme_qwen25_3b/packetdf_candidate",
    [string]$Port = "COM3",
    [string]$ExpectedFtdiSerial = "XFL1PL5N11BJB",
    [string]$FixedPromptBase64 = "6K+355So5LiJ5Y+l6K+d6Kej6YeKVHJhbnNmb3JtZXLkuK3oh6rms6jmhI/lipvmnLrliLbnmoTkvZznlKjjgII=",
    [int]$MaxNewTokens = 96,
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-0\$Timestamp"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$fixedPrompt = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String($FixedPromptBase64)
)

$boardStableFiles = @(
    "BOARD_GATE_RESULT.json",
    "run_chat_3b.sh",
    "overlay/qwen25_shared_l40.xsa",
    "runtime/chat.py",
    "runtime/qwen_fpga_runtime.py",
    "runtime/prefill_packet.py",
    "runtime/prefill_native.cpython-310-aarch64-linux-gnu.so",
    "model/config.json",
    "model/tokenizer.json",
    "model/tokenizer_config.json",
    "model/qwen25_3b_mixed_gs_index.json",
    "model/qwen25_3b_linears_w4g64.mgs",
    "model/qwen25_3b_aux_fp16.bin",
    "lm_head/qwen25_3b_lm_head_w4g64.json",
    "lm_head/qwen25_3b_lm_head_w4g64.mgs"
)

# The checked-in stable deployment intentionally omits the multi-gigabyte
# packed model payload.  Hash every immutable board payload in place, and
# separately hash/compare the checked-in files that exist on both host and
# board.  Web-5 repeats both manifests.
$hostStableFiles = @(
    "BOARD_GATE_RESULT.json",
    "run_chat_3b.sh",
    "overlay/qwen25_shared_l40.xsa",
    "runtime/chat.py",
    "runtime/qwen_fpga_runtime.py",
    "runtime/prefill_packet.py",
    "runtime/prefill_native.cpython-310-aarch64-linux-gnu.so"
)

$stableHostRoot = Join-Path $workspace "deployment\qwen25_3b_packetdf"
$boardGatePath = Join-Path $stableHostRoot "BOARD_GATE_RESULT.json"
$promotionGatePath = Join-Path $workspace "deployment\qwen25_3b_packetcopy\BOARD_GATE_RESULT.json"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path

function Write-HostHashes([string]$Path) {
    $rows = foreach ($relative in $hostStableFiles) {
        $local = Join-Path $stableHostRoot ($relative -replace "/", "\")
        if (-not (Test-Path -LiteralPath $local -PathType Leaf)) {
            throw "Missing stable host file: $relative"
        }
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $local).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
    Set-Content -LiteralPath $Path -Value $rows -Encoding ascii
}

function Read-BoardHashes() {
    $quoted = ($boardStableFiles | ForEach-Object { "'$StableBoardRoot/$_'" }) -join " "
    $remote = "sha256sum $quoted"
    $lines = & ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" $remote 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Board SHA256 command failed: $($lines -join [Environment]::NewLine)"
    }
    $normalised = foreach ($line in $lines) {
        if ($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') {
            throw "Unexpected board SHA256 output: $line"
        }
        $hash = $Matches[1].ToLowerInvariant()
        $absolute = $Matches[2]
        $relative = $absolute.Substring($StableBoardRoot.Length + 1)
        "$hash  $relative"
    }
    return @($normalised)
}

function Read-HashMap([string[]]$Lines) {
    $map = @{}
    foreach ($line in $Lines) {
        if ($line -match '^([0-9a-f]{64})\s+(.+)$') {
            $map[$Matches[2]] = $Matches[1]
        }
    }
    return $map
}

function Proof-Value([string]$Line, [string]$Name) {
    if ($Line -match "(?:^|\s)$([regex]::Escape($Name))=([^\s]+)") {
        return $Matches[1]
    }
    throw "Missing proof field '$Name'"
}

function Invoke-FixedCliViaUart(
    [string]$Command,
    [string]$LogPath,
    [int]$TimeoutSeconds = 300
) {
    $device = Get-CimInstance Win32_PnPEntity | Where-Object {
        $_.Name -match "\($([regex]::Escape($Port))\)$"
    }
    if (-not $device) {
        throw "Serial port $Port is not present"
    }
    if ($ExpectedFtdiSerial -and $device.PNPDeviceID -notmatch [regex]::Escape($ExpectedFtdiSerial)) {
        throw "Serial port $Port does not match expected FTDI serial $ExpectedFtdiSerial"
    }
    $marker = "__WEB3B_WEB0_RC_"
    $serialCommand = "$Command; rc=`$?; echo ${marker}`${rc}__"
    $serial = [System.IO.Ports.SerialPort]::new(
        $Port,
        115200,
        [System.IO.Ports.Parity]::None,
        8,
        [System.IO.Ports.StopBits]::One
    )
    $serial.Handshake = [System.IO.Ports.Handshake]::None
    $serial.Encoding = [Text.Encoding]::UTF8
    $serial.NewLine = "`n"
    $serial.ReadTimeout = 250
    $serial.WriteTimeout = 2000
    $captured = [System.Text.StringBuilder]::new()
    Set-Content -LiteralPath $LogPath -Value "" -Encoding utf8
    try {
        $serial.Open()
        $serial.Write("`n")
        Start-Sleep -Milliseconds 300
        $serial.WriteLine($serialCommand)
        $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
        while ([DateTime]::UtcNow -lt $deadline) {
            $chunk = $serial.ReadExisting()
            if ($chunk.Length -gt 0) {
                [void]$captured.Append($chunk)
                [System.IO.File]::AppendAllText($LogPath, $chunk)
                $match = [regex]::Match(
                    $captured.ToString(),
                    [regex]::Escape($marker) + '(\d+)__'
                )
                if ($match.Success) {
                    $exitCode = [int]$match.Groups[1].Value
                    if ($exitCode -ne 0) {
                        throw "UART CLI fixed prompt failed with exit code $exitCode"
                    }
                    return $captured.ToString()
                }
            }
            Start-Sleep -Milliseconds 100
        }
        throw "UART CLI fixed prompt timed out after $TimeoutSeconds seconds"
    } finally {
        if ($serial.IsOpen) {
            $serial.Close()
        }
        $serial.Dispose()
    }
}

try {
    $migrationGate = Get-Content -Raw -LiteralPath $boardGatePath | ConvertFrom-Json
    $promotionGate = Get-Content -Raw -LiteralPath $promotionGatePath | ConvertFrom-Json
    Copy-Item -LiteralPath $boardGatePath -Destination (Join-Path $evidenceRoot "board_gate_snapshot.json")
    Copy-Item -LiteralPath $promotionGatePath -Destination (Join-Path $evidenceRoot "promotion_gate_snapshot.json")

    if ($migrationGate.hardware_smoke.status -ne "PASS") { throw "Migration hardware smoke is not PASS" }
    if ($migrationGate.all_252_linear.status -ne "PASS") { throw "252-Linear gate is not PASS" }
    if ($migrationGate.warm_e2e.status -ne "PASS") { throw "Migration warm E2E is not PASS" }
    if ([bool]$migrationGate.warm_e2e.cpu_linear_fallback) { throw "Migration gate used CPU Linear fallback" }
    if ([int64]$migrationGate.warm_e2e.pl_kernel_calls -le 0) { throw "Migration gate has no PL calls" }
    if ($promotionGate.promotion_status -ne "PROMOTED") { throw "Current runtime was not promoted" }
    if ($promotionGate.e2e.status -ne "PASS") { throw "Promoted E2E gate is not PASS" }
    if ([bool]$promotionGate.e2e.cpu_linear_fallback) { throw "Promoted gate used CPU Linear fallback" }
    if ([int64]$promotionGate.e2e.pl_kernel_calls -le 0) { throw "Promoted gate has no PL calls" }
    if ($promotionGate.build_id -ne "0x51317342") { throw "Promoted Build ID mismatch" }

    $hostBeforePath = Join-Path $evidenceRoot "stable_hashes_before.sha256"
    $hostAfterPath = Join-Path $evidenceRoot "stable_hashes.sha256"
    Write-HostHashes $hostBeforePath
    $boardBefore = Read-BoardHashes
    Set-Content -LiteralPath (Join-Path $evidenceRoot "board_stable_hashes_before.sha256") -Value $boardBefore -Encoding ascii

    $toolPath = "/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    $pythonPath = "$StableBoardRoot/runtime:$StableBoardRoot/runtime/vendor"
    $boardCommand = "cd $StableBoardRoot && printf '%s' '$FixedPromptBase64' | base64 -d | sudo -n -E env PATH=$toolPath PYTHONPATH=$pythonPath XILINX_XRT=/usr LD_LIBRARY_PATH=/usr/lib /usr/local/share/pynq-venv/bin/python3 runtime/chat.py --root $StableBoardRoot --max-new-tokens $MaxNewTokens --sampling argmax"
    $exactCommands = @(
        "# Transport: COM3 serial console; SSH is used only for read-only SHA-256",
        "# Prompt: $fixedPrompt",
        $boardCommand
    )
    Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Value $exactCommands -Encoding utf8
    $cliStarted = Get-Date
    $cliLogPath = Join-Path $evidenceRoot "cli_fixed_prompt.log"
    $cliRaw = Invoke-FixedCliViaUart $boardCommand $cliLogPath
    $cliOutput = $cliRaw -split "\r?\n"
    $cliElapsedMs = ((Get-Date) - $cliStarted).TotalMilliseconds

    # Capture the complete answer up to the proof line so multiline model
    # output remains deterministic evidence instead of being truncated to the
    # first display line.
    $answerMatch = [regex]::Match(
        $cliRaw,
        'Qwen-FPGA > (?<answer>.*?)\r?\n\[FPGA PROOF\] result=',
        [Text.RegularExpressions.RegexOptions]::Singleline
    )
    $proofLine = @($cliOutput | Where-Object { $_ -match '^\[FPGA PROOF\] result=' }) | Select-Object -Last 1
    $headerLine = @($cliOutput | Where-Object { $_ -match '^\[FPGA PROOF\] manager=' }) | Select-Object -Last 1
    if (-not $answerMatch.Success) { throw "CLI answer block missing" }
    if (-not $proofLine) { throw "CLI proof line missing" }
    if (-not $headerLine) { throw "CLI FPGA header missing" }

    $answer = ($answerMatch.Groups['answer'].Value -replace "`r`n", "`n").Trim()
    $result = Proof-Value $proofLine "result"
    $buildId = Proof-Value $proofLine "build_id"
    $prefillBuildId = Proof-Value $proofLine "prefill_build_id"
    $plCalls = [int64](Proof-Value $proofLine "pl_kernel_calls")
    $plMacros = [int64](Proof-Value $proofLine "pl_macros")
    $promptTokens = [int](Proof-Value $proofLine "prompt_tokens")
    $generatedTokens = [int](Proof-Value $proofLine "generated_tokens")
    $ttftMs = [double](Proof-Value $proofLine "ttft_ms")
    $requestWallMs = [double](Proof-Value $proofLine "request_wall_ms")
    $cpuFallback = -not ($headerLine -match 'cpu_fallback=false')

    if ($result -ne "PASS") { throw "CLI proof did not PASS" }
    if ($buildId -ne "0x51317342") { throw "CLI Build ID mismatch" }
    if ($prefillBuildId -ne "0x51317342") { throw "CLI Prefill Build ID mismatch" }
    if ($plCalls -le 0 -or $plMacros -le 0) { throw "CLI did not advance FPGA counters" }
    if ($generatedTokens -le 0) { throw "CLI generated no tokens" }
    if ($cpuFallback) { throw "CLI reported CPU fallback" }

    Write-HostHashes $hostAfterPath
    $boardAfter = Read-BoardHashes
    Set-Content -LiteralPath (Join-Path $evidenceRoot "board_stable_hashes.sha256") -Value $boardAfter -Encoding ascii

    $hostBefore = Get-Content -LiteralPath $hostBeforePath
    $hostAfter = Get-Content -LiteralPath $hostAfterPath
    if (@(Compare-Object $hostBefore $hostAfter).Count -ne 0) {
        throw "Stable host files changed during Web-0"
    }
    if (@(Compare-Object $boardBefore $boardAfter).Count -ne 0) {
        throw "Stable board files changed during Web-0"
    }
    $hostMap = Read-HashMap $hostAfter
    $boardMap = Read-HashMap $boardAfter
    foreach ($relative in $hostStableFiles) {
        if ($hostMap[$relative] -ne $boardMap[$relative]) {
            throw "Host/board stable hash mismatch: $relative"
        }
    }

    $cliResult = [ordered]@{
        result = "PASS"
        prompt = $fixedPrompt
        sampling = "argmax"
        max_new_tokens = $MaxNewTokens
        answer = $answer
        build_id = $buildId
        prefill_build_id = $prefillBuildId
        cpu_linear_fallback = $cpuFallback
        pl_kernel_calls = $plCalls
        pl_macros = $plMacros
        prompt_tokens = $promptTokens
        generated_tokens = $generatedTokens
        ttft_ms = $ttftMs
        request_wall_ms = $requestWallMs
        host_observed_wall_ms = $cliElapsedMs
    }
    $cliResult | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceRoot "cli_fixed_prompt.json") -Encoding utf8

    $manifest = [ordered]@{
        result = "PASS"
        milestone = "Web-0"
        timestamp = $Timestamp
        model = "Qwen2.5-3B-Instruct"
        device = "AMD KV260"
        architecture = "aarch64-cortex-a53"
        stable_host_root = "deployment/qwen25_3b_packetdf"
        stable_board_root = $StableBoardRoot
        build_id = "0x51317342"
        prefill_build_id = "0x51317342"
        migration_gate = "PASS"
        promotion_gate = "PROMOTED"
        cpu_linear_fallback = $false
        pl_kernel_calls = $plCalls
        host_stable_file_count = $hostStableFiles.Count
        board_stable_file_count = $boardStableFiles.Count
        host_board_hashes_match = $true
        stable_candidate_unchanged = $true
        cli_fixed_prompt = "PASS"
        fixed_prompt = $fixedPrompt
        sampling = "argmax"
        max_new_tokens = $MaxNewTokens
        failed_checks = @()
        blocked_checks = @()
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceRoot "baseline_manifest.json") -Encoding utf8

    $summary = @"
# Web-0 Baseline Freeze - PASS

- Model: Qwen2.5-3B-Instruct
- Device: AMD KV260 (aarch64 Cortex-A53)
- Stable host root: deployment/qwen25_3b_packetdf/
- Stable board root: $StableBoardRoot
- Build ID / Prefill Build ID: $buildId / $prefillBuildId
- Historical migration gate: PASS
- Promoted four-core runtime gate: PROMOTED and E2E PASS
- Fixed CLI prompt: $fixedPrompt
- Deterministic answer: $answer
- FPGA proof: result=$result, PL calls=$plCalls, PL macros=$plMacros
- CPU Linear fallback: false
- TTFT / request wall: $([math]::Round($ttftMs, 3)) / $([math]::Round($requestWallMs, 3)) ms
- Stable host key files: $($hostStableFiles.Count)/$($hostStableFiles.Count) host/board SHA-256 match
- Stable board key files: $($boardStableFiles.Count)/$($boardStableFiles.Count) recorded before/after with no change
- Stable candidate changed during gate: no

Go decision: PASS; Web-1 is permitted, but has not started in this run.
"@
    Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Value $summary -Encoding utf8
    Write-Output "WEB0_PASS"
    Write-Output "EVIDENCE=$evidenceRoot"
} catch {
    $message = $_.Exception.Message
    $failure = [ordered]@{
        result = "FAIL"
        milestone = "Web-0"
        timestamp = $Timestamp
        error = $message
        failed_checks = @($message)
        blocked_checks = @()
    }
    $failure | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceRoot "baseline_manifest.json") -Encoding utf8
    Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Value "# Web-0 Baseline Freeze — FAIL`n`n$message`n" -Encoding utf8
    Write-Error "WEB0_FAIL: $message"
}
