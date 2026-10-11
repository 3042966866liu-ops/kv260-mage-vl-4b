param([switch]$Run)
$ErrorActionPreference='Stop'
if(-not $Run){throw 'Explicit readback Run required'}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskOut=Join-Path $taskRoot 'tmp/m357_checkpoint_readback_01'
if(Test-Path $taskOut){throw 'Existing readback attempt; inspect only'}
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskInputs=@()
foreach($taskIp in @('qwen25_mixed_gs_reset_sync_0','qwen25_mixed_gs_sc_s2mm_0')){
  $taskDirectory=Join-Path $taskRoot "tmp/m357_shell_01/mage_m120_m89x2_highddr.runs/${taskIp}_synth_1"
  $taskLog=Join-Path $taskDirectory 'runme.log'
  $taskText=Get-Content -LiteralPath $taskLog -Encoding UTF8 -Raw
  $taskRows=[regex]::Matches($taskText,'(?m)^ERROR:.*$')
  if($taskRows.Count -ne 1 -or $taskRows[0].Value.Trim() -ne "ERROR: [Common 17-354] Could not open 'C' for writing."){throw 'Different tool error; no startup-only classification'}
  if($taskText.IndexOf($taskRows[0].Value) -gt $taskText.IndexOf("source ${taskIp}.tcl -notrace")){throw 'Error after design script; no startup-only classification'}
  if(-not $taskText.Contains('Synthesis finished with 0 errors, 0 critical warnings')){throw 'Design synthesis not clean'}
  $taskDcp=Join-Path $taskDirectory "$taskIp.dcp"
  $taskInputs+=@{ip=$taskIp;checkpoint_sha256=(Get-FileHash $taskDcp -Algorithm SHA256).Hash.ToLowerInvariant();original_log_sha256=(Get-FileHash $taskLog -Algorithm SHA256).Hash.ToLowerInvariant()}
}
[IO.File]::WriteAllText((Join-Path $taskOut 'INPUTS.json'),($taskInputs|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Push-Location $taskOut
try{
 & 'D:/AMDDesignTools/2026.1/Vivado/bin/vivado.bat' -mode batch -source (Join-Path $PSScriptRoot 'm357_checkpoint_readback.tcl') -tclargs $taskRoot $taskOut -log readback.log -journal readback.jou *> console.log
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskOut 'EXIT.json'),("{`"vivado_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 Get-Content -LiteralPath console.log -Encoding UTF8 -Tail 12
 if($taskRc -ne 0){throw 'Readback failed; do not ignore original errors'}
}finally{Pop-Location}
