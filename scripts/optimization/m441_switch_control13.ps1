param([ValidateSet('Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskUART=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskRemote='/home/ubuntu/m441_first_switch_cma_candidate_13'
$taskLog="tmp/m441_cma13/${Mode}.log"
if(Test-Path (Join-Path $taskRoot $taskLog)){throw 'Existing attempt: fresh saved-byte collection only'}
& $taskUART -Command 'sudo -n true' -LogPath "tmp/m441_cma13/${Mode}_sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__M441D_AUTH_RC_'
if($Mode -eq 'Upload'){
 foreach($taskName in @('PACKAGE_MANIFEST.json','m441_cma_trace13.py','m441_switch_entry13.py','m441_switch_export13.py','PROTOCOL.json','run.sh','SOURCE_IDENTITIES.json','SHA256SUMS')){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath ('deployment/mage_vl4b/optimization_v1/candidates/M441-first-switch-CMA-13/'+$taskName) -RemotePath ($taskRemote+'/'+$taskName) -LogPrefix ('tmp/m441_cma13/upload_'+$taskName.Replace('.','_')) -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUART -Command "sudo -n bash -n $taskRemote/run.sh" -LogPath 'tmp/m441_cma13/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441D_SYNTAX_RC_'
 exit 0
}
$taskError=$null
try{& $taskUART -Command "sudo -n bash $taskRemote/run.sh 36c9322edefa49eb54e3dfabc35621409212fa8380de624d36816d4656563609 $Mode" -LogPath $taskLog -TimeoutSeconds 900 -MarkerPrefix '__M441D_GATE_RC_'}catch{$taskError=$_}
& 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'm441_switch_workflow13.py') collect (Join-Path $taskRoot $taskLog)
if($LASTEXITCODE -ne 0){throw 'Collection incomplete: never repeat hardware'}
if($taskError){throw $taskError}
