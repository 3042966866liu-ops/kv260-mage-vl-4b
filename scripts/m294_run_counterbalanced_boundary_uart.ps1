[CmdletBinding()]
param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$Attempt = '01',
    [int]$TimeoutSeconds = 9000,
    [string]$BuildResultRelative = 'deployment\mage_vl4b\M294_COUNTERBALANCED_BOUNDARY_BUILD_RESULT.json',
    [string]$AttemptRootName = 'm294_counterbalanced_boundary',
    [string]$FormalResultStem = 'M294_COUNTERBALANCED_BOUNDARY_BOARD_RESULT',
    [string]$RemoteCandidatePrefix = 'm294_counterbalanced_boundary_candidate',
    [switch]$OfflineSelfTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$commandTool = Join-Path $PSScriptRoot 'm75c_uart_command.ps1'
$uploader = Join-Path $PSScriptRoot 'm212_uart_put_file_chunked.ps1'
$buildPath = Join-Path $workspace $BuildResultRelative
$build = Get-Content -Raw -LiteralPath $buildPath | ConvertFrom-Json
if ($build.status -ne 'M294_BUILD_PASS') { throw 'M294_BUILD_NOT_PASS' }
$candidate = (Resolve-Path -LiteralPath (Join-Path $workspace $build.directory)).Path
$archive = (Resolve-Path -LiteralPath (Join-Path $workspace $build.archive)).Path
$manifestPath = Join-Path $candidate 'PACKAGE_MANIFEST.json'
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
$archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
if ($manifestHash -ne $build.manifest_sha256) { throw 'M294_LOCAL_MANIFEST_HASH_MISMATCH' }
if ($archiveHash -ne $build.archive_sha256) { throw 'M294_LOCAL_ARCHIVE_HASH_MISMATCH' }
if ($build.expected_measurement_count -ne 27) { throw 'M294_LOCAL_SCHEDULE_COUNT_MISMATCH' }

function Assert-M294Condition {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}
if ($OfflineSelfTest) {
    $caught = $false
    try {
        Assert-M294Condition -Condition $false -Message 'M294_INTENTIONAL_FAILURE_BRANCH'
    } catch {
        if ($_.Exception.Message -ne 'M294_INTENTIONAL_FAILURE_BRANCH') { throw }
        $caught = $true
    }
    Assert-M294Condition -Condition $caught -Message 'M294_FAILURE_BRANCH_NOT_EXECUTED'
    Write-Output "M294_CONTROLLER_OFFLINE_SELFTEST_PASS manifest=$manifestHash archive=$archiveHash"
    return
}
$m270Hash = '8e768b513664ab1b3a6caaf5dfe00bb39ba1e186ee1d8f27780d2a91e96f18d9'
$m254ManifestHash = '2a3b720441be44eecc18d57e5d78a8a0a3deab1f8897ee1fb5de02a92c8901a9'
$attemptRelative = "tmp\$AttemptRootName\attempt_$Attempt"
$attemptRoot = Join-Path $workspace $attemptRelative
$formal = Join-Path $workspace "deployment\mage_vl4b\${FormalResultStem}_$Attempt.json"
if (Test-Path -LiteralPath $attemptRoot) { throw "M294 attempt already exists: $attemptRoot" }
if (Test-Path -LiteralPath $formal) { throw "M294 result already exists: $formal" }
New-Item -ItemType Directory -Path $attemptRoot | Out-Null

& (Join-Path $PSScriptRoot 'm255_require_uart_shell.ps1') -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPath (Join-Path $attemptRelative 'shell_probe_uart.log')
& $commandTool -Command 'sudo -n true' -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'sudo_uart.log') -TimeoutSeconds 30

$stageLocal = Join-Path $candidate 'm294_stage_archive.py'
$stageRelative = $stageLocal.Substring($workspace.Length + 1)
$archiveRelative = $archive.Substring($workspace.Length + 1)
$remoteStage = '/dev/shm/tellme_m294_stage_archive.py'
$remoteArchive = '/dev/shm/tellme_m294_counterbalanced_boundary_candidate.tar.gz'
$remoteCandidate = "/home/ubuntu/tellme_m120_m89x2_20260901/${RemoteCandidatePrefix}_$Attempt"
& $uploader -LocalPath $stageRelative -RemotePath $remoteStage -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix (Join-Path $attemptRelative 'upload_stage') `
    -ChunkBytes 1800 -TimeoutSeconds 60
& $uploader -LocalPath $archiveRelative -RemotePath $remoteArchive -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial -LogPrefix (Join-Path $attemptRelative 'upload_archive') `
    -ChunkBytes 1800 -TimeoutSeconds 180
& $commandTool -Command "/usr/local/share/pynq-venv/bin/python $remoteStage --archive $remoteArchive --archive-sha256 $archiveHash --destination $remoteCandidate --destination-prefix $RemoteCandidatePrefix --manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'stage_uart.log') -TimeoutSeconds 180
& $commandTool -Command "/usr/local/share/pynq-venv/bin/python $remoteCandidate/m294_verify_package.py --root $remoteCandidate --expected-manifest-sha256 $manifestHash" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'verify_uart.log') -TimeoutSeconds 120
& $commandTool -Command "bash -n $remoteCandidate/run_m294_counterbalanced_boundary_gate.sh" `
    -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath (Join-Path $attemptRelative 'bash_n_uart.log') -TimeoutSeconds 60

$runLog = Join-Path $attemptRoot 'run_uart.log'
$commandError = $null
try {
    & $commandTool -Command "sudo -n bash $remoteCandidate/run_m294_counterbalanced_boundary_gate.sh $manifestHash $m270Hash $m254ManifestHash $Attempt $remoteCandidate" `
        -Port $Port -ExpectedFtdiSerial $ExpectedFtdiSerial `
        -LogPath (Join-Path $attemptRelative 'run_uart.log') -TimeoutSeconds $TimeoutSeconds
} catch { $commandError = $_ }
& $python -B (Join-Path $PSScriptRoot 'm294_collect_counterbalanced_uart.py') `
    --log $runLog --result $formal --package-manifest-sha256 $manifestHash
$collectorRc = $LASTEXITCODE
if ($collectorRc -ne 0) {
    throw "M294 collector recorded failed/incomplete gate rc=$collectorRc; inspect $formal and $runLog"
}
if ($null -ne $commandError) { throw $commandError }
Write-Output "M294_KV260_COUNTERBALANCED_UART_GATE_PASS result=$formal"
