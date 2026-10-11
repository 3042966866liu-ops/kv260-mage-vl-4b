$ErrorActionPreference='Stop'
$taskRoot=Resolve-Path (Join-Path $PSScriptRoot '../..')
$taskSim=Join-Path $taskRoot 'tmp/m356_stable_q_trace/verilog'
if(Test-Path (Join-Path $taskSim 'm356_xsim_03.log')){throw 'Existing host check: review only'}
if(Test-Path (Join-Path $taskSim 'm356_trace.csv')){throw 'Simulation started; do not repeat'}
$taskArgs=[IO.File]::ReadAllText((Join-Path $taskSim 'm356_xsim.args')).Replace('m356_xsim_02.log','m356_xsim_03.log')
[IO.File]::WriteAllText((Join-Path $taskSim 'm356_xsim_03.args'),$taskArgs,[Text.UTF8Encoding]::new($false))
Push-Location $taskSim
try {
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat' m356_stable_q -f m356_xsim_03.args
  $taskRc=$LASTEXITCODE
  $taskLog=[IO.File]::ReadAllText((Join-Path $taskSim 'm356_xsim_03.log'))
  $taskStarted=Test-Path (Join-Path $taskSim 'm356_trace.csv')
  $taskEngineError=$taskLog -match 'ERROR:|necessary license|failed to start'
  [IO.File]::WriteAllText((Join-Path $taskSim 'm356_exit_03.json'),("{`"process_rc`":$taskRc,`"engine_error`":"+$taskEngineError.ToString().ToLower()+",`"trace_started`":"+$taskStarted.ToString().ToLower()+"}"),[Text.UTF8Encoding]::new($false))
  if($taskRc -ne 0 -or $taskEngineError -or -not $taskStarted){throw "Simulation not validated rc=$taskRc engine_error=$taskEngineError started=$taskStarted"}
} finally {Pop-Location}
