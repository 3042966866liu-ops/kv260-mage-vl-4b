param([ValidateSet('SelfTest','Bootstrap','Receive','TransferCollect','Component','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-ThenCollect {
 param([scriptblock]$Gate,[scriptblock]$Collect)
 $taskError=$null
 try {& $Gate} catch {$taskError=$_}
 & $Collect
 if($taskError){throw $taskError}
}
if($Mode -eq 'SelfTest'){
 $script:taskCollected=$false
 try {Invoke-ThenCollect {throw 'EXPECTED_FAILURE'} {$script:taskCollected=$true}}catch{if($_.Exception.Message -ne 'EXPECTED_FAILURE'){throw}}
 if(-not $script:taskCollected){throw 'Failure skipped collection'}
 $taskTokens=$null;$taskErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
 if($taskErrors.Count){throw 'PowerShell parser error'}
 'M442_COMPONENT_CONTROL_SELFTEST_PASS';exit 0
}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskBase=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1'
$taskPython='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskPrepPath=Join-Path $taskBase 'runs/M442-A53-parser-component-preparation-01/RESULT.json'
function Require-Sync {
 param([string]$Path)
 $taskDigest=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
  if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskDigest)){throw 'Evidence not synchronized'}
 }
}
Require-Sync $taskPrepPath
$taskPrep=Get-Content $taskPrepPath -Raw -Encoding UTF8|ConvertFrom-Json
$taskRemote='/home/ubuntu/m442_a53_component_candidate_01'
$taskRemoteBoot='/home/ubuntu/m442_a53_transfer_bootstrap_01'
$taskBootstrapRelative='deployment/mage_vl4b/optimization_v1/candidates/M442-A53-transfer-bootstrap-01'
$taskBootstrap=Join-Path $taskRoot $taskBootstrapRelative
$taskBootSHA=$taskPrep.bootstrap_manifest_sha256
$taskSHA=$taskPrep.manifest_sha256
if((Get-FileHash (Join-Path $taskBootstrap 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskBootSHA){throw 'Bootstrap manifest changed'}
$taskManifest=Get-Content (Join-Path $taskBootstrap 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskBootstrap $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Bootstrap member changed'}}
if($Mode -eq 'Bootstrap'){
 if(Test-Path (Join-Path $taskRoot 'tmp/m442_board01/bootstrap_absence.log')){throw 'Bootstrap attempt exists: inspect only'}
 & $taskUart -Command 'sudo -n true' -LogPath 'tmp/m442_board01/bootstrap_sudo01.log' -TimeoutSeconds 15 -MarkerPrefix '__M442_BOOT_SUDO_RC_'
 & $taskUart -Command "test ! -e $taskRemoteBoot" -LogPath 'tmp/m442_board01/bootstrap_absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M442_BOOT_ABSENT_RC_'
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskBootstrapRelative/$taskName" -RemotePath "$taskRemoteBoot/$taskName" -LogPrefix "tmp/m442_board01/bootstrap_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n bash -n $taskRemoteBoot/run_m442_transfer.sh" -LogPath 'tmp/m442_board01/bootstrap_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M442_BOOT_SYNTAX_RC_'
 'M442_BOOTSTRAP_UPLOADED_NO_GATE';exit 0
}
if($Mode -in @('Receive','TransferCollect')){
 $taskLog="tmp/m442_board01/${Mode}_transfer_uart.log"
 if(Test-Path (Join-Path $taskRoot $taskLog)){throw 'Original transfer log exists: saved collect only'}
 & $taskUart -Command 'sudo -n true' -LogPath "tmp/m442_board01/${Mode}_transfer_sudo01.log" -TimeoutSeconds 15 -MarkerPrefix '__M442_TRANSFER_SUDO_RC_'
 $taskAction=if($Mode -eq 'Receive'){'receive'}else{'collect'}
 Invoke-ThenCollect {
  & $taskUart -Command "sudo -n bash $taskRemoteBoot/run_m442_transfer.sh $taskAction $taskBootSHA" -LogPath $taskLog -TimeoutSeconds 660 -MarkerPrefix '__M442_TRANSFER_RC_'
 } {
  & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm442_component_workflow01.py') transfer-collect (Join-Path $taskRoot $taskLog)
  if($LASTEXITCODE -ne 0){throw 'Transfer rejected: saved collection only'}
 };exit 0
}
Require-Sync (Join-Path $taskBase 'runs/M442-A53-artifact-transfer-01/BOARD_RESULT.json')
$taskTransfer=Get-Content (Join-Path $taskBase 'runs/M442-A53-artifact-transfer-01/BOARD_RESULT.json') -Raw -Encoding UTF8|ConvertFrom-Json
if($taskTransfer.status -ne 'PASS_M441_ARTIFACT_TRANSFER_ONLY' -or -not $taskTransfer.temporary_address_restored -or $taskTransfer.package_manifest_sha256 -ne $taskSHA){throw 'Exact transfer/restoration prerequisite failed'}
$taskLog="tmp/m442_board01/${Mode}_component_uart.log"
if(Test-Path (Join-Path $taskRoot $taskLog)){throw 'Attempt log exists: saved bytes only'}
if($Mode -eq 'Component' -and(Test-Path (Join-Path $taskBase 'runs/M442-A53-parser-component-board-01/BOARD_RESULT.json'))){throw 'Component result exists: Collect only'}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m442_board01/${Mode}_component_sudo01.log" -TimeoutSeconds 15 -MarkerPrefix '__M442C_SUDO_RC_'
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m442_component.sh" -LogPath "tmp/m442_board01/${Mode}_component_syntax.log" -TimeoutSeconds 15 -MarkerPrefix '__M442C_SYNTAX_RC_'
$taskAction=if($Mode -eq 'Component'){'Run'}else{'Collect'}
Invoke-ThenCollect {
 & $taskUart -Command "sudo -n bash $taskRemote/run_m442_component.sh $taskSHA $taskAction" -LogPath $taskLog -TimeoutSeconds 300 -MarkerPrefix '__M442C_GATE_RC_'
} {
 & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm442_component_workflow01.py') collect (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Component FAIL or saved collection rejected; stop this level'}
}
