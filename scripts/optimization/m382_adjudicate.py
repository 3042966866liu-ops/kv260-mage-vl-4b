"""Adjudicate saved slot-only evidence; never run/collect hardware."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    path=BASE/'runs/M382-sealed-ps-slot-board-01/BOARD_RESULT.json'
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    raw=board['latest_m382_sealed_ps_slot_board'];assert raw['sha256']==sha(path)
    assert all(raw['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(path.read_text(encoding='utf-8'));p=r.get('ps_slot',{});passed=r['status']=='PASS_M382_SEALED_LOAD_ONLY_PS_SLOT'
    summary={}
    def summary_at(label,m):
        summary[label]={k+'_MiB':v/(1<<20) for k,v in dict(RSS=m['process_bytes']['VmRSS'],HWM=m['process_bytes']['VmHWM'],CmaFree=m['system_bytes']['CmaFree'],MemAvailable=m['system_bytes']['MemAvailable']).items()}
    for label,m in [('before_slot',p.get('baseline_before_slot')),('after_slot_release_runtime_retained',p.get('after_release_runtime_retained')),('after_slot_release_settled_runtime_retained',p.get('after_release_settled_runtime_retained'))]:
        if m:summary_at(label,m)
    for x in p.get('checkpoints',[]):
        if x['name']=='PS-slot:all-four-retained-after-settle':summary_at('slot_live_runtime_retained',x['memory'])
    rvalue=dict(status='PASS_LOAD_ONLY_SLOT_LIFECYCLE_PRECONDITION' if passed else 'STOP_EXPANSION_AT_SLOT_DIAGNOSTIC',raw_sha256=raw['sha256'],build_id=r['build_id'],errors=r['errors'],slot_bytes=p.get('slot_bytes'),actual_memory=summary,slot_object_release=p.get('release'),seven_dma_release_count=len(r['released_buffers']),global_cma_api_unchanged=passed,model_forward_calls=r['model_forward_calls'],physical_transactions=r['fpga_transactions'],ordinary_memory_native_peak_proven=False,full_video_memory_capacity_proven=False,numerical_pass=False,performance_pass=False,production64MiB_unchanged=True,existing_PS_component_unchanged=True,stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),source_sha256=sha(path),rejected_offline_test_receipt_sha256=sha(BASE/'runs/M382-offline-rejection-01/RESULT.json'),next_step='Only now design isolated sealed-DMA admission adapter and reuse existing one-slot PS read source; begin descriptor/chain numerical binding gates with original one parser, then layer/text/video; capacity/lifecycle failure stops expansion' if passed else 'Debug only failed slot/capacity/lifecycle level; no pre-read/model expansion')
    out=BASE/'runs/M382-sealed-ps-slot-closure-01';atomic(out/'RESULT.json',encoded(rvalue),immutable=True);digest=sha(out/'RESULT.json')
    rows=['|阶段|RSS MiB|HWM MiB|CMA空闲 MiB|普通可用 MiB|','|---|---:|---:|---:|---:|']
    for name,x in summary.items():rows.append(f'|{name}|{x["RSS_MiB"]:.3f}|{x["HWM_MiB"]:.3f}|{x["CmaFree_MiB"]:.3f}|{x["MemAvailable_MiB"]:.3f}|')
    report='# M382 完整runtime驻留 PS slot 分配—触页—释放诊断\n\n'+rvalue['status']+'，Build '+r['build_id']+'。\n\n'+'\n'.join(rows)+'\n\nslot27,852,800B，七原DMA全程驻留至slot释放，0新增专用CMA申请/forward/PL事务/预读worker。实际CmaFree原值报告；生产和旧PS组件64MiB CMA检查未改。本次独立准入：slot前RSS为基准，64MiB普通PS增长实验上限，剩余预算之外64MiB MemAvailable余量，global CMA API计数不变。该上限不是已证明native峰值。\n\n释放依据是所有bytearray仅由slot持有、包装对象weakref全死；RSS是否回落单独报告，不以RSS判对象泄漏，无GC/trim/清缓存。七DMA随后逆序幂等释放，稳定Overlay恢复且无恢复事务。未做推理，因此不证明视频slot峰值、输出一致或新性能收益。\n\n原始SHA '+raw['sha256']+'；闭合SHA '+digest+'。\n\n下一步：'+rvalue['next_step']+'。\n'
    atomic(out/'REPORT.md',report.encode('utf-8'))
    sync('latest_m382_sealed_ps_slot_closure',dict(status=rvalue['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,raw_sha256=raw['sha256'],performance_pass=False),f'## M382 PS slot只加载闭合（2026-10-03）\n\n{rvalue["status"]}，Build0x4D333537，原SHA {raw["sha256"]}，闭合SHA {digest}。实际内存 {json.dumps(summary,ensure_ascii=False)}。0forward/PL/额外PYNQ；sole-owned bytearrays及owner weakref、七DMA逆序回收分开核对，原生产/旧组件64MiB保持，非视频峰值或新增性能。下一步 {rvalue["next_step"]}。')
    print(json.dumps(dict(status=rvalue['status'],sha256=digest,memory=summary,next_step=rvalue['next_step'])))
if __name__=='__main__':main()
