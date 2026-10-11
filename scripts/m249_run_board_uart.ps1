[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$buildResultPath = Join-Path $workspace 'deployment\mage_vl4b\M249_SSDLITE_TRANSFER_BOOTSTRAP_RESULT.json'
$buildResult = Get-Content -LiteralPath $buildResultPath -Raw | ConvertFrom-Json
if ($buildResult.status -ne 'PASS') { throw 'M249_BOOTSTRAP_NOT_PASS' }
$bootstrap = (Resolve-Path -LiteralPath (Join-Path $workspace $buildResult.directory)).Path
$manifestPath = Join-Path $bootstrap 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $buildResult.package_manifest_sha256 -or $manifest.file_count -ne 4) {
    throw 'M249_BOOTSTRAP_MANIFEST_FAIL'
}
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m249_bootstrap'
$attemptRelative = "tmp\m249_ssdlite_network\attempt_$Attempt"
$attemptRoot = Join-Path $workspace $attemptRelative
if (Test-Path -LiteralPath $attemptRoot) { throw "M249 attempt already exists: $attemptRoot" }
New-Item -ItemType Directory -Path $attemptRoot | Out-Null

& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'sudo_uart.log') -TimeoutSeconds 30

$entries = @($manifest.files) + @([pscustomobject]@{path='PACKAGE_MANIFEST.json'})
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $absolute = (Resolve-Path -LiteralPath (Join-Path $bootstrap $name)).Path
    $relative = $absolute.Substring($workspace.Length + 1)
    $safe = $name.Replace('/','_')
    & $uploader -LocalPath $relative -RemotePath "$remote/$name" -Port $Port `
        -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix (Join-Path $attemptRelative "upload_$safe") `
        -ChunkBytes 1800 -TimeoutSeconds 60
}

& $commandTool `
    -Command "python3 $remote/m249_verify_bootstrap.py --root $remote --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'verify_uart.log') -TimeoutSeconds 120
$verifyText = Get-Content -LiteralPath (Join-Path $attemptRoot 'verify_uart.log') -Raw
if ($verifyText -notmatch 'M249_BOOTSTRAP_VERIFY_PASS') { throw 'M249_BOARD_BOOTSTRAP_VERIFY_FAIL' }

$runLog = Join-Path $attemptRoot 'run_uart.log'
& $commandTool -Command "sudo -n bash $remote/m249_run_receiver_and_gate.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'run_uart.log') -TimeoutSeconds $TimeoutSeconds

$formal = Join-Path $workspace "deployment\mage_vl4b\M249_KV260_SSDLITE_BOARD_RESULT_$Attempt.json"
& $python -B (Join-Path $PSScriptRoot 'm249_collect_board_uart.py') --log $runLog --result $formal
if ($LASTEXITCODE -ne 0) { throw "M249 collector failed exit=$LASTEXITCODE" }
Write-Output 'M249_KV260_SSDLITE_UART_GATE_PASS'
