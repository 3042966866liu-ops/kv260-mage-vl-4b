param([switch]$Run)
$ErrorActionPreference='Stop'
if(-not $Run){throw 'Explicit export-only repair required'}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPrior=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M357-full-shell-01/RESULT.json'
$taskPriorSha=(Get-FileHash $taskPrior -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
 if(-not [IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskPriorSha)){throw 'Export failure not synchronized'}
}
$taskOriginal=Get-Content $taskPrior -Raw -Encoding UTF8|ConvertFrom-Json
if($taskOriginal.status -ne 'FAIL_FULL_SHELL_GATE' -or $taskOriginal.vivado_rc -ne 1){throw 'Unexpected original failure'}
$taskLog=[IO.File]::ReadAllText((Join-Path $taskRoot 'tmp/m357_shell_console.log'))
$taskError='ERROR: [Common 17-69] Command failed: Unable to get BIT file from implementation run. Please ensure implementation has been run all the way through Bitstream generation. Aborting write_hw_platform..'
$taskErrors=[regex]::Matches($taskLog,'(?m)^ERROR:.*$')
if($taskErrors.Count -ne 1 -or $taskErrors[0].Value.Trim() -ne $taskError -or -not $taskLog.Contains('Bitgen Completed Successfully.')){throw 'Not the isolated XSA export failure'}
$taskOut=Join-Path $taskRoot 'tmp/m357_shell_export_02'
if(Test-Path $taskOut){throw 'Existing export repair; inspect only'}
New-Item -ItemType Directory -Path $taskOut|Out-Null
$taskInputs=@()
foreach($taskFile in @('tmp/m357_shell_01/mage_m120_m89x2_highddr.xpr','tmp/m357_shell_01/out/candidate_routed.dcp','tmp/m357_shell_01/out/m357_t32.bit','tmp/m357_shell_01/mage_m120_m89x2_highddr.gen/sources_1/bd/qwen25_mixed_gs/hw_handoff/qwen25_mixed_gs.hwh')){
 $taskInputs+=@{path=$taskFile;sha256=(Get-FileHash (Join-Path $taskRoot $taskFile) -Algorithm SHA256).Hash.ToLowerInvariant()}
}
[IO.File]::WriteAllText((Join-Path $taskOut 'INPUTS.json'),(@{prior_failure_sha256=$taskPriorSha;files=$taskInputs}|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
if(Test-Path 'T:\'){throw 'T: already in use; preserve existing mapping'}
& subst.exe T: $taskRoot
if($LASTEXITCODE -ne 0){throw 'Mapping failed'}
try{
 & 'D:/AMDDesignTools/2026.1/Vivado/bin/vivado.bat' -mode batch -source 'T:/scripts/optimization/m357_repair_shell_export.tcl' -tclargs 'T:/' 'T:/tmp/m357_shell_export_02' *> (Join-Path $taskOut 'console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskOut 'EXIT.json'),("{`"export_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 foreach($taskRow in $taskInputs){if((Get-FileHash (Join-Path $taskRoot $taskRow.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRow.sha256){throw 'Read-only original artifact changed'}}
 Get-Content (Join-Path $taskOut 'console.log') -Tail 16
 if($taskRc -ne 0){throw 'Export-only repair failed; no synthesis/place/route rerun'}
}finally{
 & subst.exe T: /D
 $taskRemoved=$LASTEXITCODE -eq 0
 [IO.File]::WriteAllText((Join-Path $taskOut 'MAPPING.json'),(@{removed=$taskRemoved;target=$taskRoot;drive='T:'}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
 if(-not $taskRemoved){throw 'Mapping restoration failed'}
}
