"""Collect frozen-source numerical and synthesis evidence without rerunning."""
import sys,json,re,xml.etree.ElementTree as ET
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
OUT=ROOT/'tmp/m439_record_load_01';PROJECT=ROOT/'tmp/m439_hls_project_01'

def store(tag,r):
    p=BASE/f'runs/M439-record-load-{tag}-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m439_record_load_'+tag,dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id='0x4D343339',board=False),
      f'## M439 单条记录连续加载{tag}（2026-10-07）\n\nSHA {sha(p)}；{r["status"]}。隔离Build0x4D343339，原M357/原M437与服务不改，无新PS槽/CMA/下一条预取。数值/资源/时序以本证据实际范围为准，0板端、非新提速或晋级。下一步 {r["next_step"]}')
    print('M439_SYNC',tag,sha(p),r['status']);return p

def main():
    mode=sys.argv[1];assert mode in ('csim','hls')
    prep=BASE/'runs/M439-record-load-preparation-01/RESULT.json';pr=json.loads(prep.read_bytes())
    for f in pr['files']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
    log=PROJECT/'hls/csim/report/m89x_runtime_kernel_csim.log';s=log.read_text(encoding='utf-8-sig')
    cases=re.findall(r'M128_CHAIN_PASS[^\r\n]+',s)
    checks=dict(csim_finish='CSim done with 0 errors' in s,original_numeric_pass='M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS' in s,seven_cases=len(cases)==7,
      original_output_count='M128_OUTPUT_WORDS=16384' in s,original_W2_W4={'2','4'}==set(re.findall(r'bits=(\d+)',s)),headers=pr['missing_headers']==[],source_exact=True)
    ok=all(checks.values())
    if mode=='csim':
        r=dict(status='PASS_M439_REAL_RECORD_NUMERICAL_CSIM' if ok else 'FAIL_M439_NUMERICAL_CSIM',build_id='0x4D343339',checks=checks,cases=cases,output_words=16384 if checks['original_output_count'] else None,
          original_fixture_sha256=pr['fixture_sha256'],preparation_sha256=sha(prep),csim_log_sha256=sha(log),board=False,rtl=False,resources=False,implementation_timing=False,
          scope='Seven original reduced-row real-record CSim cases only; CSim streams unbounded, not maximum RTL FIFO evidence',next_step='仅同约束综合报告；若不生成burst停止本版，否则准备窄W2/W4实际RTL比较。')
        store(mode,r)
        if not ok:raise SystemExit(1)
        return
    csim=BASE/'runs/M439-record-load-csim-01/RESULT.json';assert json.loads(csim.read_bytes())['status']=='PASS_M439_REAL_RECORD_NUMERICAL_CSIM'
    rc=json.loads((OUT/'m439_hls_exit.json').read_bytes())['hls_rc']
    xml=PROJECT/'hls/syn/report/m89x_runtime_kernel_csynth.xml';root=ET.parse(xml).getroot()
    resources={x.tag:int(x.text) for x in root.find('AreaEstimates/Resources')}
    capacity={x.tag:int(x.text) for x in root.find('AreaEstimates/AvailableResources')}
    est=float(root.findtext('PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod'))
    target=float(root.findtext('UserAssignments/TargetClockPeriod'));uncertainty=float(root.findtext('UserAssignments/ClockUncertainty'))
    hlslog=(OUT/'m439_hls_console.log').read_text(encoding='utf-8-sig',errors='replace')
    burst=[line for line in hlslog.splitlines() if 'burst' in line.lower()]
    checks.update(hls_rc=rc==0,resources_fit=all(resources[k]<=capacity[k] for k in resources),same_HLS_constraints=target==4.8 and uncertainty==1.3)
    r=dict(status='PASS_M439_HLS_RESOURCE_REPORT' if all(checks.values()) else 'FAIL_M439_HLS_RESOURCE_OR_SYNTHESIS',build_id='0x4D343339',checks=checks,hls_rc=rc,
      resources=resources,capacity=capacity,estimated_clock_ns=est,target_clock_ns=target,clock_uncertainty_ns=uncertainty,
      burst_messages=burst,burst_proven_in_RTL=False,preparation_sha256=sha(prep),csim_sha256=sha(csim),report_sha256=sha(xml),log_sha256=sha(OUT/'m439_hls_console.log'),
      board=False,implementation_timing=False,performance=False,rtl_inputs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted((PROJECT/'hls/syn/verilog').glob('*.v'))],
      next_step='仅窄W2/W4实际ARLEN/字数/输出/周期对照；HLS估计不代替实现时序。' if all(checks.values()) else '停止扩展，在本综合/资源失败级保存与分析，不上板或全模型。')
    store(mode,r);print(json.dumps({k:r[k] for k in ('resources','capacity','estimated_clock_ns','burst_messages')},ensure_ascii=True))
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
