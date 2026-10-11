$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m443_pair_pipeline_01'
if(Test-Path (Join-Path $taskDir 'hls_console.log')){throw 'Existing attempt: collect only'}
if(Test-Path (Join-Path $taskRoot 'tmp/m443_hls_project_01')){throw 'Existing project: collect only'}
$taskStart=[DateTime]::UtcNow
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_m443_hls.tcl') --log (Join-Path $taskDir 'm443_hls') *> (Join-Path $taskDir 'hls_console.log')
 $taskRc=$LASTEXITCODE
 $taskElapsed=([DateTime]::UtcNow-$taskStart).TotalSeconds
 $taskReceipt=@{original_rc=$taskRc;elapsed_s=$taskElapsed;wall_budget_s=7200;budget_exceeded=($taskElapsed -gt 7200);tool_killed=$false}|ConvertTo-Json
 [IO.File]::WriteAllText((Join-Path $taskDir 'hls_exit.json'),$taskReceipt,[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M443 HLS failed rc=$taskRc; saved evidence only"}
 if($taskElapsed -gt 7200){throw 'M443 wall budget exceeded; no following gate'}
 'M443_HLS_RETURN rc=0'
} finally {Pop-Location}
