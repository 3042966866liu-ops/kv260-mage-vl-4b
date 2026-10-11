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
$buildPath = Join-Path $workspace 'deployment\mage_vl4b\M218_DUAL_SOURCE_BOARD_DELTA_RESULT.json'
$build = Get-Content -LiteralPath $buildPath -Raw | ConvertFrom-Json
$package = (Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M218_BOOTSTRAP_HASH_FAIL' }
if ($manifest.gate -ne 'M218-dual-source-service-board-delta') { throw 'M218_MANIFEST_IDENTITY_FAIL' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m218_dual_source_delta'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'

& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m218_dual_source\sudo_${Attempt}.log" -TimeoutSeconds 30

# PACKAGE_MANIFEST.json is the first trust root. Every command remains below the
# proven UART canonical-line bound through the M212 chunked uploader.
$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $localAbsolute = (Resolve-Path -LiteralPath (Join-Path $package $name)).Path
    $localRelative = $localAbsolute.Substring($workspace.Length + 1)
    & $uploader -LocalPath $localRelative -RemotePath "$remote/$name" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPrefix "tmp\m218_dual_source\upload_${Attempt}_$($name.Replace('/','_'))" `
        -TimeoutSeconds 60
}

& $commandTool `
    -Command "python3 $remote/m218_verify_board_delta.py --root $remote --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m218_dual_source\verify_${Attempt}.log" -TimeoutSeconds 180
& $commandTool -Command "bash -n $remote/m218_board_preflight_and_restart.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m218_dual_source\bash_n_${Attempt}.log" -TimeoutSeconds 60

$runLog = "tmp\m218_dual_source\run_${Attempt}.log"
$formal = "deployment\mage_vl4b\M218_DUAL_SOURCE_SERVICE_BOARD_RESULT_${Attempt}.json"
try {
    & $commandTool `
        -Command "sudo -n bash $remote/m218_board_preflight_and_restart.sh $manifestHash" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    Write-Warning $_
}
& $python (Join-Path $PSScriptRoot 'm218_collect_board_result.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) {
    throw "M218 board service gate failed; formal result preserved at $formal"
}
Write-Output 'M218_DUAL_SOURCE_UART_PASS'
