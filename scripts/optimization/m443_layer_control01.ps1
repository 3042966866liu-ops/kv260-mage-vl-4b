param([ValidateSet('Upload','Run','Collect','SelfTest')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Invoke-GateAndCollect {
 param([scriptblock]$Gate,[scriptblock]$Collect)
 $taskError=$null
 try {& $Gate} catch {$taskError=$_}
 & $Collect
 if($taskError){throw $taskError}
}
if($Mode -eq 'SelfTest'){
 $script:taskCollected=$false
 try{Invoke-GateAndCollect {throw 'EXPECTED_FAILURE'} {$script:taskCollected=$true}}catch{if($_.Exception.Message -ne 'EXPECTED_FAILURE'){throw}}
 if(-not $script:taskCollected){throw 'Failure skipped collector'}
 try{Invoke-GateAndCollect {} {throw 'EXPECTED_COLLECT_FAILURE'};throw 'Collector failure ignored'}catch{if($_.Exception.Message -ne 'EXPECTED_COLLECT_FAILURE'){throw}}
 $taskTokens=$null;$taskErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
 if($taskErrors.Count){throw 'Parser error'}
 'M443L_CONTROL_SELFTEST_PASS';exit 0
}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPython='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskBase=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1'
function Require-Synchronized {
 param([string]$Path)
 $taskHash=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskHash)){throw 'Evidence not synchronized'}}
 return $taskHash
}
$taskSupport=Join-Path $taskBase 'runs/M443-single-layer-support-01/RESULT.json'
[void](Require-Synchronized $taskSupport)
$taskPrep=Get-Content $taskSupport -Raw -Encoding UTF8|ConvertFrom-Json
if($taskPrep.status -ne 'PASS_M443_SINGLE_LAYER_SUPPORT_FIXTURES01'){throw 'Support failed'}
foreach($taskRow in $taskPrep.files){if((Get-FileHash -LiteralPath (Join-Path $taskRoot $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Frozen control/decoder changed'}}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M443-single-layer-01'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSHA=$taskPrep.manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskSHA){throw 'Manifest changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskRemote='/home/ubuntu/m443_single_layer_candidate_01'
$taskLog="tmp/m443_layer01/${Mode}_uart.log"
if((Test-Path (Join-Path $taskRoot $taskLog)) -or ($Mode -eq 'Run' -and (Test-Path (Join-Path $taskBase 'runs/M443-single-layer-board-01/BOARD_RESULT.json')))){throw 'Attempt already exists; saved-byte collection only'}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m443_layer01/${Mode}_sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__M443L_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m443_layer01/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M443L_ABSENT_RC_'
 $taskKnownHashes=@()
 foreach($taskOld in @('candidates/M441-single-layer-09/PACKAGE_MANIFEST.json','candidates/M443-pair-pipeline-01/PACKAGE_MANIFEST.json')){
  $taskOldManifest=Get-Content (Join-Path $taskBase $taskOld) -Raw -Encoding UTF8|ConvertFrom-Json
  $taskKnownHashes+=@($taskOldManifest.files|ForEach-Object sha256)
 }
 foreach($taskPrior in @('runs/M443-buildid-board-01/BOARD_RESULT.json','runs/M443-chain-board-01/BOARD_RESULT.json')){$taskKnownHashes+=Require-Synchronized (Join-Path $taskBase $taskPrior)}
 $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskKnownHashes}|ForEach-Object path)
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m443_layer01/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m443_layer_assemble.py $taskSHA" -LogPath 'tmp/m443_layer01/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M443L_ASSEMBLY_RC_'
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m443_layer.sh" -LogPath 'tmp/m443_layer01/upload_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M443L_SYNTAX_RC_'
 & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm443_layer_support01.py') receipt
 if($LASTEXITCODE -ne 0){throw 'Transfer receipt failed'}
 exit 0
}
if($Mode -eq 'Run'){
 $taskTransfer=Join-Path $taskBase 'runs/M443-single-layer-transfer-01/RESULT.json'
 [void](Require-Synchronized $taskTransfer)
 $taskTransferValue=Get-Content $taskTransfer -Raw -Encoding UTF8|ConvertFrom-Json
 if($taskTransferValue.status -ne 'PASS_M443_SINGLE_LAYER_TRANSFER_ONLY01' -or $taskTransferValue.manifest_sha256 -ne $taskSHA){throw 'Transfer closure failed'}
}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m443_layer.sh" -LogPath "tmp/m443_layer01/${Mode}_syntax.log" -TimeoutSeconds 15 -MarkerPrefix '__M443L_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M443L_ENABLE_STAGED_LAYER=1 bash $taskRemote/run_m443_layer.sh $taskSHA $Mode B1" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M443L_GATE_RC_'
} {
 & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm443_layer_collect01.py') (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Saved-byte collection failed; never repeat hardware'}
}
