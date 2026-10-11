"""Bounded offline simulator progress probe; never touches board or DUT source."""
import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
import m351_workflow as w

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--extended',action='store_true');args=ap.parse_args()
attempt='02' if args.extended else '01'
OUT=ROOT/('tmp/m357_progress_diagnostic_'+attempt)
budget=180 if args.extended else 90
if not args.run:raise RuntimeError('Explicit offline diagnostic required')
if OUT.exists():raise RuntimeError('Existing diagnostic; inspect only')
prior=BASE/'runs/M357-debug-guard-compile-01/RESULT.json'
assert w.sha(prior)=='4126e1cfa20629168615e5bdde38b84fc826a9b724dc7bfcff318c9708e7daee'
source=ROOT/'tmp/m357_guarded_max_03'
prep=json.loads((BASE/'runs/M357-debug-guard-preparation-01/RESULT.json').read_text(encoding='utf-8'))
for row in prep['files']:assert w.sha(ROOT/row['path'])==row['sha256']
OUT.mkdir();(OUT/'verilog').mkdir();(OUT/'tv/rtldatafile').mkdir(parents=True)
for row in prep['files']:
    src=ROOT/row['path'];rel=src.relative_to(source)
    dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
shutil.copytree(source/'verilog/xsim.dir',OUT/'verilog/xsim.dir')
tcl='''set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
add_force $ready 0
add_force $ar 0
run 48us
puts "M357_PROGRESS phase=held time=[current_time] cycle=[get_value -radix unsigned /m357_trace_monitor/cyc]"
remove_forces $ar
for {set step 1} {$step <= 20} {incr step} {
  run 4800ns
  puts "M357_PROGRESS phase=released step=$step time=[current_time] cycle=[get_value -radix unsigned /m357_trace_monitor/cyc] output=[get_value -radix unsigned /m357_trace_monitor/outwords]"
}
puts "M357_PROGRESS_DIAGNOSTIC_COMPLETE"
quit
'''
(OUT/'verilog/progress.tcl').write_text(tcl,encoding='utf-8')
if args.extended:
    earlier=BASE/'runs/M357-progress-diagnostic-01/RESULT.json'
    previous=json.loads(earlier.read_text(encoding='utf-8'))
    assert previous['status']=='BOUNDED_PROGRESS_DIAGNOSTIC_COMPLETE' and not previous['wall_timeout']
    tcl=tcl.replace('$step <= 20','$step <= 100')
    tcl=tcl.replace('output=[get_value -radix unsigned /m357_trace_monitor/outwords]','output=[get_value -radix unsigned /m357_trace_monitor/outwords] fifo0=[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/AESL_inst_m89x_runtime_kernel/grp_m89x_four_fu_404/result_num_data_valid]')
    (OUT/'verilog/progress.tcl').write_text(tcl,encoding='utf-8')
params='''-testplusarg UVM_VERBOSITY=UVM_NONE
-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib
-testplusarg UVM_TIMEOUT=20000000000000
-testplusarg M357_ZERO_EXTRA_LATENCY
-sv_seed 357
--noieeewarnings
-tclbatch progress.tcl
-log progress.log
'''
(OUT/'verilog/progress.args').write_text(params,encoding='utf-8')
manifest=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()]
w.atomic(OUT/'INPUT_MANIFEST.json',w.encoded(dict(files=manifest,diagnostic_only=True)))
started=time.monotonic();timed_out=False
with (OUT/'verilog/console.log').open('wb') as log:
    proc=subprocess.Popen(['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m357_guarded_debug','-f','progress.args'],cwd=OUT/'verilog',stdout=log,stderr=subprocess.STDOUT)
    print('M357_PROGRESS_DIAGNOSTIC_STARTED wrapper_pid='+str(proc.pid),flush=True)
    try:rc=proc.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        timed_out=True
        # Only this fresh offline simulator process tree; no board process or DMA.
        stopped=subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,text=True)
        if stopped.returncode:raise RuntimeError('Diagnostic software stop failed: '+stopped.stdout+stopped.stderr)
        rc=proc.wait(timeout=10)
logpath=OUT/'verilog/progress.log';text=logpath.read_text(encoding='utf-8-sig',errors='replace') if logpath.exists() else ''
rows=[line for line in text.splitlines() if line.startswith('M357_PROGRESS')]
result=dict(status='BOUNDED_PROGRESS_DIAGNOSTIC_COMPLETE' if not timed_out and 'M357_PROGRESS_DIAGNOSTIC_COMPLETE' in text else 'UNPROVEN_BOUNDED_PROGRESS_DIAGNOSTIC',
    diagnostic_only=True,board=False,rtl_gate_pass=False,wall_timeout=timed_out,wall_budget_s=budget,elapsed_s=time.monotonic()-started,
    original_wrapper_rc=rc,checkpoints=rows,input_manifest_sha256=w.sha(OUT/'INPUT_MANIFEST.json'),
    log_sha256=w.sha(logpath) if logpath.exists() else None,original_long_gate_unchanged=True)
ev=BASE/('runs/M357-progress-diagnostic-'+attempt+'/RESULT.json');w.atomic(ev,w.encoded(result),immutable=True)
digest=w.sha(ev);w.sync('M357_progress_diagnostic',dict(status=result['status'],sha256=digest,evidence_path=ev.relative_to(ROOT).as_posix(),build_id='0x4D333537'),
    'M357 同级离线仿真进度诊断 '+result['status']+'；只增加Tcl检查点、冻结电路/输入不变，'+str(budget)+'s墙钟上限，仅定位，不构成RTL PASS或板端证据。证据 '+digest)
print(json.dumps(result),flush=True)
