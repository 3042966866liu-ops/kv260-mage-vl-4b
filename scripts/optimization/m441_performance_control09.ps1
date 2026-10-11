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
 $taskTokens=$null;$taskErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$taskTokens,[ref]$taskErrors)
 if($taskErrors.Count){throw 'Parser error'}
 'M441P_CONTROL_SELFTEST_PASS';exit 0
}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPython='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskBase=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1'
$taskPrepPath=Join-Path $taskBase 'runs/M441-complete-request-performance-support-09/RESULT.json'
$taskDigest=(Get-FileHash $taskPrepPath -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskDigest)){throw 'Support not synchronized'}}
$taskPrep=Get-Content $taskPrepPath -Raw -Encoding UTF8|ConvertFrom-Json
if($taskPrep.status -ne 'PASS_M441_PERFORMANCE_SUPPORT09'){throw 'Support failed'}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M441-complete-request-performance-09'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSHA=$taskPrep.manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskSHA){throw 'Manifest changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskRemote='/home/ubuntu/m441_complete_request_candidate_09'
$taskLog="tmp/m441_performance09/${Mode}_uart.log"
if((Test-Path (Join-Path $taskRoot $taskLog)) -or ($Mode -eq 'Run' -and (Test-Path (Join-Path $taskBase 'runs/M441-complete-request-performance-board-09/BOARD_RESULT.json')))){throw 'Attempt already exists; saved-byte collection only'}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m441_performance09/${Mode}_sudo.log" -TimeoutSeconds 15 -MarkerPrefix '__M441P_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m441_performance09/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M441P_ABSENT_RC_'
 $taskOld=Get-Content (Join-Path $taskBase 'candidates/M363-common-load-observer-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $taskOldText=Get-Content (Join-Path $taskBase 'candidates/M437-late11-natural-IO-performance-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $taskOldHashes=@($taskOld.files|ForEach-Object sha256)+@($taskOldText.files|ForEach-Object sha256)+@('0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d','0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7','defbb0fd59e9139e1f6c267a78aa066d25a19708c1e4a075032415b7b3ae95e8')
 $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskOldHashes}|ForEach-Object path)
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m441_performance09/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m441_performance_assemble.py $taskSHA" -LogPath 'tmp/m441_performance09/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M441P_ASSEMBLY_RC_'
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m441_performance.sh" -LogPath 'tmp/m441_performance09/upload_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441P_SYNTAX_RC_'
 & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm441_performance_support09.py') receipt
 if($LASTEXITCODE -ne 0){throw 'Transfer receipt failed'}
 exit 0
}
if($Mode -eq 'Run'){
 $taskTransfer=Join-Path $taskBase 'runs/M441-complete-request-performance-transfer-09/RESULT.json'
 $taskTransferSHA=(Get-FileHash $taskTransfer -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskTransferSHA)){throw 'Transfer not synchronized'}}
}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m441_performance.sh" -LogPath "tmp/m441_performance09/${Mode}_syntax.log" -TimeoutSeconds 15 -MarkerPrefix '__M441P_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M441P_ENABLE_INTEGRATED_VIDEO=1 bash $taskRemote/run_m441_performance.sh $taskSHA $Mode" -LogPath $taskLog -TimeoutSeconds 5100 -MarkerPrefix '__M441P_GATE_RC_'
} {
 & $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'm441_performance_collect09.py') (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Saved-byte collection failed; never repeat hardware'}
}
