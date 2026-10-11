param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path(Join-Path $PSScriptRoot '../..')).Path
$taskRelative='deployment/mage_vl4b/optimization_v1/candidates/M368-staged-video-03'
$taskRemote='/home/ubuntu/m368_staged_video_candidate_03'
$taskPackage=Join-Path $taskRoot $taskRelative
$taskDigest='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66'
if((Get-FileHash(Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskDigest){throw 'Manifest changed'}
$taskManifest=Get-Content(Join-Path $taskPackage 'PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
$taskUart=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
& $taskUart -Command 'sudo -n true' -LogPath 'tmp/m36803/sudo_transfer_resume.log' -TimeoutSeconds 15 -MarkerPrefix '__M368_SUDO_RC_'
foreach($taskName in @('VIDEO_EXPECTED.json.zlib','VISUAL_EXPECTED.json.zlib')){
 $taskRow=$taskManifest.files|Where-Object path -eq $taskName
 if((Get-FileHash(Join-Path $taskPackage $taskName) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Reference payload changed'}
 & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath "$taskRelative/$taskName" -RemotePath "$taskRemote/$taskName" -LogPrefix "tmp/m36803/resume_$($taskName.Replace('.','_'))" -ChunkBytes 900 -TimeoutSeconds 25
}
& $taskUart -Command "sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m368_assemble.py $taskDigest" -LogPath 'tmp/m36803/assembly_resume.log' -TimeoutSeconds 30 -MarkerPrefix '__M368_ASSEMBLY_RC_'
& $taskUart -Command "sudo -n bash -n $taskRemote/run_m368_staged_video.sh" -LogPath 'tmp/m36803/root_syntax_resume.log' -TimeoutSeconds 15 -MarkerPrefix '__M368_SYNTAX_RC_'
& 'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B (Join-Path $PSScriptRoot 'm36803_resume_receipt.py')
if($LASTEXITCODE -ne 0){throw 'Resume transfer receipt incomplete'}
