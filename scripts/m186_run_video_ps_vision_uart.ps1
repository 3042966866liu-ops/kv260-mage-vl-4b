[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 6000
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M186_M181_PS_VISION_BOOTSTRAP_RESULT.json') -Raw | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M186_BOOTSTRAP_NOT_PASS' }
$package = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256 -or $manifest.file_count -ne 4) { throw 'M186_BOOTSTRAP_MANIFEST_FAIL' }
$remoteRoot = '/home/ubuntu/tellme_m120_m89x2_20260901/m186_gate'

$sudoLog = "tmp\m186_ps_vision\sudo_${Attempt}_uart.log"
if (Test-Path -LiteralPath (Join-Path $workspace $sudoLog)) { throw "M186 sudo log exists: $sudoLog" }
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $sudoLog -TimeoutSeconds 30

foreach ($entry in @($manifest.files) + @([pscustomobject]@{path='PACKAGE_MANIFEST.json'})) {
    $relative = [string]$entry.path
    $safe = $relative -replace '[^A-Za-z0-9_.-]', '_'
    $log = "tmp\m186_ps_vision\upload_${Attempt}_${safe}_uart.log"
    if (Test-Path -LiteralPath (Join-Path $workspace $log)) { throw "M186 upload log exists: $log" }
    & (Join-Path $PSScriptRoot 'm75c_uart_put_file_base64.ps1') `
        -LocalPath ((Resolve-Path -LiteralPath (Join-Path $package $relative)).Path.Substring($workspace.Length + 1)) `
        -RemotePath "$remoteRoot/$relative" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $log -TimeoutSeconds 180
}

$verifyLog = "tmp\m186_ps_vision\verify_${Attempt}_uart.log"
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command "python3 $remoteRoot/m186_verify_video_ps_vision_bootstrap.py --root $remoteRoot --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $verifyLog -TimeoutSeconds 180
$verifyText = Get-Content -LiteralPath (Join-Path $workspace $verifyLog) -Raw
if ($verifyText -notmatch 'M186_PS_VISION_BOOTSTRAP_VERIFY_PASS') { throw 'M186_BOARD_BOOTSTRAP_VERIFY_FAIL' }

$runLog = "tmp\m186_ps_vision\run_${Attempt}_uart.log"
$formal = "deployment\mage_vl4b\M186_M181_PS_VISION_BOARD_RESULT_${Attempt}.json"
if (Test-Path -LiteralPath (Join-Path $workspace $runLog)) { throw "M186 run log exists: $runLog" }
if (Test-Path -LiteralPath (Join-Path $workspace $formal)) { throw "M186 formal result exists: $formal" }
$commandError = $null
try {
    & (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
        -Command "sudo -n bash $remoteRoot/m186_run_video_ps_vision_board_gate.sh" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}
& $python (Join-Path $PSScriptRoot 'm186_collect_video_ps_vision_uart.py') --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M186 collector failed exit=$LASTEXITCODE" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M186_M181_PS_VISION_UART_PASS'
