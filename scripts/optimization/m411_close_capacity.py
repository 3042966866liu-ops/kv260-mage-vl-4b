"""Classify actual pre-allocation reserve rejection; never replay hardware."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m411_complete_mlp_board'];p=ROOT/e['result'];assert sha(p)==e['sha256']
    r=json.loads(p.read_bytes());assert r['status']=='FAIL_M411_COMPLETE_MLP' and r['gate_return_code']==1 and r['phase']=='PS-constructor'
    assert len(r['errors'])==1 and r['errors'][0]['type']=='MemoryError' and 'below64MiB' in r['errors'][0]['message']
    assert r['allocations']==r['releases']==r['overlay_loads']==r['transactions']==r['samples']==r['warmups']==r['PL_rows']==[] and r['physical_transactions_started']==r['local_mlp_calls']==0
    assert r['PS_owner_closed'] and r['safe_buffers_released'] and not r['unsafe_dma_buffers_retained']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    before=r['memory_before_constructor'];after=r['memory_after_constructor'];floor=64<<20
    v=dict(status='CLOSED_M411_PRE_ALLOCATION_CMA_RESERVE_REJECTION',raw_sha256=e['sha256'],raw_result=e['result'],original_gate_rc=1,export_rc=0,
        original_35_asset_preflight_PASS=r['release_preflight']['status']=='READY_FOR_BOARD_PREFLIGHT',frozen_sources_verified=49,actual_board_Torch_small_component_PASS=r['component'],
        observed_before_constructor=before,observed_after_constructor=after,observed_after_PS_owner_close=r['memory_after_cleanup'],
        CMA_reserve_bytes=floor,CMA_deficit_after_constructor_bytes=floor-after['CmaFree'],constructor_CMA_decrease_bytes=before['CmaFree']-after['CmaFree'],
        seven_planned_buffers_payload_bytes=3440656,actual_DMA_allocations=0,overlay_loads=0,PL_transactions=0,actual_MLP_forwards=0,
        original_PS_owner_collected=True,stable_Overlay_was_not_changed=True,performance_test_started=False,target_complete_numerical_test_started=False,
        interpretation='64MiB safety reserve rejected before any allocation/forward; not failed DMA allocation, not total4GB exhaustion, not target quality or speed rejection.',
        attribution_limit='before_constructor is already after full35 hashing/Torch import/reference loading/component; no separated CMA checkpoints for those stages. Only constructor interval decrease observed; no page ownership or cache reclaim/root-cause proof.',
        prior_M410_descriptor_and_chain_PASS_preserved=True,expanded_24_layers=False,production_threshold_changed=False,cache_eviction=False,
        next_step='Stop expansion and timed retry. Audit this isolated-entry memory/checkpoint coverage at this failed capacity level; retain35 complete hashes and64MiB reserve. Need actual qualifying memory condition before any MLP numerical/performance retry.')
    out=BASE/'runs/M411-complete-MLP-capacity-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    mb=lambda x:x/(1<<20)
    report=f'''# M411 完整视觉MLP门禁容量失败闭合

原结果 `{e['sha256']}`，gate rc1/export rc0，9个≤900B分块完整SHA回收；未重执行。

原35资产完整SHA和49冻结源码通过，板端真实Torch/M207/Siglip小组件通过（submit为PS软件数学替身、buffer/sync明确fake，不是目标PL）。实际构造的第12层矩阵/bias/精度/原M261非缓存两目标合同通过。

|观察点|CmaFree MiB|MemAvailable MiB|PS RSS MiB|
|---|---:|---:|---:|
|构造前（已完成资产校验/Torch导入/参考加载/小组件）|{mb(before['CmaFree']):.6f}|{mb(before['MemAvailable']):.6f}|{mb(before['VmRSS']):.6f}|
|完整原PS视觉对象构造后|{mb(after['CmaFree']):.6f}|{mb(after['MemAvailable']):.6f}|{mb(after['VmRSS']):.6f}|

构造区间CMA下降 {mb(v['constructor_CMA_decrease_bytes']):.6f} MiB；距64MiB保留余量缺 {mb(v['CMA_deficit_after_constructor_bytes']):.6f} MiB。七块计划payload 3,440,656B（{mb(3440656):.6f}MiB），但这次一块都没申请。不能把门槛拒绝表述为分配失败或4GB内存用尽。

Overlay0、DMA分配0、PL事务0、实际MLP forward0、warmup0、计时样本0。原PS owner弱引用证明已回收；正常退出，稳定Overlay从未改变。立即退出前统计不是实际推理容量或页归属证明。

M410首32行单descriptor/双descriptor链完整wire PASS保持；M411未给出392行PL数值或完整段净时间结论。没有因本次失败否定旧语言并行核40.81%完整请求收益，也未判断新的视觉MLP候选提速与否。

本轮停止扩大测试、不进24层、不降低64MiB、不清缓存、不改boot/DTB/CMA或服务。下一项只能在此容量失败级核查独立入口的内存检查点/预算；这份raw的构造前点已经晚于资产校验等多个阶段，不能从它定位每个阶段或文件的责任。实际容量条件成立后才允许重试完整MLP数值/预定固定计时，不能直接重跑昂贵模型或扫描样本。
'''
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m411_complete_mlp_capacity_closure',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],performance_pass=False,expanded_24_layers=False),
        f'## M411 完整视觉MLP容量拒绝闭合（2026-10-06）\n\nSHA {sha(out)}，原FAIL {e["sha256"]}保持；rc1/export0，0Overlay/DMA分配/PL/实际MLP/warmup/计时，原PS owner回收。构造前CMA{mb(before["CmaFree"]):.6f}MiB，构造后{mb(after["CmaFree"]):.6f}MiB，缺原64MiB余量{mb(v["CMA_deficit_after_constructor_bytes"]):.6f}MiB；MemAvailable{mb(after["MemAvailable"]):.6f}MiB，不是4GB耗尽或已尝试DMA分配失败。M410两最小硬件PASS保持；未得到完整MLP数值或净时间。停止扩大/计时重跑/24层，保留门槛、原35完整SHA及稳定回滚；仅在本容量失败级核查阶段/预算，不推断页归属。')
    print('M411_CAPACITY_CLOSED',sha(out),json.dumps(dict(after_CMA_MiB=mb(after['CmaFree']),deficit_MiB=mb(v['CMA_deficit_after_constructor_bytes']),constructor_decrease_MiB=mb(v['constructor_CMA_decrease_bytes']),MemAvailable_MiB=mb(after['MemAvailable']))))
if __name__=='__main__':main()
