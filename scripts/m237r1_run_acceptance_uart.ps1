[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$build = Get-Content -Raw 'deployment\mage_vl4b\M237R1_ACCEPTANCE_REPAIR_DELTA_RESULT.json' | ConvertFrom-Json
if ($build.status -ne 'PASS' -or $build.gate -ne 'M237R1-acceptance-repair-delta-build') {
    throw 'M237R1 build identity failed'
}
$package = (Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M237R1 manifest mismatch' }

$root = '/home/ubuntu/tellme_m120_m89x2_20260901'
$remote = "$root/m237r1_acceptance_repair_delta"
$observed = "$root/results/m237_m236_fixed_text_01/fixed_text_measurement.json"
$reference = "$root/results/m179_fixed_text_01/fixed_text_measurement.json"
$result = "$root/results/m237r1_acceptance_repair_$Attempt"
$servicePidFile = "$root/results/m223_realtime_service.pid"
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploadTool = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$logRoot = "tmp\m237r1_acceptance_repair\attempt_$Attempt"
$runLog = Join-Path $workspace "$logRoot\run_uart.log"
$formal = Join-Path $workspace "deployment\mage_vl4b\M237R1_ACCEPTANCE_REPAIR_BOARD_RESULT_$Attempt.json"
if (Test-Path $logRoot) { throw 'M237R1 attempt exists' }
New-Item -ItemType Directory $logRoot | Out-Null

& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "$logRoot\sudo.log" -TimeoutSeconds 30
$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $absolute = (Resolve-Path (Join-Path $package $name)).Path
    $relative = $absolute.Substring($workspace.Length + 1)
    & $uploadTool -LocalPath $relative -RemotePath "$remote/$name" -Port $Port `
        -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPrefix "$logRoot\upload_$($name.Replace('/','_'))" `
        -ChunkBytes 1800 -TimeoutSeconds 60
}
& $commandTool -Command "python3 $remote/m230_verify_package.py --root $remote --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "$logRoot\verify.log" -TimeoutSeconds 120
& $commandTool -Command "bash -n $remote/run_m237r1_acceptance_repair.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "$logRoot\bash_n.log" -TimeoutSeconds 60
$boardCommand = "sudo -n bash $remote/run_m237r1_acceptance_repair.sh $remote $observed $reference $result $manifestHash $servicePidFile"
$boardError = $null
try {
    & $commandTool -Command $boardCommand -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath "$logRoot\run_uart.log" -TimeoutSeconds $TimeoutSeconds
} catch {
    $boardError = $_
}
& $python (Join-Path $PSScriptRoot 'm237r1_collect_acceptance_uart.py') `
    --log $runLog --result $formal --expected-manifest-sha256 $manifestHash
if ($LASTEXITCODE -ne 0) { throw 'M237R1 acceptance repair gate failed' }
if ($null -ne $boardError) { throw $boardError }
'M237R1_ACCEPTANCE_REPAIR_BOARD_UART_PASS'
