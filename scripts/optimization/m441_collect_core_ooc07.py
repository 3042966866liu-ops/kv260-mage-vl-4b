"""Saved-only core implementation closure, exact same clock XDC required."""
import json,re,xml.etree.ElementTree as ET
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def main():
    prep=BASE/'runs/M441-record-pipeline-core-OOC-preparation-01/RESULT.json';pr=json.loads(prep.read_bytes())
    out=ROOT/'tmp/m441_record_pipeline_02';impl=ROOT/'tmp/m441_hls_project_02/hls/impl';rc=json.loads((out/'core_ooc_exit.json').read_bytes())['hls_rc']
    xml=impl/'verilog/report/vivado_impl.xml';xdc=impl/'verilog/m89x_runtime_kernel.xdc';timing_file=impl/'verilog/report/m89x_runtime_kernel_timing_routed.rpt';route_file=impl/'verilog/report/m89x_runtime_kernel_status_routed.rpt'
    checks=dict(original_rc=rc==0);resources={};timing={};capacity={};summary=None
    if xml.exists() and timing_file.exists() and route_file.exists() and xdc.exists():
        profile=ET.parse(xml).getroot();timing={x.tag:x.text for x in profile.find('TimingReport')}
        resources={x.tag:int(x.text) for x in profile.find('AreaReport/Resources')};capacity={x.tag:int(x.text) for x in profile.find('AreaReport/AvailableResources')}
        text=timing_file.read_text(encoding='utf-8-sig',errors='replace')
        table=re.search(r'WNS\(ns\)[^\r\n]+\r?\n[^\r\n]+\r?\n([^\r\n]+)',text)
        vals=table[1].split() if table else []
        if len(vals)==12:summary=dict(WNS_ns=float(vals[0]),TNS_ns=float(vals[1]),setup_failing_endpoints=int(vals[2]),WHS_ns=float(vals[4]),THS_ns=float(vals[5]),hold_failing_endpoints=int(vals[6]),WPWS_ns=float(vals[8]),pulse_failing_endpoints=int(vals[10]))
        route=route_file.read_text(encoding='utf-8-sig',errors='replace')
        checks.update(actual_reports=True,same_clock_XDC=sha(xdc)==pr['original_constraint']['sha256'],target_period=timing.get('CP_TARGET')=='4.800',
          XML_timing_met=timing.get('TIMING_MET')=='TRUE',resources_fit=all(resources[k]<=capacity[k] for k in capacity),
          setup_hold_pulse=bool(summary) and summary['WNS_ns']>=0 and summary['WHS_ns']>=0 and summary['WPWS_ns']>=0 and all(summary[k]==0 for k in ('setup_failing_endpoints','hold_failing_endpoints','pulse_failing_endpoints')),
          route_clean=bool(re.search(r'# of nets with routing errors\.+\s*:\s*0\b',route)))
    else:checks['actual_reports']=False
    ok=all(checks.values());status='PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING' if ok else 'CLOSED_M441_CORE_IMPLEMENTATION_FAILURE'
    evidence=[p for p in [out/'core_ooc_exit.json',out/'core_ooc_console.log',xml,xdc,timing_file,route_file,impl/'verilog/report/m89x_runtime_kernel_utilization_routed.rpt',impl/'export.zip'] if p.exists()]
    r=dict(status=status,build_id='0x4D343431',checks=checks,original_rc=rc,preparation_sha256=sha(prep),resources=resources,capacity=capacity,timing=timing,timing_summary=summary,
      original_M357=dict(resources=pr['original_routed_resources'],target_period_ns=4.8,achieved_period_ns=pr['original_achieved_period_ns'],WNS_ns=pr['original_WNS_ns']),
      resource_delta={k:resources[k]-pr['original_routed_resources'].get(k,0) for k in resources},
      core_only=True,full_shell=False,board=False,board_frequency_measured=False,board_speed_proven=False,promotion=False,
      next_step='Independent maximum FIFO/backpressure/timeout already closed; next full shell and original COM3 hardware gate order. Keep frozen bounded-record pipeline; no extra experiment.' if ok else 'Stop current record-load version. Preserve narrow correct-output/cycle evidence, do not relax clock, implement full shell or board test.',
      evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in evidence])
    p=BASE/'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    report='# M441 核心同约束布局布线\n\n'+status+'\n\n原M357目标4.8ns，候选核心要求同一原XDC字节SHA。仅核心，不含完整板级shell，不证明板端频率或请求收益。\n\n'
    report+='| 资源 | 原M357 | M441 | 差值 |\n|---|---:|---:|---:|\n'
    for k,v in resources.items():report+=f'| {k} | {pr["original_routed_resources"].get(k,0)} | {v} | {r["resource_delta"][k]:+d} |\n'
    report+='\n时序报告：`'+json.dumps(timing,ensure_ascii=False)+'`\n\nsetup/hold/pulse汇总：`'+json.dumps(summary)+'`\n\n检查：`'+json.dumps(checks)+'`\n\n下一步：'+r['next_step']+'\n'
    atomic(p.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_record_pipeline_core_OOC',dict(status=status,result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),
      f'## M441 核心同约束实现闭合（2026-10-07）\n\nSHA {sha(p)}；{status}，原rc{rc}；仅核心，原M3574.8ns同XDC核对，资源/setup/hold/pulse/route实证见RESULT与REPORT。非整机shell/板端速度，M437与稳定服务不变。下一步 {r["next_step"]}')
    print('M441_CORE_OOC_CLOSED',sha(p),status);print(json.dumps(dict(checks=checks,resources=resources,timing=timing,timing_summary=summary),indent=2))
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
