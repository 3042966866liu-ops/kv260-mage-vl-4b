"""Record observed timeout rejection; explicitly preserve XSIM's zero-exit anomaly."""
import json,re
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
stage=root/'tmp/op01_decode_one_timeout'
log=stage/'verilog/xsim.log';tb=stage/'verilog/op01_decode_one_kernel.autotb.v'
text=log.read_text(errors='replace');source=tb.read_text()
for marker in ['OP01_WATCHDOG_ARMED start_cnt=1','OP01_RTL_TIMEOUT_TRIGGERED finish_cnt=0 total=4','Fatal: OP01 bounded timeout expired before ap_done']:
    assert marker in text,marker
assert 'repeat (200) @ (posedge AESL_clock);' in source
assert 'wait (start_cnt > 0);' in source
assert not re.search(r'RTL Simulation\s*:\s*[1-4]\s*/\s*4',text)
assert 'OP01 negative test invalid' not in text
assert re.search(r'Time:\s*4533600\s*ps',text)
prep=json.loads((stage/'PREPARATION.json').read_text())
assert sha256(tb)==prep['modified_tb_sha256']
normal=root/'tmp/op01_decode_one_rtl/hls/sim/report/op01_decode_one_kernel_cosim.rpt'
assert sha256(normal)==prep['normal_report_sha256']
out=base/'gates/G02-decode-one-timeout/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
result=dict(status='PASS_TIMEOUT_REJECTION_WITH_XSIM_EXIT_ANOMALY',build_id='0x4F503131',
    started_transactions=1,completed_transactions=0,budget_cycles_after_start=200,fatal_time_ps=4533600,
    observed_process=dict(session_id=32565,outer_gate_exit=1,simulator_exit=0,
        provenance='Original exec session32565 terminal output: explicit Expected nonzero simulator exit guard triggered; outer rc1. No re-execution.'),
    conclusion='RTL watchdog rejected unfinished transaction; outer gate failed closed. Simulator rc0 alone is not trustworthy.',
    limitations=['Not proof of production watchdog/recovery','Not missing-input timeout coverage','Not board or performance evidence'],
    board_deployed=False,performance_pass=False,
    evidence={str(p.relative_to(root)):sha256(p) for p in [log,tb,stage/'PREPARATION.json',stage/'verilog/run_timeout.cmd',root/'scripts/optimization/run_decode_one_timeout.ps1']})
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    p=base/'STATE.json';s=json.loads(p.read_text());s['results']['decode_one_timeout']=str(out.relative_to(root))
    s['next_action']='Normal RTL and bounded-timeout rejection recorded; XSIM fatal rc0 preserved. Add tail/W2/maxgroups RTL coverage before full-shell implementation; stable board unchanged.';write_json(p,s)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';s=json.loads(p.read_text(encoding='utf-8-sig'))
    s['latest_decode_one_timeout']=dict(status=result['status'],result=str(out.relative_to(root)),sha256=sha256(out),board_deployed=False);write_json(p,s)
print(result['status'])
