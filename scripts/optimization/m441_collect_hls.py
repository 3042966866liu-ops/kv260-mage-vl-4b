"""Saved-only collection; no synthesis or simulation invocation."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

OUT=ROOT/'tmp/m441_record_pipeline_02'
PROJECT=ROOT/'tmp/m441_hls_project_02'
BUILD='0x4D343431'


def main():
    mode=sys.argv[1]
    assert mode in ('csim','hls')
    prep=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json'
    p=json.loads(prep.read_bytes())
    for row in p['files']: assert sha(ROOT/row['path'])==row['sha256']
    log=PROJECT/'hls/csim/report/m89x_runtime_kernel_csim.log'
    text=log.read_text(encoding='utf-8-sig')
    cases=re.findall(r'^M128_CHAIN_PASS[^\r\n]+',text,re.M)
    checks=dict(seven_cases=len(cases)==7,full_marker='M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS' in text,
                all_output_words='M128_OUTPUT_WORDS=16384' in text,csim_zero_errors='CSim done with 0 errors' in text,
                headers=p['missing_headers']==[],source_exact=True)
    result=dict(status='PASS_M441_SEVEN_REDUCED_REAL_RECORD_CSIM' if all(checks.values()) else 'FAIL_M441_REDUCED_CSIM',
                build_id=BUILD,checks=checks,cases=cases,preparation_sha256=sha(prep),csim_log_sha256=sha(log),
                output_words=16384,board=False,performance=False,promoted=False,
                full_size_numeric=False,RTL_bounded_queue_proven=False,read_compute_overlap_proven=False,
                scope='Seven existing reduced-row real-record CSim cases. Unbounded CSim streams do not prove FIFO34 backpressure or overlap.',
                next_step='Verify complete-size saved real-weight windows and references; inspect actual synthesis MAC, queue, resources. No RTL or board admission yet.')
    if mode=='hls':
        prev=BASE/'runs/M441-record-pipeline-csim-02/RESULT.json'
        assert json.loads(prev.read_bytes())['status']=='PASS_M441_SEVEN_REDUCED_REAL_RECORD_CSIM'
        rc_path=OUT/'m441_hls_exit.json';rc=json.loads(rc_path.read_bytes())['hls_rc']
        xml=PROJECT/'hls/syn/report/m89x_runtime_kernel_csynth.xml'
        tree=ET.parse(xml).getroot()
        resources={r.tag:int(r.text) for r in tree.find('AreaEstimates/Resources')}
        available={r.tag:int(r.text) for r in tree.find('AreaEstimates/AvailableResources')}
        target=float(tree.findtext('UserAssignments/TargetClockPeriod'))
        uncertainty=float(tree.findtext('UserAssignments/ClockUncertainty'))
        console=OUT/'m441_hls_console.log';s=console.read_text(encoding='utf-8-sig',errors='replace')
        checks.update(hls_rc=rc==0,resources_fit=all(resources[k]<=available[k] for k in resources),same_constraints=target==4.8 and uncertainty==1.3,
                      original_DSP_schedule=resources['DSP']==1184)
        result.update(status='PASS_M441_HLS_RESOURCE_AND_MAC_GUARD' if all(checks.values()) else 'FAIL_M441_HLS_RESOURCE_OR_MAC_GUARD',
                      csim_sha256=sha(prev),resources=resources,capacity=available,target_clock_ns=target,clock_uncertainty_ns=uncertainty,
                      estimated_clock_ns=float(tree.findtext('PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod')),
                      report_sha256=sha(xml),console_sha256=sha(console),hls_rc=rc,implementation_timing=False,
                      burst_messages=[line for line in s.splitlines() if 'burst' in line.lower()],
                      RTL_files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in sorted((PROJECT/'hls/syn/verilog').glob('*.v'))],
                      next_step='Inspect exact MAC II/calls, bounded queue and real full-size numeric before independent RTL; HLS estimate not routed timing.' if all(checks.values()) else 'Stop at synthesis/schedule guard; preserve failure. No RTL, shell or board.')
    ev=BASE/f'runs/M441-record-pipeline-{mode}-02/RESULT.json'
    atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_record_pipeline_'+mode,dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=BUILD,board=False),
         f'## M441 记录供给流水{mode}闭合（2026-10-07）\n\nSHA {sha(ev)}；{result["status"]}。Build {BUILD}，原七组缩小真实记录16384字，C流无界不能证明34字RTL队列或读算重叠；资源/调度如有仅HLS报告，不替代实现时序或实板。M439原FAIL不改，0新板端/模型/提速。下一步 {result["next_step"]}')
    print(result['status'],sha(ev))
    if not all(checks.values()): raise SystemExit(1)


if __name__=='__main__': main()
