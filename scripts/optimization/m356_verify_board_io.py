"""Verify exact stable HWH bus identity, not merely a historical BD pathname."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
p=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/overlay/m120_m89x2_t32.hwh'
assert w.sha(p)=='9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520'
tree=ET.parse(p)
ports={}
for module in tree.getroot().iter('MODULE'):
    name=module.attrib.get('INSTANCE') or module.attrib.get('FULLNAME')
    for bus in module.findall('./BUSINTERFACES/BUSINTERFACE'):
        ports[(name,bus.attrib['NAME'])]=dict(bus.attrib)
core='mage_m120_m89x2_0';ps='zynq_ultra_ps_e_0'
paths=[]
for shard,expected in [(0,'S_AXI_HPC0_FPD'),(1,'S_AXI_HPC1_FPD')]:
    a=ports[(core,'m_axi_w'+str(shard))];b=ports[(ps,expected)];assert a['BUSNAME']==b['BUSNAME'] and a['DATAWIDTH']==b['DATAWIDTH']=='128'
    paths.append(dict(shard=shard,route=[core+'/m_axi_w'+str(shard),ps+'/'+expected],bus=a['BUSNAME']))
for shard,sc,hp,dma in [(2,'sc_mm2s','S_AXI_HP0_FPD','M_AXI_MM2S'),(3,'sc_s2mm','S_AXI_HP1_FPD','M_AXI_S2MM')]:
    a=ports[(core,'m_axi_w'+str(shard))];b=ports[(sc,'S00_AXI')];c=ports[(sc,'M00_AXI')];d=ports[(ps,hp)]
    assert a['BUSNAME']==b['BUSNAME'] and c['BUSNAME']==d['BUSNAME']
    other=ports[('axi_dma_prefill',dma)];slave=ports[(sc,'S01_AXI')];assert other['BUSNAME']==slave['BUSNAME']
    paths.append(dict(shard=shard,route=[core+'/m_axi_w'+str(shard),sc+'/S00_AXI',sc+'/M00_AXI',ps+'/'+hp],shares_with='axi_dma_prefill/'+dma,buses=[a['BUSNAME'],c['BUSNAME']]))
result=dict(status='PASS_EXACT_STABLE_HWH_WEIGHT_DMA_PATH',build_id='0x4D395832',hwh_sha256=w.sha(p),paths=paths,
    limitation='Connectivity proves possible contention; no measured DDR bandwidth or attribution of device waiting. NO_DELAY independent-port RTL model does not reproduce PS DDR arbitration.')
ev=BASE/'runs/M356-stable-io-path-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M356_stable_io_path',dict(status=result['status'],build_id=result['build_id'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix()),
    'M356 exact稳定HWH同SHA确认w0→HPC0、w1→HPC1、w2+MM2S→HP0、w3+S2MM→HP1；仅连接关系，非DDR带宽/耗时归因。RTL独立NO_DELAY端口只能先验调度；后级须考虑共享带宽及板端交错。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha),ensure_ascii=True))
