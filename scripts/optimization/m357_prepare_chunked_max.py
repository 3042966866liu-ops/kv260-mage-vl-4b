"""Same-level TB repair: bounded chunked progress and proven FIFO saturation."""
import json
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m357_chunked_max_04'
if OUT.exists():raise RuntimeError('Existing attempt; inspect only')
failure=BASE/'runs/M357-max-fifo-rtl-02/RESULT.json'
if not failure.exists():raise RuntimeError('Close original long attempt before preparing repair')
failed=json.loads(failure.read_text(encoding='utf-8'))
assert failed['status']=='FAIL_MAX_DESCRIPTOR_FIFO_RTL' and failed.get('software_wall_budget_exceeded') is True
prep=BASE/'runs/M357-debug-guard-preparation-01/RESULT.json'
assert w.sha(prep)=='f3fcdbacfc4a946acdb48a73d7c02dc9e20e61d9e600529762fa061b8dff6e28'
old=ROOT/'tmp/m357_guarded_max_03'
OUT.mkdir();(OUT/'verilog').mkdir();(OUT/'tv/rtldatafile').mkdir(parents=True)
for row in json.loads(prep.read_text(encoding='utf-8'))['files']:
    src=ROOT/row['path'];assert w.sha(src)==row['sha256'];dst=OUT/src.relative_to(old)
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
shutil.copytree(old/'verilog/xsim.dir',OUT/'verilog/xsim.dir')
tcl='''set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set core /apatb_m89x_runtime_kernel_top/AESL_inst_m89x_runtime_kernel/grp_m89x_four_fu_404
add_force $ready 0
add_force $ar 0
run 48us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1} {error "Actual pending AXI hold missing"}
puts "M357_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {set i 1} {$i <= 9} {incr i} {
 run 48us
 puts "M357_CHUNK_PROGRESS time=[current_time] cycle=[get_value -radix unsigned /m357_trace_monitor/cyc]"
}
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TVALID] != 1} {error "Actual held valid output missing"}
set full 0
foreach name {result_num_data_valid result_1_num_data_valid result_2_num_data_valid result_3_num_data_valid} {
 set occupancy [get_value -radix unsigned $core/$name]
 puts "M357_FIFO_HOLD_SNAPSHOT name=$name occupancy=$occupancy"
 if {$occupancy > 8192} {error "FIFO capacity overflow"}
 if {$occupancy == 8192} {incr full}
}
if {$full < 1} {error "Maximum legal FIFO occupancy not reached before release"}
puts "M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
for {set i 1} {$i <= 300} {incr i} {
 run 48us
 puts "M357_CHUNK_PROGRESS time=[current_time] cycle=[get_value -radix unsigned /m357_trace_monitor/cyc] words=[get_value -radix unsigned /m357_trace_monitor/outwords] lasts=[get_value -radix unsigned /m357_trace_monitor/lasts]"
 if {[get_value -radix unsigned /m357_trace_monitor/outwords] == 327680 && [get_value -radix unsigned /m357_trace_monitor/lasts] == 1} {break}
}
if {[get_value -radix unsigned /m357_trace_monitor/outwords] != 327680} {error "Maximum bounded simulation cycle budget exceeded"}
run 480ns
quit
'''
(OUT/'verilog/chunked.tcl').write_text(tcl,encoding='utf-8')
args='''-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-testplusarg M357_ZERO_EXTRA_LATENCY
-sv_seed 357
--noieeewarnings
-tclbatch chunked.tcl
-log m357_max_xsim.log
'''
(OUT/'verilog/chunked.args').write_text(args,encoding='utf-8')
result=dict(status='PREPARED_CHUNKED_MAXIMUM_SAME_DUT',build_id='0x4D333537',rejected_raw_sha256=w.sha(failure),
    source_preparation_sha256=w.sha(prep),change='Tcl checks every10000 cycles; output held100000 cycles with actual held-valid and FIFO capacity8192 verified before release; all DUT/VIP/observer/fixture bytes unchanged',
    wall_budget_s=1800,virtual_budget_cycles=3100000,board=False,executed=False,
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()])
ev=BASE/'runs/M357-chunked-max-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);digest=w.sha(ev)
w.sync('M357_chunked_max_preparation',dict(status=result['status'],sha256=digest,evidence_path=ev.relative_to(ROOT).as_posix(),build_id='0x4D333537'),
    'M357 仅在最大FIFO失败级准备有界分段Tcl驱动；不改DUT/VIP/输入，实际FIFO达到8192且输出valid被暂停后才能解除背压，0新增执行。证据 '+digest)
print(json.dumps(dict(status=result['status'],sha256=digest)))
