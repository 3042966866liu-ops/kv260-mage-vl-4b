"""Add deterministic slave address backpressure to the unexecuted maximum FIFO case."""
from pathlib import Path
import json
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
out=ROOT/'tmp/m357_max_axi_control_01.tcl'
if out.exists():raise RuntimeError('Existing AXI hold preparation; inspect only')
tcl='''set ready_path /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set arready_path /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
add_force $ready_path 0
add_force $arready_path 0
run 48us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0} {error "Shared AXI ARREADY hold not effective"}
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1} {error "No real pending AXI address under hold"}
puts "M357_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $arready_path
run 2832us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0} {error "Shared VIP output backpressure not effective"}
puts "M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=600000"
remove_forces $ready_path
run all
quit
'''
w.atomic(out,tcl.encode('utf-8'),immutable=True)
result=dict(status='PREPARED_DETERMINISTIC_AXI_AND_OUTPUT_BACKPRESSURE',core_changed=False,
    already_compiled_snapshot='m357_guarded',guarded_preparation_sha256='5f84b4ac57b137044d44acc79f5fab0dcde0badcd853b4f0869e38dcfb6ef6ce',
    tcl_path=out.relative_to(ROOT).as_posix(),tcl_sha256=w.sha(out),executed=False,
    scope='Real pending w0 ARVALID against shared slave ARREADY=0 for first10000 cycles; output shared ready=0 for total600000; then full output/beat/FIFO checks',
    rationale='Require observed AXI address backpressure, not merely the random-stall generator setting or a flags-only claim')
ev=BASE/'runs/M357-max-axi-control-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True)
print(json.dumps(dict(status=result['status'],sha256=w.sha(ev),tcl_sha256=w.sha(out))))
