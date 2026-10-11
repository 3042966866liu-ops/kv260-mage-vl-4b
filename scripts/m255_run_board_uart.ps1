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
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$shellProbe = Join-Path $PSScriptRoot 'm255_require_uart_shell.ps1'
$build = Get-Content -Raw (Join-Path $workspace 'deployment\mage_vl4b\M255_M254_SESSION_ATTACH_CANDIDATE_RESULT.json') | ConvertFrom-Json
if ($build.status -ne 'PASS') { throw 'M255_BUILD_NOT_PASS' }
$candidate = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$manifestPath = Join-Path $candidate 'PACKAGE_MANIFEST.json'
$appPath = Join-Path $candidate 'static\app.js'
$newManifest = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
$appHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $appPath).Hash.ToLowerInvariant()
if ($newManifest -ne $build.package_manifest_sha256 -or $appHash -ne $build.app_js_sha256) {
    throw 'M255_LOCAL_PAYLOAD_HASH_MISMATCH'
}
$oldManifest = 'b28d3618f03b97dc2e756dbf0dbb056aed83266a0c9a5575dd014344d3f6a4a0'
$verifierPath = Join-Path $workspace 'scripts\m255_verify_and_swap.py'
$runnerPath = Join-Path $workspace 'scripts\run_m255_session_attach_hotfix.sh'
$verifierHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $verifierPath).Hash.ToLowerInvariant()
$runnerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $runnerPath).Hash.ToLowerInvariant()
$attemptRelative = "tmp\m255_session_attach\attempt_$Attempt"
$attemptRoot = Join-Path $workspace $attemptRelative
$formal = Join-Path $workspace "deployment\mage_vl4b\M255_SESSION_ATTACH_BOARD_RESULT_$Attempt.json"
if (Test-Path -LiteralPath $attemptRoot) { throw "M255 attempt already exists: $attemptRoot" }
if (Test-Path -LiteralPath $formal) { throw "M255 result already exists: $formal" }
New-Item -ItemType Directory -Path $attemptRoot | Out-Null

& $shellProbe -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'shell_probe_uart.log')

$control = '/home/ubuntu/tellme_m120_m89x2_20260901/m255_session_attach_control'
$uploads = @(
    @{ Local = $manifestPath; Remote = "$control/PACKAGE_MANIFEST.json"; Name = 'manifest' },
    @{ Local = $appPath; Remote = "$control/app.js"; Name = 'app_js' },
    @{ Local = $verifierPath; Remote = "$control/m255_verify_and_swap.py"; Name = 'verifier' },
    @{ Local = $runnerPath; Remote = "$control/run_m255_session_attach_hotfix.sh"; Name = 'runner' }
)
foreach ($upload in $uploads) {
    $relative = $upload.Local.Substring($workspace.Length + 1)
    & $uploader -LocalPath $relative -RemotePath $upload.Remote -Port $Port `
        -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix (Join-Path $attemptRelative "upload_$($upload.Name)") `
        -ChunkBytes 1800 -TimeoutSeconds 90
}

& $commandTool -Command "bash -n $control/run_m255_session_attach_hotfix.sh" -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath (Join-Path $attemptRelative 'bash_n_uart.log') -TimeoutSeconds 30

$runLog = Join-Path $attemptRoot 'run_uart.log'
$commandError = $null
try {
    & $commandTool -Command "bash $control/run_m255_session_attach_hotfix.sh $oldManifest $newManifest $appHash $verifierHash $runnerHash" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath (Join-Path $attemptRelative 'run_uart.log') -TimeoutSeconds $TimeoutSeconds
} catch {
    $commandError = $_
}

& $python -B (Join-Path $PSScriptRoot 'm255_collect_board_uart.py') --log $runLog --result $formal `
    --new-manifest-sha256 $newManifest --app-js-sha256 $appHash
if ($LASTEXITCODE -ne 0) { throw "M255 collector failed exit=$LASTEXITCODE" }
if ($null -ne $commandError) { throw $commandError }
Write-Output 'M255_KV260_SESSION_ATTACH_WEB_FIX_UART_GATE_PASS'
