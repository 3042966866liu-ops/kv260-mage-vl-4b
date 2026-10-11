[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 300
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -Raw (Join-Path $workspace 'deployment\mage_vl4b\M227_RUNTIME_BASE_PATCH_BUILD_RESULT.json') | ConvertFrom-Json
$package = (Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M227_BOOTSTRAP_HASH_FAIL' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m227_runtime_base_patch'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m227_runtime_base\sudo_$Attempt.log" -TimeoutSeconds 30
$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $localAbsolute = (Resolve-Path (Join-Path $package $name)).Path
    $localRelative = $localAbsolute.Substring($workspace.Length + 1)
    & $uploader -LocalPath $localRelative -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix "tmp\m227_runtime_base\upload_${Attempt}_$name" -TimeoutSeconds 60
}
& $commandTool -Command "python3 $remote/m227_verify_patch.py --root $remote --expected-manifest-sha256 $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m227_runtime_base\verify_$Attempt.log" -TimeoutSeconds 120
& $commandTool -Command "bash -n $remote/m227_board_restart.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m227_runtime_base\bash_n_$Attempt.log" -TimeoutSeconds 60
$runLog = "tmp\m227_runtime_base\run_$Attempt.log"
$formal = "deployment\mage_vl4b\M227_RUNTIME_BASE_PATCH_BOARD_RESULT_$Attempt.json"
try {
    & $commandTool -Command "sudo -n bash $remote/m227_board_restart.sh $manifestHash" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch { Write-Warning $_ }
& $python (Join-Path $PSScriptRoot 'm227_collect_board_result.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M227 board gate failed; evidence at $formal" }
Write-Output 'M227_RUNTIME_BASE_PATCH_UART_PASS'
