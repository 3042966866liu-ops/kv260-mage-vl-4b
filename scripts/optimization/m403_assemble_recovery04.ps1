[CmdletBinding()]
param([ValidateSet('SelfTest','Assemble')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($Mode -eq 'SelfTest') {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw 'Recovery syntax rejected' }
    Write-Output 'M403_ASSEMBLY_ONLY_SELF_TEST_PASS';exit 0
}
if ($Mode -ne 'Assemble') { throw 'Explicit mode required' }
$workspace=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -X utf8 -B (Join-Path $PSScriptRoot 'm403_resume04.py') Check
if ($LASTEXITCODE -ne 0) { throw 'Saved receipt/source rejection; no board command' }
$uart=Join-Path $workspace 'scripts/m75c_uart_command.ps1'
$remote='/home/ubuntu/m403_tail_performance_candidate_01'
$package=Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M403-tail-performance-01'
$digest=(Get-FileHash -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()
foreach ($n in @('sudo_assembly_precheck_03.log','assembly02_uart.log','root_syntax02_uart.log')) {
    if (Test-Path (Join-Path $workspace "tmp/m403/$n")) { throw 'Recovery log exists; no overwrite or repeated action' }
}
& $uart -Command 'sudo -n true' -LogPath 'tmp/m403/sudo_assembly_precheck_03.log' -TimeoutSeconds 15 -MarkerPrefix '__M403_RESUME_SUDO_RC_'
if (-not $?) { throw 'Sudo expired; no assembly' }
& $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/m403_assemble.py $digest" -LogPath 'tmp/m403/assembly02_uart.log' -TimeoutSeconds 30 -MarkerPrefix '__M403_ASSEMBLY_RC_'
if (-not $?) { throw 'Assembly rejected; no gate' }
& $uart -Command "sudo -n bash -n $remote/run_m403_light_video.sh" -LogPath 'tmp/m403/root_syntax02_uart.log' -TimeoutSeconds 15 -MarkerPrefix '__M403_SYNTAX_RC_'
if (-not $?) { throw 'Runner syntax rejected; no gate' }
& $python -X utf8 -B (Join-Path $PSScriptRoot 'm403_workflow04.py') transfer
if ($LASTEXITCODE -ne 0) { throw 'Transfer synchronization rejected; no gate' }
Write-Output 'M403_ASSEMBLY_ONLY_SYNCHRONIZED'
