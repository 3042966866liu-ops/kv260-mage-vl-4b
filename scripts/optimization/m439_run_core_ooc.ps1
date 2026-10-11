$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m439_record_load_02'
if(Test-Path (Join-Path $taskDir 'core_ooc_console.log')){throw 'Existing core OOC: collect only'}
if(Get-ChildItem (Join-Path $taskRoot 'tmp/m439_hls_project_02/hls/impl') -Recurse -File | Where-Object {$_.Extension -in '.rpt','.xml','.zip','.xpr','.dcp'}){throw 'Existing implementation run artifacts: collect only'}
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_core_ooc.tcl') --log (Join-Path $taskDir 'm439_core_ooc') *> (Join-Path $taskDir 'core_ooc_console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskDir 'core_ooc_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M439 core OOC failed rc=$taskRc"}
 Write-Output 'M439_CORE_OOC_RETURN rc=0'
} finally {Pop-Location}
