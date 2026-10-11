"""Whole handoff comparison; normalize only explicitly known kernel metadata."""
import copy,json,xml.etree.ElementTree as E
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
old=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/overlay/m120_m89x2_t32.hwh'
new=ROOT/'tmp/m439_shell_01/mage_m120_m89x2_highddr.gen/sources_1/bd/qwen25_mixed_gs/hw_handoff/qwen25_mixed_gs.hwh'
assert sha(old)=='9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520'
component=ROOT/'tmp/m439_shell_inputs_01/ip/component.xml'
root=E.parse(component).getroot();revision=next(e.text for e in root.iter() if e.tag.endswith('}coreRevision'))
a,b=[E.parse(p).getroot() for p in (old,new)]
def signature(e):
    return(e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(sorted(signature(x) for x in e)))
x=next(m for m in a.findall('./MODULES/MODULE') if m.get('INSTANCE')=='mage_m120_m89x2_0')
y=next(m for m in b.findall('./MODULES/MODULE') if m.get('INSTANCE')=='mage_m120_m89x2_0')
assert x.get('VLNV')=='tellme.local:hls:m89x_runtime_kernel:1.0'
assert y.get('VLNV')=='xilinx.com:hls:m89x_runtime_kernel:1.0' and y.get('COREREVISION')==revision
deltas=[]
for key in ('COREREVISION','VLNV'):
    deltas.append(dict(field='kernel.'+key,original=x.get(key),candidate=y.get(key)));y.set(key,x.get(key))
px=x.find('./PARAMETERS/PARAMETER[@NAME="II"]');py=y.find('./PARAMETERS/PARAMETER[@NAME="II"]')
assert px is not None and py is not None
deltas.append(dict(field='kernel.PARAMETER.II',original=px.get('VALUE'),candidate=py.get('VALUE')));py.set('VALUE',px.get('VALUE'))
dx=x.find('DOCUMENTS');dy=y.find('DOCUMENTS');assert dx is not None and dy is not None
deltas.append(dict(field='kernel.DOCUMENTS',original=E.tostring(dx).decode(),candidate=E.tostring(dy).decode()))
y.remove(dy);y.append(copy.deepcopy(dx));b.set('TIMESTAMP',a.get('TIMESTAMP'))
assert signature(a)==signature(b),'Unexpected handoff topology/register/interface/clock/address difference'
r=dict(status='PASS_M439_MATCHING_HWH_ABI_TOPOLOGY_ONLY',build_id='0x4D343339',stable_hwh_sha256=sha(old),candidate_hwh_sha256=sha(new),
       candidate_path=new.relative_to(ROOT).as_posix(),component_sha256=sha(component),permitted_metadata_deltas=deltas,
       module_count=len(a.findall('./MODULES/MODULE')),comparison='Whole XML after only timestamp and known IP revision/VLNV/II/doc metadata normalization. Registers, interfaces, PS/clock/address/connectivity unchanged.',
       board=False,whole_shell_timing_pass=False,promotion=False)
p=BASE/'runs/M439-hwh-abi-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_hwh_abi',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),
     '## M439 HWH静态ABI闭合（2026-10-07）\n\nSHA '+sha(p)+'；固定稳定HWH全树核对，IP revision来自实际候选component，不猜常量。仅timestamp/VLNV/revision/II/doc元数据标准化，寄存器/接口/PS/时钟/地址/连接全同；非整壳时序/板端PASS。')
print(r['status'],sha(p))
