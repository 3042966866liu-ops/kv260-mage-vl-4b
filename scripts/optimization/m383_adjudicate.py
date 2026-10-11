"""Adjudicate one saved descriptor numerical pair; no hardware calls."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    path=BASE/'runs/M383-ps-descriptor-board-01/BOARD_RESULT.json';board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m383_ps_descriptor_board'];assert prior['sha256']==sha(path)
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(path.read_text(encoding='utf-8'));passed=r['status']=='PASS_M383_PS_DESCRIPTOR_NUMERICAL';p=r.get('ps_session',{});c=p.get('component',{});checks=p.get('independent_memory_checks',[])
    observed={}
    if checks:
        observed=dict(min_CmaFree_MiB=min(x['memory']['system_bytes']['CmaFree'] for x in checks)/(1<<20),min_MemAvailable_MiB=min(x['memory']['system_bytes']['MemAvailable'] for x in checks)/(1<<20),max_observed_RSS_growth_MiB=max(x['decision']['observed_rss_growth_bytes'] for x in checks)/(1<<20),PS_payload_MiB=c['ps_payload_bytes']/(1<<20))
    value=dict(status='PASS_SINGLE_DESCRIPTOR_PS_BINDING_ONLY' if passed else 'STOP_EXPANSION_AT_PS_DESCRIPTOR',raw_sha256=prior['sha256'],build_id=r['build_id'],errors=r['errors'],physical_transactions=r['fpga_transactions'],model_forward_calls=r['model_forward_calls'],observed_memory=observed,component=c,slot_release=p.get('slot_release'),session_weakref_dead=r.get('session_weakref_dead'),seven_dma_released=len(r['released_buffers']),PS_read_overlap_proven=False,new_performance_pass=False,production_admission_changed=False,next_step='Prepare one representative complete chain binding numerical gate, original one parser and frozen math; then layer/text/video only after each raw/closure triad. Single first-window read does not demonstrate overlap or benefit' if passed else 'Debug only failed descriptor/lifecycle/capacity level; no layer/text/video/performance expansion')
    out=BASE/'runs/M383-ps-descriptor-closure-01';atomic(out/'RESULT.json',encoded(value),immutable=True);d=sha(out/'RESULT.json')
    report='# M383 PS 暂存单 descriptor 门禁\n\n'+value['status']+'，Build '+r['build_id']+'。\n\n原始SHA '+prior['sha256']+'；闭合SHA '+d+'。\n\n'+json.dumps(observed,ensure_ascii=False,indent=2)+'\n\n复用现有PS组件和真实权重；一个26.5625MiB普通slot，无新增DMA。只有原Q第一descriptor，同Overlay最小事务后分别原暂存与PS暂存，完整输出对原FTZ golden和两次权重字节核对。保留原生产64MiB，独立sealed-DMA普通内存预算和实际计数停止。\n\n本级只有第一次窗口，没有下一窗口可提前读取，因此不能证明计算/读取重叠，也不能称新性能优化已成功。slot唯一所有权、worker/fd/view/session恢复及七DMA释放分开核对。\n\n下一步：'+value['next_step']+'。\n'
    atomic(out/'REPORT.md',report.encode('utf-8'))
    sync('latest_m383_ps_descriptor_closure',dict(status=value['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=d,raw_sha256=prior['sha256'],numerical_pass=passed,performance_pass=False),f'## M383 PS单descriptor闭合（2026-10-03）\n\n{value["status"]}，原SHA {prior["sha256"]}，闭合SHA {d}。实际内存 {json.dumps(observed)}；真实3物理/0forward，原权重/完整wire及slot/session/七DMA生命周期核对。仅首窗口，未证明读取重叠或新净收益；原生产准入不改。下一步 {value["next_step"]}。')
    print(json.dumps(dict(status=value['status'],sha256=d,memory=observed,errors=value['errors'])))
if __name__=='__main__':main()
