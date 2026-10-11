"""Adjudicate complete ABBA constructor diagnostics, not request performance."""
import json
import m351_workflow as w
import m361_collect_load_comparison as c

def main():
    rows=[];bindings=[]
    for case in c.CASES:
        p=w.BASE/f'runs/M361-load-{case}-board-01/BOARD_RESULT.json';r=json.loads(p.read_text(encoding='utf-8'))
        assert c.validate(r) and c.completed(r)
        digest=w.sha(p)
        for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (w.ROOT/name).read_text(encoding='utf-8-sig')
        bindings.append(dict(case=case,path=p.relative_to(w.ROOT).as_posix(),sha256=digest))
        rows.append(r)
    reference=[(x['name'],x['first_path'],x.get('returned_sha256')) for x in rows[0]['io_events'] if 'returned_sha256' in x]
    for row in rows[1:]:assert [(x['name'],x['first_path'],x.get('returned_sha256')) for x in row['io_events'] if 'returned_sha256' in x]==reference
    assert len({r['common_runner_sha256'] for r in rows})==1
    assert all([x['bytes'] for x in r['allocated_buffers']]==c.SIZES for r in rows)
    bits=[r['build_id'] for r in rows];assert bits==['0x4D395832','0x4D333537','0x4D333537','0x4D395832']
    summary=[]
    for r in rows:
        io=[]
        for x in r['io_events']:
            before=x['before'];after=x['after']
            io.append(dict(name=x['name'],path=x['first_path'],sha256=x.get('returned_sha256'),delta_bytes={k:after['system_bytes'][k]-before['system_bytes'][k] for k in ('CmaFree','Cached','MemAvailable')},rss_delta_bytes=after['process_bytes']['VmRSS']-before['process_bytes']['VmRSS']))
        allocation=[]
        stages={x['name']:x for x in r['stages']}
        for buffer in r['allocated_buffers']:
            before=stages['before-DMA-allocation-'+buffer['role']]['memory'];after=stages['after-DMA-allocation-'+buffer['role']]['memory']
            allocation.append(dict(buffer,cma_delta_bytes=after['system_bytes']['CmaFree']-before['system_bytes']['CmaFree']))
        summary.append(dict(case=r['case'],build_id=r['build_id'],status=r['status'],initial_memory=r['stages'][0]['memory'],loaded_capacity=r['loaded_capacity'],settled_capacity=r['settled_capacity'],io_deltas=io,allocation_deltas=allocation,retained_inventory=r['retained_inventory'],retained_mappings=r['retained_mappings']))
    all_fit=all(r['memory_capacity_proven'] for r in rows)
    stable_fit=[r['memory_capacity_proven'] for r in rows if r['case'].startswith('A')];candidate_fit=[r['memory_capacity_proven'] for r in rows if r['case'].startswith('B')]
    if all_fit:decision='COMMON_LOAD_CAPACITY_PASSES_ONLY_NO_FORWARD'
    elif not any(stable_fit+candidate_fit):decision='BOTH_VARIANTS_REJECT_RESERVE_INVESTIGATE_COMMON_LOAD'
    elif all(stable_fit) and not any(candidate_fit):decision='CANDIDATE_ONLY_REJECTS_INVESTIGATE_BIT_OR_ENTRY_EFFECT_WITH_CACHE_LIMIT'
    else:decision='MIXED_NATURAL_MEMORY_CAPACITY_NO_STABLE_CONCLUSION'
    out=w.BASE/'runs/M361-load-comparison-closure-01'
    result=dict(status=decision,bindings=bindings,ordered_cases=list(c.CASES),source_hash_sequence_equal=True,original_buffer_geometry_equal=True,common_runner_equal=True,cache_conditions='Natural residency varied; no eviction, no claim identical cache or isolated causal treatment',summary=summary,capacity_unlocked=all_fit,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,next_step='Inspect largest repeated common file/checkpoint reductions and concrete owned objects. Make at most one justified memory-lifecycle fix before any new capacity test. No Q replay or model-forward automatic expansion.')
    lines=['# M361 稳定版/候选版共同入口只加载对照','', '| 次序 | Build | 初始CMA MiB | 构造完成CMA MiB | +2秒CMA MiB | 容量裁决 |','|---|---|---:|---:|---:|---|']
    for r in summary:lines.append(f"| {r['case']} | {r['build_id']} | {r['initial_memory']['system_bytes']['CmaFree']/(1<<20):.6f} | {r['loaded_capacity']['cma_free_bytes']/(1<<20):.6f} | {r['settled_capacity']['cma_free_bytes']/(1<<20):.6f} | {r['status']} |")
    lines+=['',decision,'','原完整SHA调用序列/摘要一致，七块缓冲的用途与大小一致；共同观察器及入口相同，仅Overlay路径变化。自然缓存状态有差异，不能把相同政策写成缓存完全相同；观察阶段变化也不证明具体物理页归属或不可回收碎片。','']
    for r in summary:
        lines +=['## '+r['case']+' 逐文件读取中最大CMA下降','', '| 调用 | 文件 | CMA变化 MiB | Cached变化 MiB | RSS变化 MiB |','|---|---|---:|---:|---:|']
        for x in sorted(r['io_deltas'],key=lambda x:x['delta_bytes']['CmaFree'])[:8]:lines.append(f"| {x['name']} | {x['path']} | {x['delta_bytes']['CmaFree']/(1<<20):+.6f} | {x['delta_bytes']['Cached']/(1<<20):+.6f} | {x['rss_delta_bytes']/(1<<20):+.6f} |")
    lines+=['','0模型forward、0FPGA事务、无新增CMA/PS slot；7块各安全释放一次，稳定Overlay重新加载仅未提交生命周期，不作为已完成DMA空闲或硬件数值证据。','','Q代表链已经通过的结果保持；其他W4/MLP、单层、固定文本及159-token视频数值和完整请求时间尚未验证。本诊断不计算推理提速。']
    w.atomic(out/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m361_load_comparison_closure',dict(status=decision,sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),capacity_unlocked=all_fit),f'## M361 共同入口加载对照闭合\n\nA-B-B-A四例原SHA序列/缓冲几何/观察器一致；裁决{decision}，自然缓存差异记录，不宣称物理页归属。0forward/FPGA、无新bank/PSslot，不重跑Q。证据SHA `{digest}`。容量之外数值/性能不自动解锁；仅在明确临时对象或重复占用后做一处修复。')
    print(decision,digest)

if __name__=='__main__':main()
