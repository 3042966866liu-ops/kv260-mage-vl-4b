[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 900
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M240_PS_ATTENTION_BOARD_DELTA_RESULT.json') -Raw | ConvertFrom-Json
if ($build.status -ne 'PASS' -or $build.gate -ne 'M240-PS-attention-board-micro-gate-delta-build') { throw 'M240 build identity failed' }
$package = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M240 manifest hash mismatch' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m240_ps_attention_delta'
$result = "/home/ubuntu/tellme_m120_m89x2_20260901/results/m240_ps_attention_$Attempt"
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$logRoot = Join-Path $workspace "tmp\m240_ps_attention\attempt_$Attempt"
$runLog = Join-Path $logRoot 'run_uart.log'
$formal = Join-Path $workspace "deployment\mage_vl4b\M240_PS_ATTENTION_BOARD_RESULT_$Attempt.json"
if (Test-Path -LiteralPath $logRoot) { throw "M240 attempt exists: $logRoot" }
if (Test-Path -LiteralPath $formal) { throw "M240 result exists: $formal" }
New-Item -ItemType Directory -Path $logRoot | Out-Null
& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m240_ps_attention\attempt_$Attempt\sudo_uart.log" -TimeoutSeconds 30
$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $absolute = (Resolve-Path -LiteralPath (Join-Path $package $name)).Path
    $relative = $absolute.Substring($workspace.Length + 1)
    $safe = $name.Replace('/', '_')
    & $uploader -LocalPath $relative -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix "tmp\m240_ps_attention\attempt_$Attempt\upload_$safe" -ChunkBytes 1800 -TimeoutSeconds 60
}
& $commandTool -Command "python3 $remote/m230_verify_package.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m240_ps_attention\attempt_$Attempt\verify_uart.log" -TimeoutSeconds 120
& $commandTool -Command "bash -n $remote/run_m240_board_gate.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m240_ps_attention\attempt_$Attempt\bash_n_uart.log" -TimeoutSeconds 60
$boardCommand = "sudo -n bash $remote/run_m240_board_gate.sh $remote $result $manifestHash"
$commandError = $null
try {
    & $commandTool -Command $boardCommand -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m240_ps_attention\attempt_$Attempt\run_uart.log" -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}
& $python (Join-Path $PSScriptRoot 'm240_collect_board_uart.py') --log $runLog --result $formal --expected-manifest-sha256 $manifestHash
if ($LASTEXITCODE -ne 0) { throw "M240 board micro-gate failed; UART retained at $runLog" }
if ($null -ne $commandError) { throw $commandError }
'M240_PS_ATTENTION_BOARD_UART_PASS'
