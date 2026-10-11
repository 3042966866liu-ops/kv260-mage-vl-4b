param([switch]$Run)
$ErrorActionPreference='Stop'
if(-not $Run){throw 'Explicit Run required'}
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskPrep=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M441-shell-preparation-01/RESULT.json'
if(-not(Test-Path $taskPrep)){throw 'Shell prerequisites not closed'}
$taskSpec=Get-Content -LiteralPath $taskPrep -Raw -Encoding UTF8 | ConvertFrom-Json
if($taskSpec.status -ne 'PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES'){throw 'Preparation rejected'}
$taskPrepSha=(Get-FileHash $taskPrep -Algorithm SHA256).Hash.ToLowerInvariant()
foreach($n in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){
  if(-not([IO.File]::ReadAllText((Join-Path $taskRoot $n)).Contains($taskPrepSha))){throw "Preparation not synchronized: $n"}
}
$taskManifest=Join-Path $taskRoot $taskSpec.manifest_path
if((Get-FileHash $taskManifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskSpec.manifest_sha256){throw 'Input manifest changed'}
$taskInputs=Split-Path $taskManifest
$taskManifestSpec=Get-Content $taskManifest -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($row in $taskManifestSpec.files){
  if((Get-FileHash -LiteralPath (Join-Path $taskInputs $row.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256){throw "Input changed: $($row.path)"}
}
foreach($row in $taskSpec.prerequisites){
  if((Get-FileHash -LiteralPath (Join-Path $taskRoot $row.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256){throw 'Gate evidence changed'}
}
$taskProject=Join-Path $taskRoot 'tmp/m441_shell_01'
if(Test-Path $taskProject){throw 'Existing shell attempt; inspect only'}
$taskMappingCreated=$false
if(Test-Path 'T:\'){throw 'T: already exists; do not change existing mapping'}
& subst.exe T: $taskRoot
if($LASTEXITCODE -ne 0){throw 'Temporary short-path mapping failed'}
$taskMappingCreated=$true
try{
  if(-not(Test-Path 'T:\AGENTS.md')){throw 'Mapped workspace identity mismatch'}
  $taskShortSha=(Get-FileHash 'T:\deployment\mage_vl4b\optimization_v1\runs\M441-shell-preparation-01\RESULT.json' -Algorithm SHA256).Hash.ToLowerInvariant()
  if($taskShortSha -ne $taskPrepSha){throw 'Mapped workspace evidence differs'}
  $taskRecord=Join-Path $taskRoot 'tmp/m441_shell_mapping.json'
  [IO.File]::WriteAllText($taskRecord,(@{drive='T:';target=$taskRoot;created=$true;removed=$false}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
  & 'D:/AMDDesignTools/2026.1/Vivado/bin/vivado.bat' -mode batch -source 'T:/scripts/optimization/m441_build_shell.tcl' -tclargs 'T:/' -log 'T:/tmp/m441_shell_vivado.log' -journal 'T:/tmp/m441_shell_vivado.jou' *> 'T:/tmp/m441_shell_console.log'
  $taskRc=$LASTEXITCODE
  [IO.File]::WriteAllText((Join-Path $taskRoot 'tmp/m441_shell_exit.json'),(@{vivado_rc=$taskRc}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
  Get-Content -LiteralPath (Join-Path $taskRoot 'tmp/m441_shell_console.log') -Tail 18
  if($taskRc -ne 0){throw "Shell implementation failed rc=$taskRc; inspect at this level"}
}finally{
  if($taskMappingCreated){
    & subst.exe T: /D
    $taskRemoved=$LASTEXITCODE -eq 0
    [IO.File]::WriteAllText((Join-Path $taskRoot 'tmp/m441_shell_mapping.json'),(@{drive='T:';target=$taskRoot;created=$true;removed=$taskRemoved}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
    if(-not $taskRemoved){throw 'Temporary mapping cleanup failed'}
  }
}
