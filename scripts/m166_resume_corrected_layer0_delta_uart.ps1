[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M166_M120_CORRECTED_LAYER0_DELTA_RESULT.json') -Raw | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M166_DELTA_NOT_PASS' }
$delta = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $delta 'DELTA_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.delta_manifest_sha256 -or $manifest.file_count -ne 5) { throw 'M166_DELTA_MANIFEST_FAIL' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01'

# The interrupted first invocation completed the first four uploads.  Resume
# only the missing payload and manifest; the board-side applier rehashes the
# entire six-file closure before making any candidate visible.
$remaining = @(
    [pscustomobject]@{ path = 'auxiliary/m77_text_aux_fp16.npz'; log = "tmp\m166_layer0\upload_${Attempt}_auxiliary_m77_text_aux_fp16.npz_uart.log" },
    [pscustomobject]@{ path = 'DELTA_MANIFEST.json'; log = "tmp\m166_layer0\upload_${Attempt}_DELTA_MANIFEST.json_uart.log" }
)
foreach ($item in $remaining) {
    $absoluteLog = Join-Path $workspace $item.log
    if (Test-Path -LiteralPath $absoluteLog) { throw "M166 resume log already exists: $($item.log)" }
    & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath ((Resolve-Path -LiteralPath (Join-Path $delta $item.path)).Path.Substring($workspace.Length + 1)) `
        -RemotePath "$remote/$($item.path)" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $item.log -TimeoutSeconds 300
}

$runLog = "tmp\m166_layer0\stage_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_${Attempt}.json"
if (Test-Path -LiteralPath (Join-Path $workspace $runLog)) { throw "M166 run log exists: $runLog" }
if (Test-Path -LiteralPath (Join-Path $workspace $formal)) { throw "M166 result exists: $formal" }
$command = "sudo -n python3 $remote/m166_apply_corrected_layer0_delta.py --delta-root $remote --expected-delta-manifest-sha256 $manifestHash --source /home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_layer0_board_candidate --output /home/ubuntu/tellme_m120_m89x2_20260901/m165_m120_layer0_board_candidate --result /home/ubuntu/tellme_m120_m89x2_20260901/results/M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT.json"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
& $python (Join-Path $PSScriptRoot 'm166_collect_corrected_stage_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M166 collector failed exit=$LASTEXITCODE" }
Write-Output 'M166_CORRECTED_LAYER0_BOARD_STAGE_RESUME_UART_PASS'
