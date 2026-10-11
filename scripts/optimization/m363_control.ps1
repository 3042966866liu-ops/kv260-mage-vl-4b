[CmdletBinding()]
param([ValidateSet('Upload','Run','Collect','SelfTest')][string]$Mode,[ValidateSet('A1','B1','B2','A2')][string]$Case)
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
 if($taskError){Write-Host ('Original gate failure preserved: '+$taskError.Exception.Message)}
}
if($Mode -eq 'SelfTest'){
 $script:taskCollected=$false
 Invoke-GateAndCollect {throw 'EXPECTED_GATE_FAIL'} {$script:taskCollected=$true}
 if(-not $script:taskCollected){throw 'Failure skipped collection'}
 & $taskPython -B (Join-Path $PSScriptRoot 'm363_collect_load_comparison.py') --selftest
 if($LASTEXITCODE -ne 0){throw 'Collector tests failed'}
 'M363_CONTROL_SELFTEST_PASS';exit 0
}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M363-common-load-observer-01'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSupport=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M363-load-comparison-support-01/RESULT.json'
$taskValidated=Get-Content -LiteralPath $taskSupport -Raw -Encoding UTF8|ConvertFrom-Json
if($taskValidated.status -ne 'PASS_OFFLINE_COMMON_LOAD_SUPPORT'){throw 'Offline support not passed'}
$taskDigest=$taskValidated.manifest_sha256
$taskRemote='/home/ubuntu/m363_common_load_observer_01'
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Frozen package changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskSupportSHA=(Get-FileHash $taskSupport -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskSupportSHA)){throw 'Support not synchronized'}}
if($Mode -ne 'Upload' -and -not $Case){throw 'Case required'}
if($Mode -eq 'Run'){
 if($Case -notin @('A1','B1')){throw 'Only bounded A1/B1 correction cases authorized in this package'}
 $taskTransfer=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M363-transfer-01/RESULT.json'
 $taskTransferRecord=Get-Content -LiteralPath $taskTransfer -Raw -Encoding UTF8|ConvertFrom-Json
 if($taskTransferRecord.status -ne 'PASS_M363_PACKAGE_TRANSFER_ONLY' -or $taskTransferRecord.manifest_sha256 -ne $taskDigest){throw 'Transfer not verified'}
 $taskTransferSHA=(Get-FileHash $taskTransfer -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskTransferSHA)){throw 'Transfer not synchronized'}}
 $taskCases=@('A1','B1','B2','A2');$taskIndex=[Array]::IndexOf($taskCases,$Case)
 for($taskPriorIndex=0;$taskPriorIndex -lt $taskIndex;$taskPriorIndex++){
  $taskPriorCase=$taskCases[$taskPriorIndex]
  $taskPriorPath=Join-Path $taskRoot "deployment/mage_vl4b/optimization_v1/runs/M363-load-$taskPriorCase-board-01/BOARD_RESULT.json"
  $taskPrior=Get-Content -LiteralPath $taskPriorPath -Raw -Encoding UTF8|ConvertFrom-Json
  if(-not $taskPrior.diagnostic_completed -or $taskPrior.status -notin @('PASS_COMPLETE_RUNTIME_CAPACITY','FAIL_COMPLETE_RUNTIME_CAPACITY') -or $taskPrior.unsafe_buffers_retained){throw 'Prior diagnostic incomplete'}
  $taskPriorSHA=(Get-FileHash $taskPriorPath -Algorithm SHA256).Hash.ToLowerInvariant()
  foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskPriorSHA)){throw 'Prior not synchronized'}}
 }
}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m363_board/sudo_$Mode$Case.log" -TimeoutSeconds 15 -MarkerPrefix '__M363_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m363_board/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M363_ABSENT_RC_'
 $taskOldManifest=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/candidates/M362-common-load-observer-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $taskOldHashes=@($taskOldManifest.files|ForEach-Object sha256)
 $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskOldHashes}|ForEach-Object path)
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m363_board/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
  & $taskUart -Command 'sudo -n true' -LogPath "tmp/m363_board/upload_sudo_$($taskName.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M363_UPLOAD_SUDO_RC_'
 }
 & $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m363_assemble.py $taskDigest" -LogPath 'tmp/m363_board/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M363_ASSEMBLY_RC_'
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m363_load_only.sh" -LogPath 'tmp/m363_board/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M363_SYNTAX_RC_'
 'M363_PACKAGE_UPLOADED_NO_GATE';exit 0
}
$taskLog=if($Mode -eq 'Run'){"tmp/m363_board/run_$Case.log"}else{"tmp/m363_board/recollect_$Case.log"}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original attempt exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m363_load_only.sh" -LogPath "tmp/m363_board/syntax_$Mode$Case.log" -TimeoutSeconds 15 -MarkerPrefix '__M363_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M363_ENABLE_LOAD_ONLY=1 bash $taskRemote/run_m363_load_only.sh $taskDigest $Mode $Case" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M363_GATE_RC_'
} {
 & $taskPython -B (Join-Path $PSScriptRoot 'm363_collect_load_comparison.py') (Join-Path $taskRoot $taskLog) $Case
 if($LASTEXITCODE -ne 0){throw 'Collect saved raw only; no reexecution'}
}
