param([ValidateSet('Upload','Run','Collect','SelfTest','Identity','IdentityCollect')][string]$Mode)
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
 'M368_CONTROL_SELFTEST_PASS';exit 0
}
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M368-staged-video-03'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskSupport=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M368-video-support-03/RESULT.json'
$taskVerified=Get-Content $taskSupport -Raw -Encoding UTF8|ConvertFrom-Json
if($taskVerified.status -ne 'PASS_OFFLINE_FIXED_VIDEO_SCOPE_BUDGET_AND_SUPPORT'){throw 'Support incomplete'}
$taskDigest=$taskVerified.manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Manifest changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskSupportSHA=(Get-FileHash $taskSupport -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskSupportSHA)){throw 'Support not synchronized'}}
$taskRemote='/home/ubuntu/m368_staged_video_candidate_03'
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m36803/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M368_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m36803/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M368_ABSENT_RC_'
 $taskOld=Get-Content (Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/candidates/M368-staged-video-02/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $taskOldHashes=@($taskOld.files|ForEach-Object sha256)
 $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskOldHashes -and $_.path -notin @('VIDEO_EXPECTED.json','VISUAL_EXPECTED.json')}|ForEach-Object path)
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m36803/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m368_assemble.py $taskDigest" -LogPath 'tmp/m36803/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M368_ASSEMBLY_RC_'
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m368_staged_video.sh" -LogPath 'tmp/m36803/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M368_SYNTAX_RC_'
 & $taskPython -B (Join-Path $PSScriptRoot 'm36803_transfer_receipt.py')
 if($LASTEXITCODE -ne 0){throw 'Transfer evidence failed'}
 exit 0
}
if($Mode -in @('Identity','IdentityCollect')){
 $taskIdentityLog=if($Mode -eq 'Identity'){'tmp/m36803/identity.log'}else{'tmp/m36803/identity_collect.log'}
 if($Mode -eq 'Identity' -and(Test-Path(Join-Path $taskRoot $taskIdentityLog))){throw 'Identity original attempt exists; IdentityCollect only'}
 Invoke-GateAndCollect {
  & $taskUart -Command "sudo -n bash $taskRemote/run_m368_staged_video.sh $taskDigest $Mode B1" -LogPath $taskIdentityLog -TimeoutSeconds 90 -MarkerPrefix '__M368_IDENTITY_RC_'
 } {
  & $taskPython -B (Join-Path $PSScriptRoot 'm368_identity_collect.py') (Join-Path $taskRoot $taskIdentityLog)
  if($LASTEXITCODE -ne 0){throw 'Identity collection incomplete; recover saved bytes only'}
 }
 exit 0
}
$taskIdentitySHA=''
if($Mode -eq 'Run'){
 $taskIdentityPath=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M368-identity-board-01/BOARD_RESULT.json'
 $taskIdentity=Get-Content $taskIdentityPath -Raw -Encoding UTF8|ConvertFrom-Json
 if($taskIdentity.status -ne 'PASS_ACTUAL_LOADER_IDENTITY_SEQUENCE'){throw 'Actual loader identity sequence not PASS'}
 $taskIdentitySHA=(Get-FileHash $taskIdentityPath -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskIdentitySHA)){throw 'Identity evidence not synchronized'}}
}
if($Mode -eq 'Run'){
 $taskTransfer=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M368-video-transfer-02/RESULT.json'
 $taskTransferSHA=(Get-FileHash $taskTransfer -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskTransferSHA)){throw 'Transfer not synchronized'}}
}
$taskLog=if($Mode -eq 'Run'){'tmp/m36803/run.log'}else{'tmp/m36803/collect.log'}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original attempt exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m368_staged_video.sh" -LogPath "tmp/m36803/syntax_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M368_SYNTAX_RC_'
Invoke-GateAndCollect {
 & $taskUart -Command "sudo -n env M368_IDENTITY_PREFLIGHT_SHA=$taskIdentitySHA M368_ENABLE_STAGED_VIDEO=1 bash $taskRemote/run_m368_staged_video.sh $taskDigest $Mode B1" -LogPath $taskLog -TimeoutSeconds 1200 -MarkerPrefix '__M368_GATE_RC_'
} {
 & $taskPython -B (Join-Path $PSScriptRoot 'm36803_collect.py') (Join-Path $taskRoot $taskLog)
 if($LASTEXITCODE -ne 0){throw 'Collection incomplete; recover only saved raw'}
}
