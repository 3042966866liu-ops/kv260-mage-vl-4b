[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('single-descriptor','single-chain')][string]$Level)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonExe = 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$boardRecord = Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding utf8 | ConvertFrom-Json
$stateText = Get-Content -LiteralPath (Join-Path $workspace 'CURRENT_STATE.md') -Raw -Encoding utf8
$milestoneText = Get-Content -LiteralPath (Join-Path $workspace 'docsMILESTONES.md') -Raw -Encoding utf8
$manifestSha = 'b97d995bfa2f9afecd3e324c1b823731245d5c090fc1bb6de43919fc4db11e96'
$previous = $boardRecord.latest_m341_build_id_board_gate
if ($Level -eq 'single-chain') { $previous = $boardRecord.latest_m342_single_descriptor }
if ($previous.status -ne 'PASS') { throw 'Previous gate has not passed' }
$previousPath = Join-Path $workspace $previous.result
$previousSha = (Get-FileHash -LiteralPath $previousPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($previousSha -ne $previous.sha256 -or -not $stateText.Contains($previousSha) -or -not $milestoneText.Contains($previousSha)) {
    throw 'Previous evidence is not synchronized in all three recovery records; collection repair only'
}
$localEvidence = "deployment/mage_vl4b/optimization_v1/runs/M342-$Level-board-01/BOARD_RESULT.json"
if (Test-Path -LiteralPath (Join-Path $workspace $localEvidence)) { throw 'Immutable result already exists; do not rerun hardware' }
$command = "bash /home/ubuntu/m342_prefetch_fixture_01/run_m342_fixture.sh $Level $manifestSha"
if ($Level -eq 'single-chain') { $command += " $previousSha" }
& (Join-Path $workspace 'scripts/m75c_uart_command.ps1') -Command $command -LogPath "tmp/m342/${Level}_uart.log" -TimeoutSeconds 180
$gateSucceeded = $?
& $pythonExe -B (Join-Path $workspace 'scripts/optimization/m342_collect_fixture_gate.py') $Level
$collectExitCode = $LASTEXITCODE
if ($collectExitCode -ne 0) { throw "Evidence synchronization failed ($collectExitCode); stop, repair collection using existing bytes, never advance or rerun hardware" }
if (-not $gateSucceeded) { throw 'Gate failed; failure evidence synchronized. Remain at this level.' }
Write-Output 'M342_GATE_AND_ALL_RECOVERY_RECORDS_SYNCHRONIZED'
