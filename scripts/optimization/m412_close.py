"""Interpret the one saved attempt only; no UART or hardware replay."""
import json,statistics
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m412_complete_mlp_board'];p=ROOT/e['result']
    assert sha(p)==e['sha256'];r=json.loads(p.read_bytes())
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert not any(r[k] for k in ('full_model','video','promoted','expanded_24_layers'))
    success=r['gate_return_code']==0
    status=('CLOSED_M412_COMPLETE_MLP_LOCAL_NET_GAIN' if r['performance_pass'] else 'CLOSED_M412_COMPLETE_MLP_NET_GAIN_UNPROVEN') if success else 'CLOSED_M412_ORIGINAL_FAILURE'
    memory=list(r.get('memory',[]))+list(r.get('PS_checkpoints',[]))
    v=dict(status=status,raw_sha256=e['sha256'],gate_return_code=r['gate_return_code'],original_status=r['status'],phase=r['phase'],errors=r['errors'],
        numerical_pass=r['numerical_pass'],isolated_complete_MLP_performance_pass=r['performance_pass'],full_visual_semantic_or_request_performance=False,expanded_24_layers=False,
        actual_PL_rows=len(r['PL_rows']),physical_transactions=r['physical_transactions_started'],allocations=len(r['allocations']),releases=len(r['releases']),
        planned_main_payload_bytes=3440656,actual_main_payload_bytes=sum(x['bytes'] for x in r['allocations'] if x['label']=='completeMLP-seven'),
        minimum_observed_CmaFree_MiB=min((x['CmaFree']/2**20 for x in memory),default=None),minimum_observed_MemAvailable_MiB=min((x['MemAvailable']/2**20 for x in memory),default=None),maximum_observed_RSS_growth_MiB=max((x['RSS_growth_bytes']/2**20 for x in memory),default=None),
        fixed_CMA64_floor_used=False,ordinary_growth_limit_MiB=256,ordinary_available_reserve_MiB=64,
        owner_closed=r.get('PS_owner_closed'),allocator_restored=r.get('DMA_allocator_restored'),safe_buffers_released=r['safe_buffers_released'],unsafe_retained=r['unsafe_dma_buffers_retained'],stable_restored=r.get('stable_restored',False),
        comparison=r.get('comparison'),quality_metrics=r.get('quality_metrics'),samples=r.get('samples',[]),hardware_replayed_for_collection=False,
        prior_M411_failure_preserved=True,old_language_parallel_40_81percent_independent_unchanged=True)
    report=f'# M412 独立准入完整视觉MLP闭合\n\n{status}，原rc {r["gate_return_code"]}；raw SHA `{e["sha256"]}`。只复用第12层已保存392行真实输入，不重跑完整视觉/语言。\n\n'
    report+='原M411在分配前因固定CMA64MiB拒绝，不是实际分配失败。本次独立入口按实际七缓冲3,440,656B分配后封锁额外公共DMA，CmaFree仅记录；普通PS增长256MiB和普通MemAvailable余量64MiB是另外的预算。生产入口、稳定源码/rollback、boot/DTB/CMA配置和输入不变。原生/驱动零分配及任意输入长期峰值均未认证。\n\n'
    report+='|检查|结果|\n|---|---|\n'
    for key in ('phase','numerical_pass','isolated_complete_MLP_performance_pass','actual_PL_rows','physical_transactions','allocations','releases','actual_main_payload_bytes','minimum_observed_CmaFree_MiB','minimum_observed_MemAvailable_MiB','maximum_observed_RSS_growth_MiB','owner_closed','allocator_restored','safe_buffers_released','unsafe_retained','stable_restored'):
        report+=f'|{key}|{v[key]}|\n'
    if v['samples']:
        report+='\n计时为完整单MLP段：从第一权重读/恢复到两Linear+bias/原GELU的PS可用输出；含暂存/量化/pack/传输/等待/原解析/重试/转换。数值核对在计时外；原AB预热及ABBABAAB固定八次，不追加样本。保留每次原read_bytes/rchar和内存，不是完整视觉或请求成绩。\n\n|次序|分支|完整段秒|磁盘read_bytes|rchar|\n|---|---|---:|---:|---:|\n'
        for i,x in enumerate(v['samples'],1):report+=f'|{i}|{x["variant"]}|{x["elapsed_ns"]/1e9:.6f}|{x["read_bytes"]}|{x["rchar"]}|\n'
        for variant in ('A','B'):
            seconds=[x['elapsed_ns']/1e9 for x in v['samples'] if x['variant']==variant]
            report+=f'\n{variant} 均值 {statistics.mean(seconds):.6f}s，范围 {min(seconds):.6f}–{max(seconds):.6f}s。\n'
        report+='\n原预登记裁决：\n```json\n'+json.dumps(v['comparison'],ensure_ascii=False,indent=2)+'\n```\n'
    if v['errors']:report+='\n原失败：\n```json\n'+json.dumps(v['errors'],ensure_ascii=False,indent=2)+'\n```\n'
    next_step='Only after this isolated precision/net-time/lifecycle PASS, independently prepare semantic quality and bounded layer expansion; no automatic24-layer execution.' if success and r['performance_pass'] else ('Close this visual MLP timing variant without expansion or added samples; preserve local numeric evidence.' if success else 'Debug only the saved current failure level; no complete visual/model/performance replay for collection.')
    v['next_concrete_step']=next_step;report+='\n下一步：'+next_step+'\n'
    out=BASE/'runs/M412-complete-MLP-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m412_complete_mlp_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],numerical_pass=v['numerical_pass'],performance_pass=v['isolated_complete_MLP_performance_pass'],expanded_24_layers=False),
        f'## M412 独立准入完整视觉MLP闭合（2026-10-06）\n\nSHA {sha(out)}，原raw {e["sha256"]}保留，{status}。取消本隔离入口固定CMA64MiB门槛；七缓冲计划3,440,656B按实际分配及封锁新增，普通PS256MiB增长/64MiB普通余量与生命周期保持。数值{v["numerical_pass"]}，完整MLP段净时间{v["isolated_complete_MLP_performance_pass"]}，实际PL行{v["actual_PL_rows"]}、事务{v["physical_transactions"]}、分配/释放{v["allocations"]}/{v["releases"]}；最低CMA{v["minimum_observed_CmaFree_MiB"]}MiB，非任意输入/native峰值或全视觉/语义/完整请求收益。未扩24层，生产/稳定回滚/boot/DTB/CMA保持，旧语言40.81%独立。下一步 {next_step}')
    print('M412_CLOSURE_SYNC',sha(out),status)
if __name__=='__main__':main()
