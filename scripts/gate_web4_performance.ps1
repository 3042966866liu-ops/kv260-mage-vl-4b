param(
    [string]$BoardIp = "192.168.77.2",
    [string]$BoardUser = "ubuntu",
    [string]$SshKey = "tmp\m2_ssh\id_ed25519",
    [string]$Timestamp = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [int]$Samples = 5,
    [int]$MaxNewTokens = 1,
    [int]$RequestTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$evidenceRoot = Join-Path $workspace "artifacts\WEB-3B\Web-4\$Timestamp"
$webRoot = Join-Path $workspace "deployment\qwen25_3b_web"
$baseUrl = "http://${BoardIp}:8000"
$sshKeyPath = (Resolve-Path (Join-Path $workspace $SshKey)).Path
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

function Write-JsonFile([object]$Value,[string]$Path){$Value|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $Path -Encoding utf8}
function Median([double[]]$Values){$sorted=@($Values|Sort-Object);if($sorted.Count%2){return [double]$sorted[[int][math]::Floor($sorted.Count/2)]};return ([double]$sorted[$sorted.Count/2-1]+[double]$sorted[$sorted.Count/2])/2.0}
function Read-Health(){(Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri "$baseUrl/api/health").Content|ConvertFrom-Json}

$failed=[System.Collections.Generic.List[string]]::new();$blocked=[System.Collections.Generic.List[string]]::new();$results=@();$healthBefore=$null;$healthAfter=$null
try{
    $web0=Get-ChildItem -LiteralPath (Join-Path $workspace "artifacts\WEB-3B\Web-0") -Directory|Sort-Object Name -Descending|Where-Object{Test-Path (Join-Path $_.FullName "cli_fixed_prompt.json")}|Select-Object -First 1
    if($null-eq$web0){throw "Web-0 CLI reference missing"}
    $reference=Get-Content -Raw -LiteralPath (Join-Path $web0.FullName "cli_fixed_prompt.json")|ConvertFrom-Json
    $baselineTtft=[double]$reference.ttft_ms
    $threshold=[math]::Max($baselineTtft*1.15,$baselineTtft+500.0)
    $payload=[ordered]@{prompt=[string]$reference.prompt;max_new_tokens=$MaxNewTokens;sampling="argmax"}
    $payloadJson=$payload|ConvertTo-Json -Compress
    Set-Content -LiteralPath (Join-Path $evidenceRoot "exact_command.txt") -Encoding utf8 -Value "Repeat $Samples times: POST $baseUrl/api/chat`nContent-Type: application/json`n$payloadJson"
    $healthBefore=Read-Health
    Write-JsonFile $healthBefore (Join-Path $evidenceRoot "warmup_health.json")
    if($healthBefore.status-ne"ready"-or$healthBefore.warmed_up-ne$true-or[int]$healthBefore.warmup_count-ne1){$failed.Add("service was not ready after exactly one warm-up")}
    for($i=1;$i-le$Samples;$i++){
        $watch=[Diagnostics.Stopwatch]::StartNew()
        $http=Invoke-WebRequest -UseBasicParsing -TimeoutSec $RequestTimeoutSeconds -Method Post -Uri "$baseUrl/api/chat" -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($payloadJson))
        $watch.Stop();$body=$http.Content|ConvertFrom-Json;$proof=$body.proof
        Write-JsonFile $body (Join-Path $evidenceRoot ("hot_request_{0:D2}.json"-f$i))
        $row=[ordered]@{index=$i;http_status=[int]$http.StatusCode;answer=[string]$body.answer;answer_is_cli_prefix=([string]$reference.answer).StartsWith([string]$body.answer,[StringComparison]::Ordinal);host_wall_ms=$watch.Elapsed.TotalMilliseconds;runtime_wall_ms=[double]$proof.request_wall_ms;http_overhead_ms=$watch.Elapsed.TotalMilliseconds-[double]$proof.request_wall_ms;ttft_ms=[double]$proof.ttft_ms;build_id=$proof.build_id;prefill_build_id=$proof.prefill_build_id;pl_kernel_calls=[int64]$proof.pl_kernel_calls;pl_macros=[int64]$proof.pl_macros;prompt_tokens=[int]$proof.prompt_tokens;generated_tokens=[int]$proof.generated_tokens;cpu_linear_fallback=[bool]$proof.cpu_linear_fallback;runtime_instance_id=$body.runtime_instance_id;model_load_count=[int]$body.model_load_count;proof_result=$proof.result}
        $results+=([pscustomobject]$row)
        if($row.http_status-ne200-or$row.proof_result-ne"PASS"){$failed.Add("sample $i HTTP/proof did not PASS")}
        if(-not$row.answer_is_cli_prefix-or[string]::IsNullOrEmpty($row.answer)){$failed.Add("sample $i output is not a non-empty CLI reference prefix")}
        if($row.build_id-ne"0x51317342"-or$row.prefill_build_id-ne"0x51317342"){$failed.Add("sample $i Build ID mismatch")}
        if($row.pl_kernel_calls-le0-or$row.pl_macros-le0-or$row.generated_tokens-le0){$failed.Add("sample $i lacks positive FPGA/token counters")}
        if($row.cpu_linear_fallback){$failed.Add("sample $i used CPU Linear fallback")}
        if($row.runtime_instance_id-ne$healthBefore.runtime_instance_id-or$row.model_load_count-ne1){$failed.Add("sample $i violated runtime singleton")}
    }
    $healthAfter=Read-Health
    if($healthAfter.runtime_instance_id-ne$healthBefore.runtime_instance_id-or[int]$healthAfter.model_load_count-ne1){$failed.Add("runtime singleton changed across performance run")}
    if([int]$healthAfter.request_count-ne([int]$healthBefore.request_count+$Samples)){$failed.Add("request_count did not advance by $Samples")}
    $answers=@($results|ForEach-Object{$_.answer}|Sort-Object -Unique);if($answers.Count-ne1){$failed.Add("hot request outputs were not deterministic")}
    $medianTtft=Median @($results|ForEach-Object{[double]$_.ttft_ms})
    $medianHost=Median @($results|ForEach-Object{[double]$_.host_wall_ms})
    $medianRuntime=Median @($results|ForEach-Object{[double]$_.runtime_wall_ms})
    $medianOverhead=Median @($results|ForEach-Object{[double]$_.http_overhead_ms})
    if($medianTtft-gt$threshold){$failed.Add("median Web TTFT $medianTtft ms exceeds threshold $threshold ms")}
    if($medianOverhead-gt500.0){$failed.Add("median HTTP overhead $medianOverhead ms exceeds 500 ms")}
    Write-JsonFile $results (Join-Path $evidenceRoot "hot_requests.json")
    $summary=[ordered]@{result=if($failed.Count){"FAIL"}else{"PASS"};milestone="Web-4";timestamp=$Timestamp;samples=$Samples;warmup_count=[int]$healthAfter.warmup_count;baseline_source=(Join-Path $web0.FullName "cli_fixed_prompt.json");baseline_cli_ttft_ms=$baselineTtft;ttft_threshold_ms=$threshold;median_web_ttft_ms=$medianTtft;median_host_wall_ms=$medianHost;median_runtime_wall_ms=$medianRuntime;median_http_overhead_ms=$medianOverhead;runtime_instance_id=$healthAfter.runtime_instance_id;model_load_count=[int]$healthAfter.model_load_count;request_count_before=[int]$healthBefore.request_count;request_count_after=[int]$healthAfter.request_count;all_outputs_deterministic=($answers.Count-eq1);all_outputs_cli_prefix=(@($results|Where-Object{-not$_.answer_is_cli_prefix}).Count-eq0);all_fpga_proof_pass=(@($results|Where-Object{$_.proof_result-ne"PASS"-or$_.pl_kernel_calls-le0-or$_.cpu_linear_fallback}).Count-eq0);failed_checks=@($failed);blocked_checks=@($blocked)}
    Write-JsonFile $summary (Join-Path $evidenceRoot "performance_summary.json")
    Write-JsonFile $healthAfter (Join-Path $evidenceRoot "health_after.json")
}catch{if($_.Exception.Message-match'connect|unreachable|timed out'){$blocked.Add($_.Exception.Message)}else{$failed.Add($_.Exception.Message)}}

