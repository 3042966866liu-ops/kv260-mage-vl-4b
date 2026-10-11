[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 3600
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M190_RUNTIME_BOOTSTRAP_RESULT.json') -Raw | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M190_BOOTSTRAP_NOT_PASS' }
$package = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256 -or $manifest.file_count -ne 3) { throw 'M190_BOOTSTRAP_MANIFEST_FAIL' }
$remoteRoot = '/home/ubuntu/tellme_m120_m89x2_20260901/m190_bootstrap'

$sudoLog = "tmp\m190_runtime\sudo_${Attempt}_uart.log"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $sudoLog -TimeoutSeconds 30

foreach ($entry in @($manifest.files) + @([pscustomobject]@{path='PACKAGE_MANIFEST.json'})) {
    $relative = [string]$entry.path
    $log = "tmp\m190_runtime\upload_${Attempt}_${relative}_uart.log"
    & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath ((Resolve-Path -LiteralPath (Join-Path $package $relative)).Path.Substring($workspace.Length + 1)) `
        -RemotePath "$remoteRoot/$relative" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $log -TimeoutSeconds 180
}

$verifyLog = "tmp\m190_runtime\verify_${Attempt}_uart.log"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $remoteRoot/m190_verify_runtime_bootstrap.py --root $remoteRoot --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $verifyLog -TimeoutSeconds 180
if ((Get-Content -LiteralPath (Join-Path $workspace $verifyLog) -Raw) -notmatch 'M190_RUNTIME_BOOTSTRAP_VERIFY_PASS') { throw 'M190_BOARD_BOOTSTRAP_VERIFY_FAIL' }

$runLog = "tmp\m190_runtime\install_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M190_ARM64_MAGE_RUNTIME_INSTALL_RESULT_${Attempt}.json"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "sudo -n bash $remoteRoot/m190_run_runtime_receiver.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds

& $python (Join-Path $PSScriptRoot 'm190_collect_runtime_uart.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M190 collector failed exit=$LASTEXITCODE" }
Write-Output 'M190_ARM64_RUNTIME_RECEIVER_UART_PASS'
