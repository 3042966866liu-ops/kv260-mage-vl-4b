$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskDir=Join-Path $taskRoot 'tmp/m357_activation_banks'
$taskTcl=Join-Path $taskDir 'run_m357_csim_synth_02.tcl'
if(Test-Path $taskTcl){throw 'Existing repaired runner; inspect only'}
$taskText=[IO.File]::ReadAllText((Join-Path $taskDir 'run_m357_csim_synth.tcl'))
$taskText=$taskText.Replace('tmp/m357_hls_project}','tmp/m357_hls_project_02}').Replace('cd $root','cd [file dirname $root]')
[IO.File]::WriteAllText($taskTcl,$taskText,[Text.UTF8Encoding]::new($false))
Push-Location (Join-Path $taskRoot 'tmp')
try {
  & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl $taskTcl --log (Join-Path $taskDir 'm357_hls_02')
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskDir 'm357_exit_02.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "HLS failed rc=$taskRc"}
} finally {Pop-Location}
