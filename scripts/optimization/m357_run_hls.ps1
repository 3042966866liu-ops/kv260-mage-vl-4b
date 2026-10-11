$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskDir=Join-Path $taskRoot 'tmp/m357_activation_banks'
if(Test-Path (Join-Path $taskDir 'm357_hls.log')){throw 'Existing HLS run; inspect only'}
Push-Location $taskDir
try {
  & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl run_m357_csim_synth.tcl --log m357_hls.log
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskDir 'm357_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0){throw "HLS failed rc=$taskRc"}
} finally {Pop-Location}
