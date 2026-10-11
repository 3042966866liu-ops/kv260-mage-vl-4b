$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskDir=Join-Path $taskRoot 'tmp/m357_activation_banks'
$taskTcl=Join-Path $taskDir 'run_m357_core_ooc.tcl'
if(Test-Path $taskTcl){throw 'Existing export run; inspect only'}
$taskProject=(Join-Path $taskRoot 'tmp/m357_hls_project_02').Replace('\','/')
$taskText=@"
open_project {$taskProject}
open_solution hls
export_design -rtl verilog -format ip_catalog -flow impl
exit
"@
[IO.File]::WriteAllText($taskTcl,$taskText,[Text.UTF8Encoding]::new($false))
Push-Location (Join-Path $taskRoot 'tmp')
try {
  & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl $taskTcl --log (Join-Path $taskDir 'm357_core_ooc')
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskDir 'm357_core_ooc_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "Core-only OOC export failed rc=$taskRc"}
} finally {Pop-Location}
