"""Strict normal CoSim evidence collector; timeout and implementation stay separate."""
import json,re
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
sim=root/'tmp/op01_decode_one_rtl/hls/sim'
report=sim/'report/op01_decode_one_kernel_cosim.rpt'
log=sim/'verilog/xsim.log'
tb=sim/'verilog/op01_decode_one_kernel.autotb.v'
env=sim/'verilog/op01_decode_one_kernel_subsystem/op01_decode_one_kernel_env.sv'
assert re.search(r'Verilog\s*\|\s*Pass',report.read_text()),'No actual RTL PASS'
logtext=log.read_text(errors='replace')
assert re.search(r'RTL Simulation\s*:\s*4\s*/\s*4',logtext),'Not all four hardware transactions finished'
assert 'parameter AUTOTB_TRANSACTION_NUM = 4;' in tb.read_text()
for cls in ['svr_latency_tx','svr_latency_rx','axi_latency_w0','axi_latency_w1','axi_latency_w2','axi_latency_w3']:
    assert ('class '+cls) in env.read_text()
assert 'delay inside {[0:256]}' in env.read_text()
out=base/'gates/G02-decode-one-rtl/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
result=dict(status='PASS_NORMAL_RTL_COSIM_ONLY',build_id='0x4F503131',board_deployed=False,performance_pass=False,
    transactions=4,modes=['T32','decode_one'],geometries=[dict(groups=1,rows=512,descriptors=1),dict(groups=1,rows=8,descriptors=10)],
    output_words_per_mode=[32768,5120],oracle='nonzero analytic4 in active positions; zero inactive Decode lanes',
    coverage='Generated AXIS tx/rx and four weight AXI latency classes configured for randomized0..256 delays; normal CoSim completion/output comparison',
    limitations=['No maximum-groups RTL execution; max152 numerical CSim separate','No claimed measured maximum FIFO occupancy','timeout negative pending','resource placement/routing and board gates pending'],
    evidence={str(p.relative_to(root)):sha256(p) for p in [report,log,tb,env,root/'hls/mage_decode_op01_one/tb_rtl.cpp',root/'hls/mage_decode_op01_one/decode_one.cpp']})
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    p=base/'STATE.json';s=json.loads(p.read_text());s['results']['decode_one_rtl']=str(out.relative_to(root))
    s['next_action']='Normal RTL CoSim completed; run isolated bounded-timeout negative, audit FIFO/backpressure and ABI, then routed resource/timing gates before board.';write_json(p,s)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';s=json.loads(p.read_text(encoding='utf-8-sig'))
    s['latest_decode_one_rtl']=dict(status=result['status'],result=str(out.relative_to(root)),sha256=sha256(out),board_deployed=False);write_json(p,s)
print(result['status'])
