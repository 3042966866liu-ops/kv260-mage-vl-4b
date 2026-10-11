[CmdletBinding()]
param([ValidateSet('SelfTest','Bootstrap','Receive','TransferCollect','BuildID','Descriptor','Chain','Compare','Collect')][string]$Mode,
 [ValidateSet('BuildID','Descriptor','Chain','Compare')][string]$GateMode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
 param([scriptblock]$GateAction,[scriptblock]$CollectAction)
 $taskError=$null
 try { & $GateAction } catch { $taskError=$_ }
 & $CollectAction
 if($taskError){throw $taskError}
}
if($Mode -eq 'SelfTest'){
 $script:taskCollected=$false;$taskCaught=$false
 try {Invoke-GateAndCollect {throw 'EXPECTED_GATE_FAIL'} {$script:taskCollected=$true}}
 catch {if($_.Exception.Message -ne 'EXPECTED_GATE_FAIL'){throw};$taskCaught=$true}
 if(-not($script:taskCollected -and $taskCaught)){throw 'Failure skipped collection'}
 try {Invoke-GateAndCollect {} {throw 'EXPECTED_COLLECT_FAIL'};throw 'Collector failure ignored'}
 catch {if($_.Exception.Message -ne 'EXPECTED_COLLECT_FAIL'){throw}}
 $taskTokens=$null;$taskErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
 if($taskErrors.Count){throw 'Parser errors'}
 'M441_CONTROL_SELF_TEST_PASS failure-collects collection-failure-stops';exit 0
}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskBase=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1'
$taskPython='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskPrepPath=Join-Path $taskBase 'runs/M441-board-package-preparation-01/RESULT.json'
function Require-Synchronized {
 param([string]$Path)
 $taskDigest=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
  if(-not [IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskDigest)){throw "Evidence not synchronized: $taskName"}
 }
 return $taskDigest
}
[void](Require-Synchronized $taskPrepPath)
$taskPrep=Get-Content -LiteralPath $taskPrepPath -Raw -Encoding UTF8 | ConvertFrom-Json
if($taskPrep.status -ne 'PREPARED_NEW_CIRCUIT_BOARD_PACKAGE_AFTER_ALL_GATES'){throw 'Package prerequisites rejected'}
$taskPackage=Join-Path $taskRoot $taskPrep.package_path
$taskBootstrap=Join-Path $taskRoot $taskPrep.bootstrap_path
$taskDigest=$taskPrep.manifest_sha256
$taskBootDigest=$taskPrep.bootstrap_manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Candidate manifest changed'}
if((Get-FileHash (Join-Path $taskBootstrap 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskBootDigest){throw 'Bootstrap manifest changed'}
$taskRemote='/home/ubuntu/m441_candidate_01'
$taskRemoteBoot='/home/ubuntu/m441_transfer_bootstrap_01'
if($Mode -eq 'Bootstrap'){
 & $taskUart -Command 'sudo -n true' -LogPath 'tmp/m441_board/sudo_bootstrap_renewed02.log' -TimeoutSeconds 15 -MarkerPrefix '__M441_BOOT_SUDO_RC_'
 & $taskUart -Command "test ! -e $taskRemoteBoot" -LogPath 'tmp/m441_board/bootstrap_absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M441_BOOT_ABSENT_RC_'
 $taskManifest=Get-Content (Join-Path $taskBootstrap 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$($taskPrep.bootstrap_path)/$taskName" -RemotePath "$taskRemoteBoot/$taskName" -LogPrefix "tmp/m441_board/bootstrap_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "bash -n $taskRemoteBoot/run_m441_transfer.sh" -LogPath 'tmp/m441_board/bootstrap_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441_BOOT_SYNTAX_RC_'
 'M441_BOOTSTRAP_UPLOADED_ONLY_NO_GATE';exit 0
}
if($Mode -in @('Receive','TransferCollect')){
 $taskLog=if($Mode -eq 'Receive'){'tmp/m441_board/transfer_uart.log'}else{'tmp/m441_board/transfer_recollect_uart.log'}
 if($Mode -eq 'Receive' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original transfer attempt exists; TransferCollect only'}
 & $taskUart -Command 'sudo -n true' -LogPath "tmp/m441_board/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M441_TRANSFER_SUDO_RC_'
 $taskAction=if($Mode -eq 'Receive'){'receive'}else{'collect'}
 Invoke-GateAndCollect {
  & $taskUart -Command "sudo -n bash $taskRemoteBoot/run_m441_transfer.sh $taskAction $taskBootDigest" -LogPath $taskLog -TimeoutSeconds 660 -MarkerPrefix '__M441_TRANSFER_RC_'
 } {
  & $taskPython -B (Join-Path $PSScriptRoot 'm441_transfer_collection.py') (Join-Path $taskRoot $taskLog)
  if($LASTEXITCODE -ne 0){throw 'Transfer collection failed; only recover saved bytes, no retry/import'}
 };exit 0
}
$taskGate=if($Mode -eq 'Collect'){$GateMode}else{$Mode}
if($taskGate -notin @('BuildID','Descriptor','Chain','Compare')){throw 'Explicit gate mode required'}
$taskTransfer=Join-Path $taskBase 'runs/M441-artifact-transfer-01/BOARD_RESULT.json'
[void](Require-Synchronized $taskTransfer)
$taskTransferResult=Get-Content $taskTransfer -Raw -Encoding UTF8|ConvertFrom-Json
if($taskTransferResult.status -ne 'PASS_M441_ARTIFACT_TRANSFER_ONLY' -or -not $taskTransferResult.temporary_address_restored -or $taskTransferResult.package_manifest_sha256 -ne $taskDigest){throw 'Artifact/network closure rejected'}
$taskPriorSha=$null
if($taskGate -ne 'BuildID'){
 $taskPriorMode=@{Descriptor='buildid';Chain='descriptor';Compare='chain'}[$taskGate]
 $taskPrior=Join-Path $taskBase "runs/M441-$taskPriorMode-board-01/BOARD_RESULT.json"
 $taskPriorSha=Require-Synchronized $taskPrior
 $taskPriorValue=Get-Content $taskPrior -Raw -Encoding UTF8|ConvertFrom-Json
 if($taskPriorValue.status -ne "PASS_M441_$($taskPriorMode.ToUpperInvariant())" -or $taskPriorValue.gate_return_code -ne 0){throw 'Lower gate rejected'}
}
$taskLabel=$taskGate.ToLowerInvariant()
$taskLog=if($Mode -eq 'Collect'){"tmp/m441_board/${taskLabel}_recollect_uart.log"}else{"tmp/m441_board/${taskLabel}_uart.log"}
if($Mode -ne 'Collect' -and ((Test-Path (Join-Path $taskRoot $taskLog)) -or(Test-Path (Join-Path $taskBase "runs/M441-$taskLabel-board-01/BOARD_RESULT.json")))){throw 'Existing gate attempt; Collect only'}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m441_board/${taskLabel}_${Mode}_sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__M441_GATE_SUDO_RC_'
& $taskUart -Command "sudo -n bash -n $taskRemote/m441_gate_runner.sh" -LogPath "tmp/m441_board/${taskLabel}_${Mode}_root_syntax.log" -TimeoutSeconds 15 -MarkerPrefix '__M441_SYNTAX_RC_'
$taskAction=if($Mode -eq 'Collect'){'Collect'}else{'Run'}
$taskCommand="sudo -n env M441_ENABLE_GATE=1 bash $taskRemote/m441_gate_runner.sh $taskGate $taskDigest $taskAction"
if($taskPriorSha){$taskCommand+=" $taskPriorSha"}
Invoke-GateAndCollect {
 & $taskUart -Command $taskCommand -LogPath $taskLog -TimeoutSeconds 660 -MarkerPrefix '__M441_GATE_RC_'
} {
 $taskArgs=@('-B',(Join-Path $PSScriptRoot 'm441_board_collection.py'),$taskGate,(Join-Path $taskRoot $taskLog),$taskDigest)
 if($taskPriorSha){$taskArgs+=@('--prior-sha',$taskPriorSha)}
 & $taskPython @taskArgs
 if($LASTEXITCODE -ne 0){throw 'Board collection failed; recover saved original bytes only, never rerun hardware'}
}
'M441_GATE_EVIDENCE_SYNCHRONIZED'
