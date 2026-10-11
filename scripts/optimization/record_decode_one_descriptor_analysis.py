"""Freeze exact generated RTL used for the descriptor serialization analysis."""
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
rtl=root/'tmp/op01_decode_one_rtl/hls/syn/verilog'
names=['op01_decode_one_kernel.v','op01_decode_one_kernel_m89x_four.v',
       'op01_decode_one_kernel_m89x_merge.v','op01_decode_one_kernel_flow_control_loop_pipe.v']
out=root/'deployment/mage_vl4b/optimization_v1/runs/OP01-descriptor-serialization/result.json'
if out.exists():raise RuntimeError('Immutable analysis already exists')
write_json(out,dict(status='DERIVED_RTL_SERIALIZATION_ANALYSIS',
    interpretation='Top waits for current four.ready AND four.done; four.done is merge.done; merge consumes per-shard production count before completion. No descriptor-level pipeline overlap inferred for this exact RTL.',
    is_formal_proof=False,maximum_rows_times_descriptors_simulated=False,
    occupancy_peaks_measured=False,board_pass=False,
    caveat='Output register slice can retain data; claim applies to four result FIFOs, not complete external processing.',
    evidence={str(p.relative_to(root)):sha256(p) for p in [rtl/n for n in names]},
    report='deployment/mage_vl4b/optimization_v1/reports/DECODE_ONE_FIFO_COVERAGE.md'))
print('DESCRIPTOR_SERIALIZATION_ANALYSIS_RECORDED_NOT_DYNAMIC_PASS')
