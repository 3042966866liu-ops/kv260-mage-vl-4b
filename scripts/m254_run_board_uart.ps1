[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 420
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$build = Get-Content -Raw (Join-Path $workspace 'deployment\mage_vl4b\M254_DUAL_PATH_WEB_BOARD_CANDIDATE_RESULT_R3.json') | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M254_BUILD_NOT_PASS' }
$candidate = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $candidate 'PACKAGE_MANIFEST.json'
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M254_MANIFEST_HASH_MISMATCH' }
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$attemptRelative = "tmp\m254_dual_path_web\attempt_$Attempt"
$attemptRoot = Join-Path $workspace $attemptRelative
if (Test-Path -LiteralPath $attemptRoot) { throw "M254 attempt already exists: $attemptRoot" }
$formal = Join-Path $workspace "deployment\mage_vl4b\M254_DUAL_PATH_WEB_BOARD_RESULT_$Attempt.json"
if (Test-Path -LiteralPath $formal) { throw "M254 result already exists: $formal" }
New-Item -ItemType Directory -Path $attemptRoot | Out-Null
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m254_dual_path_web_candidate'

& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'sudo_uart.log') -TimeoutSeconds 30

$uploadEntries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $uploadEntries) {
    $name = [string]$entry.path
    $absolute = (Resolve-Path -LiteralPath (Join-Path $candidate $name)).Path
    $relative = $absolute.Substring($workspace.Length + 1)
    $safe = $name.Replace('/','_')
    & $uploader -LocalPath $relative -RemotePath "$remote/$name" -Port $Port `
        -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix (Join-Path $attemptRelative "upload_$safe") `
        -ChunkBytes 1800 -TimeoutSeconds 90
}

$verifyLog = Join-Path $attemptRoot 'verify_uart.log'
& $commandTool -Command "python3 $remote/verify_m254_candidate.py --root $remote --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'verify_uart.log') -TimeoutSeconds 120
if ((Get-Content -Raw $verifyLog) -notmatch 'M254_STAGED_PACKAGE_VERIFY_PASS') {
    throw 'M254_STAGED_PACKAGE_VERIFY_FAIL'
}

& $commandTool -Command "bash -n $remote/run_m254_board_gate.sh" -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath (Join-Path $attemptRelative 'bash_n_uart.log') `
    -TimeoutSeconds 60

$runLog = Join-Path $attemptRoot 'run_uart.log'
$commandError = $null
try {
    & $commandTool -Command "sudo -n bash $remote/run_m254_board_gate.sh $manifestHash $Attempt" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath (Join-Path $attemptRelative 'run_uart.log') -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}

& $python -B (Join-Path $PSScriptRoot 'm254_collect_board_uart.py') --log $runLog --result $formal `
    --package-manifest-sha256 $manifestHash
if ($LASTEXITCODE -ne 0) { throw "M254 collector failed exit=$LASTEXITCODE" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M254_KV260_DUAL_PATH_WEB_UART_GATE_PASS'
