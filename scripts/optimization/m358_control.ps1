[CmdletBinding()]
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
 $script:taskCollected=$false;$taskCaught=$false
 try {Invoke-GateAndCollect {throw 'EXPECTED_GATE_FAIL'} {$script:taskCollected=$true}}
 catch {if($_.Exception.Message -ne 'EXPECTED_GATE_FAIL'){throw};$taskCaught=$true}
 if(-not($script:taskCollected -and $taskCaught)){throw 'Failure skipped collection'}
 & $taskPython -B (Join-Path $PSScriptRoot 'm358_collect_capacity.py') --selftest
 if($LASTEXITCODE -ne 0){throw 'Collector tests failed'}
 'M358_CONTROL_SELFTEST_PASS';exit 0
}
$taskPackage=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/candidates/M358-m357-load-only-03'
$taskDigest='9069628e668a98ec0965f0638a85c369ea80587b844075e72e25a710efdd4eb3'
$taskRemote='/home/ubuntu/m358_m357_load_only_03'
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Frozen package changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskPrior='ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskPrior)){throw 'Prior gate not synchronized'}}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m358_board/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M358_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m358_board/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M358_ABSENT_RC_'
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "deployment/mage_vl4b/optimization_v1/candidates/M358-m357-load-only-03/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m358_board/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
  & $taskUart -Command 'sudo -n true' -LogPath "tmp/m358_board/upload_sudo_$($taskName.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M358_UPLOAD_SUDO_RC_'
 }
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m358_load_only.sh" -LogPath 'tmp/m358_board/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M358_SYNTAX_RC_'
 'M358_PACKAGE_UPLOADED_NO_GATE';exit 0
}
$taskLog=if($Mode -eq 'Run'){'tmp/m358_board/run_uart.log'}else{'tmp/m358_board/recollect_uart.log'}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original attempt exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m358_load_only.sh" -LogPath "tmp/m358_board/syntax_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M358_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M358_ENABLE_LOAD_ONLY=1 bash $taskRemote/run_m358_load_only.sh $taskDigest $Mode" -LogPath $taskLog -TimeoutSeconds 660 -MarkerPrefix '__M358_GATE_RC_'
} {
 & $taskPython -B (Join-Path $PSScriptRoot 'm358_collect_capacity.py') (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Collect saved raw only; no reexecution'}
}
