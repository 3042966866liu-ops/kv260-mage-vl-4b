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
$manifest = Get-Content -LiteralPath (Join-Path $delta 'DELTA_MANIFEST.json') -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $delta 'DELTA_MANIFEST.json')).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.delta_manifest_sha256 -or $manifest.file_count -ne 5) { throw 'M166_DELTA_MANIFEST_FAIL' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01'

foreach ($entry in @($manifest.files) + @([pscustomobject]@{path='DELTA_MANIFEST.json'})) {
    $relative = [string]$entry.path
    $safe = $relative -replace '[^A-Za-z0-9_.-]', '_'
    $log = "tmp\m166_layer0\upload_${Attempt}_${safe}_uart.log"
    if (Test-Path -LiteralPath (Join-Path $workspace $log)) { throw "M166 upload log exists: $log" }
    & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath ((Resolve-Path -LiteralPath (Join-Path $delta $relative)).Path.Substring($workspace.Length + 1)) `
        -RemotePath "$remote/$relative" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $log -TimeoutSeconds 300
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
Write-Output 'M166_CORRECTED_LAYER0_BOARD_STAGE_UART_PASS'
