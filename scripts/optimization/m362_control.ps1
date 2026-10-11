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
 & $taskPython -B (Join-Path $PSScriptRoot 'm362_collect_load_comparison.py') --selftest
 if($LASTEXITCODE -ne 0){throw 'Collector tests failed'}
 'M362_CONTROL_SELFTEST_PASS';exit 0
}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M362-common-load-observer-01'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSupport=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M362-load-comparison-support-01/RESULT.json'
$taskValidated=Get-Content -LiteralPath $taskSupport -Raw -Encoding UTF8|ConvertFrom-Json
if($taskValidated.status -ne 'PASS_OFFLINE_COMMON_LOAD_SUPPORT'){throw 'Offline support not passed'}
$taskDigest=$taskValidated.manifest_sha256
$taskRemote='/home/ubuntu/m362_common_load_observer_01'
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Frozen package changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskSupportSHA=(Get-FileHash $taskSupport -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskSupportSHA)){throw 'Support not synchronized'}}
if($Mode -ne 'Upload' -and -not $Case){throw 'Case required'}
if($Mode -eq 'Run'){
 $taskCases=@('A1','B1','B2','A2');$taskIndex=[Array]::IndexOf($taskCases,$Case)
 for($taskPriorIndex=0;$taskPriorIndex -lt $taskIndex;$taskPriorIndex++){
  $taskPriorCase=$taskCases[$taskPriorIndex]
  $taskPriorPath=Join-Path $taskRoot "deployment/mage_vl4b/optimization_v1/runs/M362-load-$taskPriorCase-board-01/BOARD_RESULT.json"
  $taskPrior=Get-Content -LiteralPath $taskPriorPath -Raw -Encoding UTF8|ConvertFrom-Json
  if(-not $taskPrior.diagnostic_completed -or $taskPrior.status -notin @('PASS_COMPLETE_RUNTIME_CAPACITY','FAIL_COMPLETE_RUNTIME_CAPACITY') -or $taskPrior.unsafe_buffers_retained){throw 'Prior diagnostic incomplete'}
  $taskPriorSHA=(Get-FileHash $taskPriorPath -Algorithm SHA256).Hash.ToLowerInvariant()
  foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskPriorSHA)){throw 'Prior not synchronized'}}
 }
}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m362_board/sudo_$Mode$Case.log" -TimeoutSeconds 15 -MarkerPrefix '__M362_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m362_board/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M362_ABSENT_RC_'
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m362_board/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
  & $taskUart -Command 'sudo -n true' -LogPath "tmp/m362_board/upload_sudo_$($taskName.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M362_UPLOAD_SUDO_RC_'
 }
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m362_load_only.sh" -LogPath 'tmp/m362_board/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M362_SYNTAX_RC_'
 'M362_PACKAGE_UPLOADED_NO_GATE';exit 0
}
$taskLog=if($Mode -eq 'Run'){"tmp/m362_board/run_$Case.log"}else{"tmp/m362_board/recollect_$Case.log"}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original attempt exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m362_load_only.sh" -LogPath "tmp/m362_board/syntax_$Mode$Case.log" -TimeoutSeconds 15 -MarkerPrefix '__M362_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M362_ENABLE_LOAD_ONLY=1 bash $taskRemote/run_m362_load_only.sh $taskDigest $Mode $Case" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M362_GATE_RC_'
} {
 & $taskPython -B (Join-Path $PSScriptRoot 'm362_collect_load_comparison.py') (Join-Path $taskRoot $taskLog) $Case
 if($LASTEXITCODE -ne 0){throw 'Collect saved raw only; no reexecution'}
}
