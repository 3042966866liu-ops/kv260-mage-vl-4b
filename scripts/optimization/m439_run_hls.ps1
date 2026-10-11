$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m439_record_load_01'
if(Test-Path (Join-Path $taskDir 'm439_hls_console.log')){throw 'Existing HLS run; collect only'}
if(Test-Path (Join-Path $taskRoot 'tmp/m439_hls_project_01')){throw 'Existing HLS project; collect only'}
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_m439_hls.tcl') --log (Join-Path $taskDir 'm439_hls') *> (Join-Path $taskDir 'm439_hls_console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskDir 'm439_hls_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M439 HLS failed rc=$taskRc"}
 Write-Output 'M439_HLS_RETURN rc=0'
} finally {Pop-Location}
