"""Prepare max-FIFO and timeout observers; extra latency switch is TB-only."""
import json
import re
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
Q=ROOT/'tmp/m357_candidate_q_trace/verilog'
OUT=ROOT/'tmp/m357_guarded_max_02/verilog'
def main():
    if OUT.parent.exists():raise RuntimeError('Existing guarded testbench; inspect only')
    OUT.mkdir(parents=True)
    fixture=ROOT/'tmp/m357_maxfifo_trace'
    shutil.copytree(fixture/'tv',OUT.parent/'tv')
    shutil.copyfile(fixture/'golden.bin',OUT.parent/'golden.bin')
    shutil.copyfile(fixture/'verilog/m357_max_run.tcl',OUT/'m357_max_run.tcl')
    for p in Q.rglob('*'):
        rel=p.relative_to(Q)
        if not p.is_file() or any(a.startswith('xsim') for a in rel.parts):continue
        if p.suffix not in ('.v','.sv','.svh','.vh','.vhd','.mem'):continue
        dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    env=OUT/'m89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv'
    original=env.read_text(encoding='utf-8')
    text,count=re.subn(r'(virtual function int get_\w+\(\);)\s*(int delay;)',r'\1\n            \2\n            if ($test$plusargs("M357_ZERO_EXTRA_LATENCY")) return 0;',original)
    # Four weight ports + control: five channel latency getters each; TX/RX two.
    assert count==27,count
    env.write_text(text,encoding='utf-8')
    shutil.copyfile(ROOT/'scripts/optimization/m357_rtl_watchdog.sv',OUT/'m357_rtl_watchdog.sv')
    prj=(Q/'m357.prj').read_text(encoding='utf-8')+'\nsv xil_defaultlib "m357_rtl_watchdog.sv"\n'
    (OUT/'m357_guarded.prj').write_text(prj,encoding='utf-8')
    result=dict(status='PREPARED_GUARDED_CANDIDATE_RTL_FIXTURE',build_id='0x4D333537',dut_changed=False,
        latency_switch='Only testbench latency getters; optional ZERO_EXTRA_LATENCY. Fixed 600000-cycle shared AXIS hold remains in max FIFO Tcl.',
        timeout='Optional watchdog starts on actual kernel ap_start, 200 cycles, checks actual ap_done then fatal on noncompletion',
        extra_metrics='Output held-valid cycles, AXI pending requests/read waits, AR/R stalls; potential stalls, not pure compute or critical-path attribution',
        latency_getters=count,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()],
        rejected_attempt='First TB compile inserted statement before local variable declaration; no simulation. Preserve original, correct TB-only insertion in new directory.',
        compile_failure_log_sha256=w.sha(ROOT/'tmp/m357_maxfifo_trace/verilog/m357_guarded_xelab.log'),
        executed=False,pending='Full 0:q RTL adjudication before max fixture execution')
    ev=BASE/'runs/M357-guarded-rtl-preparation-02/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True)
    print(json.dumps(dict(status=result['status'],sha256=w.sha(ev)),ensure_ascii=True))
if __name__=='__main__':main()
