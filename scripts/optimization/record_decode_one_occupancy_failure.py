"""Preserve failed test instrumentation; do not classify as DUT numerical failure."""
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
stage=root/'tmp/op01_decode_one_occupancy'
out=base/'gates/G02-decode-one-occupancy/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
log=stage/'verilog/xsim.log'
if 'receive more data than ref TV' not in log.read_text(errors='replace'):raise RuntimeError('Expected error absent')
paths=[log,stage/'PREPARATION.json',stage/'verilog/op01_decode_one_kernel.autotb.v',
       stage/'verilog/svtb/sv_module_top.sv',stage/'verilog/svr/svr_slave_monitor.sv']
write_json(out,dict(status='FAIL_TESTBENCH_HANDSHAKE_INJECTION',build_id='0x4F503131',
    session=29303,stopped_xsim_pid=17564,
    cause='force on downstream rx_TREADY did not change upstream svr_rx_if.ready observed by UVM monitor; monitor counted repeated held VALID data while DUT blocked.',
    evidence={str(p.relative_to(root)):sha256(p) for p in paths},
    fifo3_full_markers=[0,2],final_peaks_available=False,
    dut_failure_proven=False,board_deployed=False,performance_pass=False,
    next_action='New isolated attempt with a shared ready handshake, validate injection on a short test before long capacity test; preserve current failure and all prior normal PASS evidence.'))
print('FAIL_TESTBENCH_HANDSHAKE_INJECTION_RECORDED')
