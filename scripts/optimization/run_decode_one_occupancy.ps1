param([switch]$ResumeSimulation)
$ErrorActionPreference='Stop'
$root='C:\Users\30429\Desktop\TeLLMe_FPGA_2026'
$dest=Join-Path $root 'tmp\op01_decode_one_occupancy_v3'
$m=Get-Content (Join-Path $dest 'PREPARATION.json') -Raw | ConvertFrom-Json
$tb=Join-Path $dest 'verilog\op01_decode_one_kernel.autotb.v'
if((Get-FileHash $tb -Algorithm SHA256).Hash.ToLowerInvariant() -ne $m.tb_sha256){throw 'TB identity mismatch'}
foreach($entry in $m.dut_files.PSObject.Properties){
    $p=Join-Path (Join-Path $dest 'verilog') $entry.Name
    if((Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw "DUT identity mismatch $($entry.Name)"}
}
Push-Location (Join-Path $dest 'verilog')
try {
    if($ResumeSimulation){
        & (Join-Path $root 'scripts\optimization\resume_decode_one_occupancy.cmd')
    } else {
        & .\run_occupancy.cmd
    }
    $rc=$LASTEXITCODE
    if($rc -ne 0){throw "Simulator exit $rc"}
    $log=Get-Content .\xsim.log -Raw
    if($log -match '(?im)^\s*(Fatal:|ERROR:|UVM_ERROR\s+file|UVM_FATAL\s+file)' -or $log -match 'UVM_(ERROR|FATAL)\s*:\s*[1-9]'){throw 'Simulator fatal/error'}
    foreach($pattern in @('OP01_FIFO_FULL tx=0 shard=3 occupancy=8192','OP01_FIFO_FULL tx=2 shard=3 occupancy=8192','OP01_FULL_HOLD_PASS tx=0 cycles=256','OP01_FULL_HOLD_PASS tx=2 cycles=256','OP01_FIFO_OCCUPANCY_PASS','RTL Simulation\s*:\s*4\s*/\s*4')){
        if($log -notmatch $pattern){throw "Missing $pattern"}
    }
    foreach($entry in $m.expected_outputs.PSObject.Properties){
        $p=Join-Path (Join-Path $dest 'tv\rtldatafile') $entry.Name
        if((Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw "Output mismatch $($entry.Name)"}
    }
    Write-Output 'OP01_OCCUPANCY_AND_FROZEN_OUTPUT_PASS'
} finally {Pop-Location}
