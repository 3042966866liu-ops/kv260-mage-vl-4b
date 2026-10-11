param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [int]$ReadyTimeoutSeconds = 420
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$webRoot = Join-Path $workspace "deployment\qwen25_3b_web"
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-1\$Timestamp"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
$baseUrl = "http://${BoardIp}:8000"
$python = "C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

function Write-JsonFile([object]$Value, [string]$Path) {
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Invoke-BoardSsh([string]$Command) {
    $output = & ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$BoardUser@$BoardIp" $Command 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "SSH command failed: $($output -join [Environment]::NewLine)"
    }
    return @($output)
}

function Read-Health() {
    $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/api/health"
    if ([int]$response.StatusCode -ne 200) {
        throw "health returned HTTP $($response.StatusCode)"
    }
    return ($response.Content | ConvertFrom-Json)
}

$exactCommands = @(
    "$python -m unittest discover -s deployment/qwen25_3b_web/tests -p test_*.py",
    "GET $baseUrl/api/health",
    "GET $baseUrl/",
    "ssh $BoardUser@$BoardIp cat /home/ubuntu/tellme_qwen25_3b_web/web3b_server.log"
)
Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Value $exactCommands -Encoding utf8

$failed = [System.Collections.Generic.List[string]]::new()
$blocked = [System.Collections.Generic.List[string]]::new()
$healthSamples = @()
$lastHealth = $null
$testLog = @()
$serverLog = @()

try {
    Push-Location $workspace
    try {
        $testLog = & $python -m unittest discover -s deployment/qwen25_3b_web/tests -p "test_*.py" 2>&1
        if ($LASTEXITCODE -ne 0) {
            $failed.Add("host unit/API contract tests failed")
        }
    } finally {
        Pop-Location
    }
    Set-Content -LiteralPath (Join-Path $evidenceRoot "host_tests.log") -Value $testLog -Encoding utf8

    $hashRows = foreach ($file in Get-ChildItem -LiteralPath $webRoot -Recurse -File | Where-Object {
        $_.FullName -notmatch '[\\/]__pycache__[\\/]'
    }) {
        $relative = $file.FullName.Substring($webRoot.Length + 1).Replace("\", "/")
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
    Set-Content -LiteralPath (Join-Path $evidenceRoot "source_hashes.sha256") -Value $hashRows -Encoding ascii

    $deadline = [DateTime]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $lastHealth = Read-Health
            if ($lastHealth.status -in @("ready", "error")) { break }
        } catch {
            $lastHealth = $null
        }
        Start-Sleep -Seconds 2
    }

    if ($null -eq $lastHealth) {
        $blocked.Add("health endpoint was unreachable before timeout")
    } elseif ($lastHealth.status -eq "error") {
        $failed.Add("runtime startup entered error: $($lastHealth.error)")
    } elseif ($lastHealth.status -ne "ready") {
        $failed.Add("service did not reach ready (status=$($lastHealth.status))")
    } else {
        for ($index = 0; $index -lt 5; $index++) {
            $healthSamples += Read-Health
        }
        $ids = @($healthSamples | ForEach-Object { $_.runtime_instance_id } | Sort-Object -Unique)
        if ($ids.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$ids[0])) {
            $failed.Add("runtime_instance_id changed or was empty across five health requests")
        }
        if (@($healthSamples | Where-Object { [int]$_.model_load_count -ne 1 }).Count -gt 0) {
            $failed.Add("model_load_count was not exactly one")
        }
        if (@($healthSamples | Where-Object { $_.build_id -ne "0x51317342" -or $_.prefill_build_id -ne "0x51317342" }).Count -gt 0) {
            $failed.Add("Build ID or Prefill Build ID mismatch")
        }
        if (@($healthSamples | Where-Object { $_.cpu_linear_fallback -ne $false }).Count -gt 0) {
            $failed.Add("health did not prove cpu_linear_fallback=false")
        }
        if (@($healthSamples | Where-Object { $_.warmed_up -ne $true -or [int]$_.warmup_count -ne 1 }).Count -gt 0) {
            $failed.Add("warm-up state/count was invalid")
        }
        $requestCounts = @($healthSamples | ForEach-Object { [int]$_.request_count } | Sort-Object -Unique)
        if ($requestCounts.Count -ne 1) {
            $failed.Add("health requests changed inference request_count")
        }
        $page = Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/"
        Set-Content -LiteralPath (Join-Path $evidenceRoot "index.html") -Value $page.Content -Encoding utf8
        if ([int]$page.StatusCode -ne 200) {
            $failed.Add("GET / did not return HTTP 200")
        }
    }

    if ($null -ne $lastHealth) {
        Write-JsonFile $lastHealth (Join-Path $evidenceRoot "health_last.json")
    }
    if ($healthSamples.Count -gt 0) {
        Write-JsonFile $healthSamples (Join-Path $evidenceRoot "health_samples.json")
    }
    try {
        $serverLog = Invoke-BoardSsh "cat /home/ubuntu/tellme_qwen25_3b_web/web3b_server.log"
    } catch {
        $serverLog = @($_.Exception.Message)
    }
    Set-Content -LiteralPath (Join-Path $evidenceRoot "server.log") -Value $serverLog -Encoding utf8
} catch {
    $failed.Add("gate exception: $($_.Exception.Message)")
}

$result = if ($blocked.Count -gt 0) { "BLOCKED" } elseif ($failed.Count -gt 0) { "FAIL" } else { "PASS" }
$gate = [ordered]@{
    result = $result
    milestone = "Web-1"
    timestamp = $Timestamp
    service_url = $baseUrl
    status = if ($null -ne $lastHealth) { $lastHealth.status } else { $null }
    runtime_instance_id = if ($null -ne $lastHealth) { $lastHealth.runtime_instance_id } else { $null }
    model_load_count = if ($null -ne $lastHealth) { $lastHealth.model_load_count } else { $null }
    warmup_count = if ($null -ne $lastHealth) { $lastHealth.warmup_count } else { $null }
    build_id = if ($null -ne $lastHealth) { $lastHealth.build_id } else { $null }
    prefill_build_id = if ($null -ne $lastHealth) { $lastHealth.prefill_build_id } else { $null }
    cpu_linear_fallback = if ($null -ne $lastHealth) { $lastHealth.cpu_linear_fallback } else { $null }
    health_sample_count = $healthSamples.Count
    failed_checks = @($failed)
    blocked_checks = @($blocked)
}
Write-JsonFile $gate (Join-Path $evidenceRoot "web1_gate.json")

$summary = @"
# Web-1 HTTP Service - $result

- URL: $baseUrl
- Final status: $($gate.status)
- Runtime instance: $($gate.runtime_instance_id)
- Model load count: $($gate.model_load_count)
- Warm-up count: $($gate.warmup_count)
- Build / Prefill Build: $($gate.build_id) / $($gate.prefill_build_id)
- CPU Linear fallback: $($gate.cpu_linear_fallback)
- Health samples: $($gate.health_sample_count)
- Failed checks: $($failed -join '; ')
- Blocked checks: $($blocked -join '; ')
"@
Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Value $summary -Encoding utf8

Write-Output "WEB1_$result"
Write-Output "EVIDENCE=$evidenceRoot"
if ($result -ne "PASS") { exit 1 }
