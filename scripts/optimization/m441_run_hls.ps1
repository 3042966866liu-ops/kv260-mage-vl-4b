$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m441_record_pipeline_01'
if(Test-Path (Join-Path $taskDir 'm441_hls_console.log')){throw 'Existing M441 run; collect only'}
if(Test-Path (Join-Path $taskRoot 'tmp/m441_hls_project_01')){throw 'Existing M441 project; collect only'}
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_m441_hls.tcl') --log (Join-Path $taskDir 'm441_hls') *> (Join-Path $taskDir 'm441_hls_console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskDir 'm441_hls_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M441 HLS failed rc=$taskRc"}
 Write-Output 'M441_HLS_RETURN rc=0'
} finally {Pop-Location}
