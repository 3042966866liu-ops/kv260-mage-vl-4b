"""Exact generated handoff comparison, allowing only candidate IP metadata."""
import copy
import json
import xml.etree.ElementTree as E
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
old=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/overlay/m120_m89x2_t32.hwh'
new=ROOT/'tmp/m357_shell_01/mage_m120_m89x2_highddr.gen/sources_1/bd/qwen25_mixed_gs/hw_handoff/qwen25_mixed_gs.hwh'
assert w.sha(old)=='9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520'
a,b=[E.parse(p).getroot() for p in (old,new)]
def signature(e):
    return (e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(sorted(signature(x) for x in e)))
x=next(m for m in a.findall('./MODULES/MODULE') if m.get('INSTANCE')=='mage_m120_m89x2_0')
y=next(m for m in b.findall('./MODULES/MODULE') if m.get('INSTANCE')=='mage_m120_m89x2_0')
assert x.get('VLNV')=='tellme.local:hls:m89x_runtime_kernel:1.0'
assert y.get('VLNV')=='xilinx.com:hls:m89x_runtime_kernel:1.0' and y.get('COREREVISION')=='2114811309'
deltas=[]
for key in ('COREREVISION','VLNV'):
    deltas.append(dict(field='kernel.'+key,original=x.get(key),candidate=y.get(key)))
    y.set(key,x.get(key))
px=x.find('./PARAMETERS/PARAMETER[@NAME="II"]');py=y.find('./PARAMETERS/PARAMETER[@NAME="II"]')
deltas.append(dict(field='kernel.PARAMETER.II',original=px.get('VALUE'),candidate=py.get('VALUE')))
py.set('VALUE',px.get('VALUE'))
dx=x.find('DOCUMENTS');dy=y.find('DOCUMENTS')
deltas.append(dict(field='kernel.DOCUMENTS',original=E.tostring(dx).decode(),candidate=E.tostring(dy).decode()))
y.remove(dy);y.append(copy.deepcopy(dx))
b.set('TIMESTAMP',a.get('TIMESTAMP'))
assert signature(a)==signature(b),'Unexpected HWH topology/ABI/clock/address change'
result=dict(status='PASS_MATCHING_HWH_ABI_TOPOLOGY_ONLY',build_id='0x4D333537',
    stable_hwh_sha256=w.sha(old),candidate_hwh_sha256=w.sha(new),candidate_path=new.relative_to(ROOT).as_posix(),
    permitted_metadata_deltas=deltas,comparison='All elements, attributes and non-whitespace text identical after only timestamp and listed kernel metadata normalization; unordered sibling XML serialization normalized. Registers, AXI/AXIS interfaces, PS settings, bus connectivity, clock/ports and address ranges unchanged.',
    module_count=len(a.findall('./MODULES/MODULE')),board=False,whole_shell_timing_pass=False,promoted=False)
ev=BASE/'runs/M357-hwh-abi-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_hwh_abi',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 生成HWH与稳定同SHA HWH全树对照：仅时间戳、候选IP VLNV/revision、II及文档元数据差异；寄存器、接口、PS/时钟、地址、连线全部保持。仅静态ABI/拓扑核对，整机时序仍待完成，未上板。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha)))
