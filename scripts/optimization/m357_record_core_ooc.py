"""Close the isolated core implementation check; no board-shell claim."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import m351_workflow as w

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
impl = ROOT / 'tmp/m357_hls_project_02/hls/impl'
receipt = ROOT / 'tmp/m357_activation_banks/m357_core_ooc_exit.json'
assert json.loads(receipt.read_text(encoding='utf-8'))['hls_rc'] == 0
xml_path = impl / 'verilog/report/vivado_impl.xml'
profile = ET.parse(xml_path).getroot()
timing = {e.tag: e.text for e in profile.find('TimingReport')}
resources = {e.tag: int(e.text) for e in profile.find('AreaReport/Resources')}
available = {e.tag: int(e.text) for e in profile.find('AreaReport/AvailableResources')}
assert timing['TIMING_MET'] == 'TRUE' and timing['CP_TARGET'] == '4.800'
assert float(timing['WNS_FINAL']) > 0
assert all(resources[k] <= v for k, v in available.items())
log = ROOT / 'tmp/m357_activation_banks/m357_core_ooc/hls_run_tcl.log'
text = log.read_text(encoding='utf-8-sig', errors='replace')
assert 'impl run complete:' in text and 'number of unrouted nets=0' in text.lower(), 'Route completion not proven'
assert '0.058912' in text and '0.055000' in text
paths = [receipt, xml_path, log, impl/'report/verilog/m89x_runtime_kernel_export.rpt',
         impl/'verilog/report/m89x_runtime_kernel_timing_routed.rpt',
         impl/'verilog/report/m89x_runtime_kernel_utilization_routed.rpt',
         impl/'verilog/report/m89x_runtime_kernel_status_routed.rpt', impl/'export.zip']
result = dict(status='PASS_ISOLATED_CORE_ROUTED_TIMING', build_id='0x4D333537',
    scope='Core OOC only; excludes complete board shell and board execution',
    resources=resources, available=available, target_period_ns=4.8,
    achieved_period_ns=float(timing['CP_FINAL']), wns_ns=0.058912,
    whs_ns=0.055, unrouted_nets=0, board=False, promoted=False,
    limitations=['URAM 64/64; DSP 1184/1248',
        'Small setup margin; complete board shell must be routed independently',
        'No measured bandwidth, power or speedup evidence'],
    evidence=[dict(path=p.relative_to(ROOT).as_posix(), sha256=w.sha(p)) for p in paths],
    pending='Complete frozen Q RTL, maximum descriptor/FIFO/backpressure and timeout checks before full-shell construction')
ev = BASE/'runs/M357-core-ooc-01/RESULT.json'
w.atomic(ev, w.encoded(result), immutable=True)
sha = w.sha(ev)
w.sync('M357_core_ooc', dict(status=result['status'], sha256=sha,
    evidence_path=ev.relative_to(ROOT).as_posix(), build_id=result['build_id']),
    'M357 独立核心OOC布局布线PASS：4.8ns目标，实际4.741ns，WNS +0.058912ns、WHS +0.055000ns、unrouted=0；LUT40327/FF49325/DSP1184/BRAM18K156/URAM64。只证明核心，URAM已用满，整机shell与新RTL完整门禁尚未通过；0候选板端事务、未提速或晋级。证据 '+sha)
print(json.dumps(dict(status=result['status'], sha256=sha)))
