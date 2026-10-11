"""Close only saved integrated numerical evidence; no board or model operation."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m432_workflow02 import check, PKG


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m432_integrated_board']
    if sha(ROOT/e['result'])!=e['sha256'] or not all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md')):
        raise RuntimeError('Saved integrated evidence not synchronized')
    r=check(json.loads((ROOT/e['result']).read_bytes()));passed=r['status']=='PASS_M432_INTEGRATED_VIDEO_NUMERICAL'
    status='CLOSED_M432_LATE11_INTEGRATED_NUMERICAL_PASS' if passed else 'CLOSED_M432_LATE11_INTEGRATED_NUMERICAL_FAILURE'
    record=dict(status=status,raw_sha256=e['sha256'],manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],gate_return_code=r['gate_return_code'],errors=r['errors'],
                selected_layers=list(range(13,24)),visual_forward_calls=r.get('vision_forward_calls',0),language_forward_calls=r.get('model_forward_calls',0),
                integrated_exact_comparisons=r.get('integrated_exact_comparisons',[]),all24_visual_boundaries_checked=len(r.get('integrated_boundaries',[])),
                visual_transactions=len(r.get('visual_transactions',[])),visual_staging_bytes=sum(x['bytes'] for x in r.get('visual_staging',[])),
                language_physical_transactions=r.get('host_calls',0),total_physical_transactions=r['fpga_transactions'],
                allocations=len(r['allocated_buffers']),releases=len(r['released_buffers']),original_DMA_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
                extra_DMA=r.get('borrowed_extra_DMA'),borrowed_buffer_identity_preserved=r.get('borrowed_buffer_identity_preserved',False),
                static_cache_invalidated=r.get('visual_static_cache_invalidated',False),provider_disposed=r.get('visual_provider_disposed',False),
                safe_buffers_released=r.get('safe_buffers_released',False),unsafe_buffers_retained=r['unsafe_buffers_retained'],stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),
                samples=[dict(variant=s['variant'],counts=s['counts'],decision=s['decision']) for s in r.get('samples',[])],logit_comparison=r.get('logit_comparison'),
                memory_checkpoints=[dict(label=x['label'],rss_bytes=x['memory']['process_bytes']['VmRSS'],CmaFree_bytes=x['memory']['system_bytes']['CmaFree'],MemAvailable_bytes=x['memory']['system_bytes']['MemAvailable']) for x in r.get('stage_memory',[])],
                numerical_pass=passed,fixed_input_decision_consistency_pass=passed,full_request_performance_gate_preparation_unlocked=passed,
                full_request_performance_proven=False,dataset_accuracy_proven=False,production_promoted=False,temperature_measurement_enabled=False,
                next_step='Freeze one bounded light-statistics controlled warm complete-request comparison: four ABBA warmups and eight ABBA/BAAB formal requests, original stream timing and exact post-timer references; no extra samples or production promotion.' if passed else 'Debug only this saved integrated numerical failure; collect saved bytes only and preserve owner if unsafe. Performance remains locked.')
    report='# M432 后11层完整视觉—语言数值闭合\n\n'+status+'。原raw SHA `'+e['sha256']+'`，gate rc '+str(r['gate_return_code'])+'。\n\n'
    report+='原版和候选各实际执行一次原固定末帧两视图视觉，再接相同159-token语言/完整LM head，输出预算1、Decode0。只有B的13–23层MLP两个Linear借用原语言七DMA使用现有并行PL核；Attention、GELU、归一化、语言量化/pack/parse/重试不改。\n\n'
    report+='A/B分别与各自M428已接受参考核对完整视觉特征、embedding、151936 logits、72份K/V、154 family及重试/物理序列；B另外核对全部286 wire及24边界。各变体接入前后须逐位一致；A8候选相对原CPU的差异保留M427/M428质量裁决。\n\n'
    report+=f'实际视觉/语言 {record["visual_forward_calls"]}/{record["language_forward_calls"]}，视觉PL {record["visual_transactions"]}，视觉暂存 {record["visual_staging_bytes"]}B，语言物理 {record["language_physical_transactions"]}，总物理含合法最小 {record["total_physical_transactions"]}。原DMA {record["original_DMA_bytes"]}B，分配/释放 {record["allocations"]}/{record["releases"]}，额外DMA {record["extra_DMA"]}。安全释放 {record["safe_buffers_released"]}，稳定Overlay恢复 {record["stable_overlay_reloaded"]}。\n\n'
    report+='没有固定64MiB CMA floor，普通PS预算/64MiB MemAvailable余量及新增DMA封锁保持。不测温，生产准入未改。稳定恢复后未提交DMA，不把初始DMASR0当完成事务证明。\n\n'
    report+='诊断的哈希/导出时间不用于性能。这是固定输入一致性证据，不是独立标注准确率，也不代表新的完整请求提速；M430完整视觉7.686577%收益及原语言并行40.81%结论各自保持。\n\n'
    if r['errors']:report+='原失败：\n\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+record['next_step']+'\n'
    out=BASE/'runs/M432-integrated-closure-01/RESULT.json';atomic(out,encoded(record),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m432_integrated_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],numerical_pass=passed,full_request_performance_gate_preparation_unlocked=passed,full_request_performance_proven=False),
         f'## M432 后11层完整请求数值闭合（2026-10-07）\n\nSHA {sha(out)}，raw {e["sha256"]}，{status}。实际视觉/语言{record["visual_forward_calls"]}/{record["language_forward_calls"]}，286视觉PL/24边界及各151936 logits/72KV/154family/retry逐位参考，七DMA分配/释放{record["allocations"]}/{record["releases"]}、额外{record["extra_DMA"]}，稳定恢复{record["stable_overlay_reloaded"]}。无新的完整请求性能/独立准确率/生产晋级，不测温；下一步：{record["next_step"]}')
    print('M432_INTEGRATED_CLOSURE_SYNC',sha(out),status)


if __name__=='__main__':main()
