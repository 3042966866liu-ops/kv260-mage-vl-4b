$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m441_full_numeric_01'
if(Test-Path (Join-Path $taskDir 'm441_full_csim_console.log')){throw 'Existing full numeric run; collect only'}
if(Test-Path (Join-Path $taskRoot 'tmp/m441_full_csim_project_01')){throw 'Existing full numeric project; collect only'}
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_m441_full_csim.tcl') --log (Join-Path $taskDir 'm441_full_csim') *> (Join-Path $taskDir 'm441_full_csim_console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskDir 'm441_full_csim_exit.json'),("{`"csim_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M441 full CSim failed rc=$taskRc"}
 Write-Output 'M441_FULL_CSIM_RETURN rc=0'
} finally {Pop-Location}
