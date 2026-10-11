"""Do not admit a burst candidate that silently changes the original MAC nest."""
import json,xml.etree.ElementTree as ET
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m439_prepare_rtl import mac_bindings
syn=ROOT/'tmp/m439_hls_project_02/hls/syn/verilog'
report=syn.parent/'report';hls=BASE/'runs/M439-record-load-hls-02/RESULT.json'
r=json.loads(hls.read_bytes());assert r['status']=='PASS_M439_HLS_RESOURCE_REPORT'
bindings=mac_bindings(syn);observed=[]
for b in bindings:
    name=b['module'].removeprefix('m89x_runtime_kernel_')
    p=report/(name+'_csynth.xml');root=ET.parse(p).getroot()
    lat=root.findtext('PerformanceEstimates/SummaryOfOverallLatency/Best-caseLatency')
    loops=root.find('PerformanceEstimates/SummaryOfLoopLatency')
    rows=[dict(name=x.tag,trip=x.findtext('TripCount'),II=x.findtext('PipelineII'),latency=x.findtext('IterationLatency')) for x in loops]
    # HLS XML uses explicit tagged reports; also guard the human-readable table.
    text=(report/(name+'_csynth.rpt')).read_text(encoding='utf-8-sig')
    assert lat=='50' and '|          1|          1|    16|' in text,(name,lat,rows)
    assert '_VITIS_LOOP_79_6_' not in name
    observed.append(dict(**b,latency_cycles=int(lat),II=1,token_pairs=16,report_sha256=sha(p)))
ev=BASE/'runs/M439-record-load-schedule-guard-02/RESULT.json'
r=dict(status='PASS_M439_ORIGINAL_MAC_SCHEDULE_RETAINED',build_id='0x4D343339',hls_sha256=sha(hls),observed=observed,
       resources=json.loads(hls.read_bytes())['resources'],scope='Original 4pair calls per record; each16iterations II1 latency50. Resource mapping differs slightly and remains estimated; not bit-identical RTL or implementation timing.',board=False)
atomic(ev,encoded(r),immutable=True)
sync('latest_m439_record_load_schedule_guard',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
     f'## M439 原计算流水结构核对通过（2026-10-07）\n\nSHA {sha(ev)}；独立02四MAC子过程均16次II1、latency50，与原M357一致；资源估计DSP1180/LUT102030/URAM64，非实现结果。连续burst需实际RTL确认，下一步仅M438同W2小片段Random/Zero，原A证据复用不重跑。')
print('M439_SCHEDULE_GUARD_PASS',sha(ev))
