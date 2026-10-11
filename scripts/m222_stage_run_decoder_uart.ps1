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
$build = Get-Content -LiteralPath (Join-Path $workspace 'deployment\mage_vl4b\M222_ARM64_DECODER_PACKAGE_RESULT.json') -Raw | ConvertFrom-Json
$package = (Resolve-Path (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $package 'PACKAGE_MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.package_manifest_sha256) { throw 'M222_BOOTSTRAP_HASH_FAIL' }
if ($manifest.gate -ne 'M222-ARM64-decoder-microgate-package') { throw 'M222_MANIFEST_IDENTITY_FAIL' }
$remote = '/home/ubuntu/tellme_m120_m89x2_20260901/m222_decoder_microgate'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'

$entries = @([pscustomobject]@{path='PACKAGE_MANIFEST.json'}) + @($manifest.files)
foreach ($entry in $entries) {
    $name = [string]$entry.path
    $localAbsolute = (Resolve-Path -LiteralPath (Join-Path $package $name)).Path
    $localRelative = $localAbsolute.Substring($workspace.Length + 1)
    & $uploader -LocalPath $localRelative -RemotePath "$remote/$name" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPrefix "tmp\m222_decoder\upload_${Attempt}_$($name.Replace('/','_'))" `
        -TimeoutSeconds 60
}

& $commandTool -Command "python3 $remote/m222_verify_board_delta.py --root $remote --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m222_decoder\verify_${Attempt}.log" -TimeoutSeconds 180
& $commandTool -Command "bash -n $remote/m222_run_board_decode_microbench.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath "tmp\m222_decoder\bash_n_${Attempt}.log" -TimeoutSeconds 60

$runLog = "tmp\m222_decoder\run_${Attempt}.log"
$formal = "deployment\mage_vl4b\M222_ARM64_DECODER_BOARD_RESULT_${Attempt}.json"
try {
    & $commandTool -Command "bash $remote/m222_run_board_decode_microbench.sh $manifestHash" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath $runLog -TimeoutSeconds $TimeoutSeconds
} catch {
    Write-Warning $_
}
& $python (Join-Path $PSScriptRoot 'm222_collect_board_result.py') `
    --log (Join-Path $workspace $runLog) --result (Join-Path $workspace $formal)
if ($LASTEXITCODE -ne 0) { throw "M222 ARM64 decoder gate failed; result preserved at $formal" }
Write-Output 'M222_ARM64_DECODER_UART_PASS'
