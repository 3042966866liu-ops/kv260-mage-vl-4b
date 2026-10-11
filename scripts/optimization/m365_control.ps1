param([ValidateSet('Upload','Run','Collect','SelfTest')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPython='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
function Invoke-GateAndCollect {
 param([scriptblock]$GateAction,[scriptblock]$CollectAction)
 $taskError=$null
 try { & $GateAction } catch { $taskError=$_ }
 & $CollectAction
 if($taskError){throw $taskError}
}
if($Mode -eq 'SelfTest'){
 $script:taskCollected=$false
 try{Invoke-GateAndCollect {throw 'EXPECTED_GATE_FAILURE'} {$script:taskCollected=$true}}catch{if($_.Exception.Message -ne 'EXPECTED_GATE_FAILURE'){throw}}
 if(-not $script:taskCollected){throw 'Failure skipped collection'}
 'M365_CONTROL_SELFTEST_PASS';exit 0
}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M365-staged-layer-03'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSupport=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M365-staged-layer-support-02/RESULT.json'
$taskVerified=Get-Content $taskSupport -Raw -Encoding UTF8|ConvertFrom-Json
if($taskVerified.status -ne 'PASS_OFFLINE_INDEPENDENT_STAGE_RULES_AND_SUPPORT'){throw 'Support incomplete'}
$taskDigest=$taskVerified.manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Manifest changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskSupportSHA=(Get-FileHash $taskSupport -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskSupportSHA)){throw 'Support not synchronized'}}
$taskRemote='/home/ubuntu/m365_staged_layer_candidate_02'
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m36503/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M365_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m36503/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M365_ABSENT_RC_'
 $taskOld=Get-Content (Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/candidates/M363-common-load-observer-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $taskOldHashes=@($taskOld.files|ForEach-Object sha256)
 $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskOldHashes}|ForEach-Object path)
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m36503/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m365_assemble.py $taskDigest" -LogPath 'tmp/m36503/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M365_ASSEMBLY_RC_'
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m365_staged_layer.sh" -LogPath 'tmp/m36503/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M365_SYNTAX_RC_'
 & $taskPython -B (Join-Path $PSScriptRoot 'm365_transfer_receipt.py')
 if($LASTEXITCODE -ne 0){throw 'Transfer evidence failed'}
 exit 0
}
if($Mode -eq 'Run'){
 $taskTransfer=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M365-staged-layer-transfer-02/RESULT.json'
 $taskTransferSHA=(Get-FileHash $taskTransfer -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskTransferSHA)){throw 'Transfer not synchronized'}}
}
$taskLog=if($Mode -eq 'Run'){'tmp/m365/run.log'}else{'tmp/m365/collect.log'}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original attempt exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m365_staged_layer.sh" -LogPath "tmp/m365/syntax_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M365_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M365_ENABLE_STAGED_LAYER=1 bash $taskRemote/run_m365_staged_layer.sh $taskDigest $Mode B1" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M365_GATE_RC_'
} {
 & $taskPython -B (Join-Path $PSScriptRoot 'm365_collect.py') (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Collection incomplete; recover only saved raw'}
}
