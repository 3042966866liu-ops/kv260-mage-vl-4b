"""Collect original completed HLS bytes without launching tools."""
import json
import re
import xml.etree.ElementTree as ET
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, encoded, sha, sync

observation = BASE/'runs/M443-pair-pipeline-hls-observation-02'
exit_path = observation/'EXIT.json'
exit_record = json.loads(exit_path.read_bytes())
assert exit_record['original_rc'] == 0, exit_record
prep_path = BASE/'runs/M443-pair-pipeline-preparation-01/RESULT.json'
prep = json.loads(prep_path.read_bytes())
assert all(sha(ROOT/r['path']) == r['sha256'] for r in prep['files'])
project = ROOT/'tmp/m443_hls_project_01/hls'
csim = project/'csim/report/m89x_runtime_kernel_csim.log'
csim_text = csim.read_text(encoding='utf-8-sig')
assert len(re.findall(r'^M128_CHAIN_PASS ordinal=',csim_text,re.M)) == 7
assert 'M128_OUTPUT_WORDS=16384' in csim_text
assert 'M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS' in csim_text
assert 'CSim done with 0 errors.' in csim_text
report = project/'syn/report'
mac_paths = sorted(report.glob('m443_compute*Pipeline_VITIS_LOOP_112_7_csynth.xml'))
assert len(mac_paths) == 4
macs = []
for path in mac_paths:
    root = ET.parse(path).getroot()
    loop = root.find('./PerformanceEstimates/SummaryOfLoopLatency/VITIS_LOOP_112_7')
    assert int(loop.findtext('TripCount')) == 64
    assert int(loop.findtext('PipelineII')) == 1
    assert int(loop.findtext('PipelineDepth')) == 34
    assert int(root.findtext('./AreaEstimates/Resources/DSP')) == 288
    assert float(root.findtext('./UserAssignments/TargetClockPeriod')) == 4.8
    assert float(root.findtext('./UserAssignments/ClockUncertainty')) == 1.3
    macs.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),trip_count=64,II=1,depth=34,loop_latency=int(loop.findtext('Latency')),function_latency=int(root.findtext('./PerformanceEstimates/SummaryOfOverallLatency/Best-caseLatency')),DSP=288))
top = report/'m89x_runtime_kernel_csynth.xml'
root = ET.parse(top).getroot()
resources = {e.tag:int(e.text) for e in root.find('./AreaEstimates/Resources')}
assert resources['DSP'] == 1184, resources
assert float(root.findtext('./UserAssignments/TargetClockPeriod')) == 4.8
evidence = [exit_path, csim, top, ROOT/'tmp/m443_pair_pipeline_01/hls_console.log']
record = dict(status='PASS_M443_NUMERICAL_CSIM_AND_HLS01', build_id='0x4D343433', preparation_sha256=sha(prep_path),source_sha256=prep['source_sha256'], original_tool_rc=0, actual_CSim_chains=7, actual_CSim_words=16384, mac_loops=macs, resources=resources, extra_MAC_DSP=0, same_target_clock_ns=4.8, same_uncertainty_ns=1.3, full_real_CSim=False, bounded_RTL=False, routed_shell=False, board=False, performance=False, controller01_failure_preserved=True, next_step='Complete real Q/gate_up/down CSim and bounded RTL; no shell/board before these pass',evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in evidence])
out = BASE/'runs/M443-pair-pipeline-hls-collection-01/RESULT.json'
atomic(out,encoded(record),immutable=True)
sync('latest_m443_pair_pipeline_hls',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),build_id=record['build_id'],board=False),f'## M443原HLS/七数值CSim裁决（2026-10-10）\n\nSHA {sha(out)}；原工具rc0，七链16384字PASS。四实际64-work loop II1/depth34、每lane288DSP、总1184DSP，MAC未复制；同4.8ns/1.3ns约束。原控制01记录错误保持，观察02只监督原PID552退出，不重复综合。尚未完整真实CSim/有界RTL/布线/上板，不是实板收益。')
print(record['status'],sha(out),resources)