$hashRows=foreach($file in Get-ChildItem -LiteralPath $webRoot -Recurse -File|Where-Object{$_.FullName-notmatch'[\\/]__pycache__[\\/]'} ){"$((Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant())  $($file.FullName.Substring($webRoot.Length+1).Replace('\','/'))"}
Set-Content -LiteralPath (Join-Path $evidenceRoot "source_hashes.sha256") -Value $hashRows -Encoding ascii
try{$log=& ssh.exe -i $sshKeyPath -o BatchMode=yes -o ConnectTimeout=10 "$BoardUser@$BoardIp" "tail -n 160 /home/ubuntu/tellme_qwen25_3b_web/web3b_server.log" 2>&1;Set-Content -LiteralPath (Join-Path $evidenceRoot "server.log") -Value $log -Encoding utf8}catch{}
$result=if($blocked.Count){"BLOCKED"}elseif($failed.Count){"FAIL"}else{"PASS"}
if(-not(Test-Path (Join-Path $evidenceRoot "performance_summary.json"))){Write-JsonFile ([ordered]@{result=$result;milestone="Web-4";timestamp=$Timestamp;failed_checks=@($failed);blocked_checks=@($blocked)}) (Join-Path $evidenceRoot "performance_summary.json")}
Set-Content -LiteralPath (Join-Path $evidenceRoot "summary.md") -Encoding utf8 -Value "# Web-4 Warm Performance - $result`n`n- Samples: $Samples hot requests after one startup warm-up`n- Each request: same Web-0 prompt, argmax, $MaxNewTokens generated token (TTFT isolation)`n- Failed: $($failed -join '; ')`n- Blocked: $($blocked -join '; ')`n"
Write-Output "WEB4_$result";Write-Output "EVIDENCE=$evidenceRoot";if($result-ne"PASS"){exit 1}
