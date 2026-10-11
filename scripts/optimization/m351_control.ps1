[CmdletBinding()]
param([ValidateSet('SelfTest','Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
    param([scriptblock]$GateAction,[scriptblock]$CollectAction)
    $gateError=$null
    try { & $GateAction } catch { $gateError=$_ }
    & $CollectAction
    if ($gateError) { throw $gateError }
}
if ($Mode -eq 'SelfTest') {
    $script:collected=$false; $caught=$false
    try { Invoke-GateAndCollect { throw 'EXPECTED_GATE_FAIL' } { $script:collected=$true } }
    catch { if ($_.Exception.Message -ne 'EXPECTED_GATE_FAIL') { throw }; $caught=$true }
    if (-not ($caught -and $script:collected)) { throw 'Failure skipped collection' }
    try { Invoke-GateAndCollect {} { throw 'EXPECTED_COLLECT_FAIL' }; throw 'Collector failure ignored' }
    catch { if ($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL') { throw } }
    $tokens=$null;$parseErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw 'Controller parse error' }
    Write-Output 'M351_CONTROL_SELF_TEST_PASS failure-collects collector-failure-stops parser-pass'
    exit 0
}
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$local='deployment/mage_vl4b/optimization_v1/candidates/M351-ps-read-component-01'
$remote='/home/ubuntu/m351_ps_read_component_01'
$package=Join-Path $workspace $local
$manifest=Get-Content -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($Mode -eq 'Collect') {
    & $uart -Command 'sudo -n true' -LogPath 'tmp/m351/sudo_before_recollect_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M351_RECOVER_SUDO_RC_'
    if (-not $?) { throw 'Same-terminal sudo expired; no gate rerun' }
    & $uart -Command "sudo -n /usr/local/share/pynq-venv/bin/python3 -B $remote/m351_export_result.py" -LogPath 'tmp/m351/component_recollect_uart.log' -TimeoutSeconds 60 -MarkerPrefix '__M351_EXPORT_RC_'
    if (-not $?) { throw 'Export failed; no gate rerun' }
    & $python -B (Join-Path $PSScriptRoot 'm351_workflow.py') collect 'tmp/m351/component_recollect_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Evidence recovery failed; repair only' }
    exit 0
}
$prior='087bd3fe93ef78d33e306f4b431937da01266b37a46995cd5a8b557e9719c256'
$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($board.latest_m350_ps_read_ahead_design.sha256 -ne $prior -or $board.latest_m351_ps_component_preparation.manifest_sha256 -ne $digest) { throw 'Prerequisite differs' }
if ((Get-FileHash -LiteralPath (Join-Path $workspace $board.latest_m350_ps_read_ahead_design.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prior) { throw 'Design evidence differs' }
$prepSha=$board.latest_m351_ps_component_preparation.sha256
if ((Get-FileHash -LiteralPath (Join-Path $workspace $board.latest_m351_ps_component_preparation.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prepSha) { throw 'Preparation raw differs' }
foreach ($name in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    $state=Get-Content -LiteralPath (Join-Path $workspace $name) -Raw -Encoding UTF8
    if (-not ($state.Contains($prior) -and $state.Contains($prepSha))) { throw 'Prerequisites not synchronized' }
}
if ($Mode -eq 'Upload') {
    foreach ($name in (@('PACKAGE_MANIFEST.json')+@($manifest.files | ForEach-Object path))) {
        & (Join-Path $workspace 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$local/$name" -RemotePath "$remote/$name" -LogPrefix "tmp/m351/upload_$($name.Replace('.','_'))" -ChunkBytes 1800 -TimeoutSeconds 25
        if (-not $?) { throw "Upload failed: $name" }
    }
    Write-Output 'M351_TRANSFER_PASS'
    exit 0
}
if ($Mode -ne 'Run') { throw 'Explicit mode required' }
if (Test-Path -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/runs/M351-ps-read-board-01/BOARD_RESULT.json')) { throw 'Result exists; collection only' }
if (Test-Path -LiteralPath (Join-Path $workspace 'tmp/m351/component_uart.log')) { throw 'Previous outcome exists/unknown; collection only' }
& $uart -Command "bash -n $remote/run_m351_component.sh" -LogPath 'tmp/m351/runner_syntax_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M351_SYNTAX_RC_'
if (-not $?) { throw 'Syntax failed; no component' }
& $uart -Command 'sudo -n true' -LogPath 'tmp/m351/sudo_before_component_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M351_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no component' }
Invoke-GateAndCollect -GateAction {
    & $uart -Command "bash $remote/run_m351_component.sh $digest --enable-fixture-gate" -LogPath 'tmp/m351/component_uart.log' -TimeoutSeconds 120 -MarkerPrefix '__M351_COMPONENT_RC_'
} -CollectAction {
    & $python -B (Join-Path $PSScriptRoot 'm351_workflow.py') collect 'tmp/m351/component_uart.log'
    if ($LASTEXITCODE -ne 0) { throw 'Collector failed; recover only, no gate rerun' }
}
Write-Output 'M351_COMPONENT_RESULT_SYNCHRONIZED'
