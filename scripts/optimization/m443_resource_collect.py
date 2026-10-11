"""Strict original HLS numerical/schedule/resource admission per revision."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,encoded,sha,sync

revision=sys.argv[1];assert revision in ('02','03')
out=ROOT/('tmp/m443_pair_pipeline_'+revision)
run=BASE/('runs/M443-pair-pipeline-hls-'+revision)
prep=BASE/('runs/M443-pair-pipeline-preparation-'+revision+'/RESULT.json')
p=json.loads(prep.read_bytes());assert all(sha(ROOT/r['path'])==r['sha256'] for r in p['files'])
receipt=run/'EXIT.json';r=json.loads(receipt.read_bytes())
assert not r['process_retained'] and not r['budget_exceeded']
report=ROOT/('tmp/m443_hls_project_'+revision+'/hls/syn/report')
top=report/'m89x_runtime_kernel_csynth.xml';root=ET.parse(top).getroot()
resources={e.tag:int(e.text) for e in root.find('AreaEstimates/Resources')}
capacity={e.tag:int(e.text) for e in root.find('AreaEstimates/AvailableResources')}
csim=report.parent.parent/'csim/report/m89x_runtime_kernel_csim.log';text=csim.read_text(encoding='utf-8-sig')
mac=[]
for path in sorted(report.glob('m443_compute*Pipeline*csynth.xml')):
    x=ET.parse(path).getroot()
    if int(x.findtext('AreaEstimates/Resources/DSP','0'))!=288:continue
    loops=list(x.find('PerformanceEstimates/SummaryOfLoopLatency'))
    assert len(loops)==1
    loop=loops[0]
    mac.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),trip_count=int(loop.findtext('TripCount')),II=int(loop.findtext('PipelineII')),depth=int(loop.findtext('PipelineDepth'))))
trip=32 if revision=='02' else 64
checks=dict(original_rc=r['original_rc']==0,seven_numeric_chains=len(re.findall(r'^M128_CHAIN_PASS ordinal=',text,re.M))==7,all_output_words='M128_OUTPUT_WORDS=16384' in text,numeric_completion='M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS' in text and 'CSim done with 0 errors' in text,same_clock=float(root.findtext('UserAssignments/TargetClockPeriod'))==4.8 and float(root.findtext('UserAssignments/ClockUncertainty'))==1.3,shared_MAC=len(mac)==4 and all(q['trip_count']==trip and q['II']==1 for q in mac),same_DSP=resources['DSP']==1184,resources_fit=all(resources[k]<=capacity[k] for k in resources))
record=dict(status=('PASS_M443_HLS_RESOURCE_AND_MAC_GUARD' if all(checks.values()) else 'FAIL_M443_HLS_RESOURCE_OR_MAC_GUARD')+revision,build_id='0x4D343433',checks=checks,resources=resources,capacity=capacity,actual_MAC_loops=mac,preparation_sha256=sha(prep),source_sha256=p['source_sha256'],full_numeric_CSim=False,bounded_RTL=False,routed_shell=False,board=False,performance=False,evidence=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in (receipt,csim,top,out/'hls_console.log')])
dest=BASE/('runs/M443-pair-pipeline-resource-guard-'+revision+'/RESULT.json')
atomic(dest,encoded(record),immutable=True)
sync('latest_m443_resource_admission'+revision,dict(status=record['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M443实际HLS门禁{revision}（2026-10-10）\n\nSHA {sha(dest)}；{record["status"]}，checks={checks}，resources={resources}。原退出/真实数值/实际MAC/资源独立核对；失败保留且只调本级，不启动RTL/整壳或上板。')
print(record['status'],sha(dest),checks)
raise SystemExit(0 if all(checks.values()) else 1)
