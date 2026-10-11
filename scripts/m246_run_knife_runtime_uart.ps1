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
$build = Get-Content -Raw (Join-Path $workspace 'deployment\mage_vl4b\M246_KNIFE_BINARY_BUILD_RESULT.json') | ConvertFrom-Json
$package = (Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M246 manifest mismatch' }
$root = '/home/ubuntu/tellme_m120_m89x2_20260901'
$remote = "$root/m246_knife_binary_delta"
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$logRoot = Join-Path $workspace "tmp\m246_knife_runtime\attempt_$Attempt"
$runLog = Join-Path $logRoot 'run_uart.log'
$formal = Join-Path $workspace "deployment\mage_vl4b\M246_KNIFE_RUNTIME_BOARD_RESULT_$Attempt.json"
if (Test-Path $logRoot) { throw "M246 attempt exists: $logRoot" }
New-Item -ItemType Directory -Path $logRoot | Out-Null
& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m246_knife_runtime\attempt_$Attempt\sudo_uart.log" -TimeoutSeconds 30
$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $absolute = (Resolve-Path (Join-Path $package $name)).Path
    $relative = $absolute.Substring($workspace.Length + 1)
    $safe = $name.Replace('/', '_')
    & $uploader -LocalPath $relative -RemotePath "$remote/$name" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix "tmp\m246_knife_runtime\attempt_$Attempt\upload_$safe" -ChunkBytes 1800 -TimeoutSeconds 60
}
& $commandTool -Command "bash -n $remote/run_m246_knife_runtime_gate.sh" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m246_knife_runtime\attempt_$Attempt\bash_n_uart.log" -TimeoutSeconds 60
$m243Hash = '80ea2b8e1d142ef4400aa7e545cf62b3c6ae7a5531e4466df06b35758df096c6'
$commandError = $null
try {
    & $commandTool -Command "sudo -n bash $remote/run_m246_knife_runtime_gate.sh $manifestHash $m243Hash $Attempt" -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath "tmp\m246_knife_runtime\attempt_$Attempt\run_uart.log" -TimeoutSeconds $TimeoutSeconds
} catch { $commandError = $_ }
& $python (Join-Path $PSScriptRoot 'm246_collect_board_uart.py') --log $runLog --result $formal
if ($LASTEXITCODE -ne 0) { throw "M246 knife runtime gate failed; UART retained at $runLog" }
if ($null -ne $commandError) { throw $commandError }
'M246_KNIFE_RUNTIME_UART_PASS'
