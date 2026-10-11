param([ValidateSet('Upload','Run','Collect')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M364-cma-metadata-01'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskRemote='/home/ubuntu/m364_cma_metadata_01'
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
$taskPython='C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskPreparation=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M364-kernel-metadata-preparation-01/RESULT.json'
$taskRecord=Get-Content -LiteralPath $taskPreparation -Raw -Encoding UTF8|ConvertFrom-Json
if($taskRecord.status -ne 'PASS_OFFLINE_READ_ONLY_METADATA_PREPARATION'){throw 'Preparation incomplete'}
$taskDigest=$taskRecord.manifest_sha256
if((Get-FileHash (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Manifest changed'}
$taskManifest=Get-Content (Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($taskRow in $taskManifest.files){if((Get-FileHash (Join-Path $taskPackage $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Payload changed'}}
$taskPrepSHA=(Get-FileHash $taskPreparation -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskPrepSHA)){throw 'Preparation not synchronized'}}
& $taskUart -Command 'sudo -n true' -LogPath "tmp/m364/sudo_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M364_SUDO_RC_'
if($Mode -eq 'Upload'){
 & $taskUart -Command "test ! -e $taskRemote" -LogPath 'tmp/m364/absence.log' -TimeoutSeconds 15 -MarkerPrefix '__M364_ABSENT_RC_'
 foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){
  & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m364/upload_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
 }
 & $taskUart -Command "sudo -n bash -n $taskRemote/run_m364_metadata.sh" -LogPath 'tmp/m364/root_syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M364_SYNTAX_RC_'
 $taskPaths=@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path)
 $taskHashArguments=($taskPaths|ForEach-Object {"$taskRemote/$_"}) -join ' '
 & $taskUart -Command "sudo -n sha256sum $taskHashArguments" -LogPath 'tmp/m364/remote_hashes.log' -TimeoutSeconds 15 -MarkerPrefix '__M364_HASH_RC_'
 & $taskPython -B (Join-Path $PSScriptRoot 'm364_metadata_workflow.py') transfer (Join-Path $taskRoot 'tmp/m364/remote_hashes.log')
 if($LASTEXITCODE -ne 0){throw 'Transfer evidence failed'}
 exit 0
}
if($Mode -eq 'Run'){
 $taskTransfer=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M364-kernel-metadata-transfer-01/RESULT.json'
 $taskTransferSHA=(Get-FileHash $taskTransfer -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskTransferSHA)){throw 'Transfer not synchronized'}}
}
$taskLog=if($Mode -eq 'Run'){'tmp/m364/run.log'}else{'tmp/m364/collect.log'}
if($Mode -eq 'Run' -and(Test-Path (Join-Path $taskRoot $taskLog))){throw 'Original execution exists; Collect only'}
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m364_metadata.sh" -LogPath "tmp/m364/syntax_$Mode.log" -TimeoutSeconds 15 -MarkerPrefix '__M364_SYNTAX_RC_'
$taskFailure=$null
try{& $taskUart -Command "sudo -n env M364_ENABLE_METADATA=1 bash $taskRemote/run_m364_metadata.sh $taskDigest $Mode" -LogPath $taskLog -TimeoutSeconds 120 -MarkerPrefix '__M364_GATE_RC_'}catch{$taskFailure=$_}
& $taskPython -B (Join-Path $PSScriptRoot 'm364_metadata_workflow.py') collect (Join-Path $taskRoot $taskLog)
if($LASTEXITCODE -ne 0){throw 'Collection incomplete; recover original result only'}
if($taskFailure){throw $taskFailure}
