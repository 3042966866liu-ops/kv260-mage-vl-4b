[CmdletBinding()]
param([switch]$ValidateOnly, [ValidateSet('01','02','03')][string]$Attempt = '03')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pwsh = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$packageRel = "deployment\mage_vl4b\optimization_v1\candidates\OP00-stable-probe-$Attempt"
$remote = "/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/OP00-stable-probe-$Attempt"
$logRoot = "tmp/op00_stable_probe$Attempt"
$manifestPath = Join-Path $workspace "$packageRel\PACKAGE_MANIFEST.json"
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedHashes = @{'01'='4c3666c8afa87200ffbc301c6b25ecce74ddfd5d7cc1e4d1298f458cf3fc362e'; '02'='e9570309f79e494a6367733639c4e41557b87c075ad7ff5a86c5ff329ca62bed'}
$expectedHashes['03'] = '24edbec4231ff5c96fb564406ad05ef6bb430610a431975a9b54e06f628ec4c8'
if ($manifestHash -ne $expectedHashes[$Attempt]) { throw 'Package drift' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($item in $manifest.files) {
    $payload = Join-Path $workspace "$packageRel\$($item.path)"
    if ((Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Payload drift: $($item.path)" }
}
if ($ValidateOnly) {
    try { throw 'EXPECTED_FAILURE_BRANCH' } catch {
        if ($_.Exception.Message -ne 'EXPECTED_FAILURE_BRANCH') { throw }
    }
    Write-Output 'OP00_CONTROLLER_VALIDATE_AND_FAILURE_BRANCH_PASS'
    exit 0
}
$lockPath = Join-Path $workspace 'deployment\mage_vl4b\optimization_v1\control.lock'
$lockStream = [IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m255_require_uart_shell.ps1') -LogPath "$logRoot/shell.log"
    if ($LASTEXITCODE -ne 0) { throw 'Authenticated UART shell required' }
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m75c_uart_command.ps1') -Command 'sudo -n true' -LogPath "$logRoot/sudo.log"
    if ($LASTEXITCODE -ne 0) { throw 'Same-UART authorization expired; no upload' }
    foreach ($name in @('PACKAGE_MANIFEST.json') + @($manifest.files.path)) {
        & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m212_uart_put_file_chunked.ps1') -LocalPath "$packageRel\$name" -RemotePath "$remote/$name" -LogPrefix "$logRoot/upload_$name"
        if ($LASTEXITCODE -ne 0) { throw "Upload failed: $name" }
    }
    $command = "sudo -n bash $remote/run_op00_stable_probe.sh $manifestHash /home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/stable_probe$Attempt.json"
    & $pwsh -NoProfile -File (Join-Path $workspace 'scripts\m75c_uart_command.ps1') -Command $command -LogPath "$logRoot/run.log" -TimeoutSeconds 120 -MarkerPrefix '__OP00_PROBE_RC_'
    $gateCode = $LASTEXITCODE
    Write-Output "OP00_PROBE_RAW_LAUNCH_EXIT=$gateCode"
    exit $gateCode
} finally {
    $lockStream.Dispose()
    Remove-Item -LiteralPath $lockPath
}
