[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 7200
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$buildResult = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M162_M120_NETWORK_BOOTSTRAP_RESULT_V2.json') -Raw | ConvertFrom-Json
if ($buildResult.status -ne 'PASS') { throw 'M162_BOOTSTRAP_NOT_PASS' }
$package = (Resolve-Path -LiteralPath (Join-Path $workspace $buildResult.directory)).Path
$manifest = Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json')).Hash.ToLowerInvariant()
if ($manifestHash -ne $buildResult.package_manifest_sha256 -or $manifest.file_count -ne 4) { throw 'M162_BOOTSTRAP_MANIFEST_FAIL' }
$remoteRoot = '/home/ubuntu/tellme_m120_m89x2_20260901/m162_bootstrap_v2'

foreach ($entry in @($manifest.files) + @([pscustomobject]@{path='PACKAGE_MANIFEST.json'})) {
    $relative = [string]$entry.path
    $safe = $relative -replace '[^A-Za-z0-9_.-]', '_'
    $log = "tmp\m162_network\upload_${Attempt}_${safe}_uart.log"
    if (Test-Path -LiteralPath (Join-Path $workspace $log)) { throw "M162 upload log exists: $log" }
    & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath ((Resolve-Path -LiteralPath (Join-Path $package $relative)).Path.Substring($workspace.Length + 1)) `
        -RemotePath "$remoteRoot/$relative" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $log -TimeoutSeconds 180
}

$verifyLog = "tmp\m162_network\verify_${Attempt}_uart.log"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $remoteRoot/m162_verify_network_bootstrap.py --root $remoteRoot --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $verifyLog -TimeoutSeconds 180
$verifyText = Get-Content -LiteralPath (Join-Path $workspace $verifyLog) -Raw
if ($verifyText -notmatch 'M162_NETWORK_BOOTSTRAP_VERIFY_PASS') { throw 'M162_BOARD_BOOTSTRAP_VERIFY_FAIL' }

$runLog = "tmp\m162_network\import_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M162_M120_NETWORK_BOARD_IMPORT_RESULT_${Attempt}.json"
if (Test-Path -LiteralPath (Join-Path $workspace $runLog)) { throw "M162 run log exists: $runLog" }
if (Test-Path -LiteralPath (Join-Path $workspace $formal)) { throw "M162 formal result exists: $formal" }
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "sudo -n bash $remoteRoot/m162_run_m120_network_import.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds

& $python (Join-Path $PSScriptRoot 'm162_collect_network_import_uart.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M162 collector failed exit=$LASTEXITCODE" }
Write-Output 'M162_M120_NETWORK_IMPORT_UART_PASS'
