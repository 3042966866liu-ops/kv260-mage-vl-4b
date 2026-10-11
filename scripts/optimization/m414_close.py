"""Close exactly the retained selected-layer visual attempt, no UART/replay."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());row=board['latest_m414_layer12_visual_board'];path=ROOT/row['result']
    assert sha(path)==row['sha256'] and all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    result=json.loads(path.read_bytes());success=result['gate_return_code']==0
    if success:assert result['feature_quality_pass'] and result['numerical_pass'] and result['stable_restored'] and result['safe_buffers_released']
    assert not result['semantic_quality_proven'] and not result['expanded_24_layers'] and not result['performance_pass']
    status='CLOSED_M414_LAYER12_COMPLETE_VISUAL_FEATURE_SCREEN_PASS' if success else 'CLOSED_M414_ORIGINAL_VISUAL_FAILURE'
    memory=result.get('memory',[])+result.get('PS_checkpoints',[])
    v=dict(status=status,raw_sha256=row['sha256'],gate_return_code=result['gate_return_code'],build_id=result['build_id'],phase=result['phase'],errors=result['errors'],
           selected_layers=result['selected_layers'],actual_visual_forward_calls=result['visual_forward_calls'],actual_language_forward_calls=result['language_forward_calls'],
           feature_quality_pass=result['feature_quality_pass'],local_numerical_pass=result['numerical_pass'],full_visual_quality=result.get('full_visual_quality'),
           final_original_visual=result.get('original_visual'),final_candidate_visual=result.get('candidate_visual'),
           local_quality_metrics=result.get('quality_metrics'),retained_visual_features=result.get('retained_visual_features'),
           physical_transactions=result['physical_transactions_started'],actual_PL_rows=len(result['PL_rows']),
           allocations=len(result['allocations']),releases=len(result['releases']),main_DMA_payload_bytes=3440656,
           minimum_observed_CmaFree_MiB=min((x['CmaFree']/2**20 for x in memory),default=None),minimum_observed_MemAvailable_MiB=min((x['MemAvailable']/2**20 for x in memory),default=None),
           maximum_observed_RSS_growth_MiB=max((x['RSS_growth_bytes']/2**20 for x in memory),default=None),
           all_layer_memory_checkpoints=len(result['PS_checkpoints']),safe_buffers_released=result['safe_buffers_released'],unsafe_retained=result['unsafe_dma_buffers_retained'],
           stable_restored=result.get('stable_restored',False),PS_owner_closed=result.get('PS_owner_closed',False),bindings_restored=result['bindings_restored'],DMA_allocator_restored=result['DMA_allocator_restored'],
           semantic_accuracy_proven=False,performance_claim=False,expanded_layers=False,replayed_for_collection=False,
           ordinary_PS_growth_budget_MiB=768,CMA64_fixed_floor=False,
           next_concrete_step='Keep candidate limited to layer12. Final feature screen alone is not task accuracy: prepare unchanged-input recognition-quality gate before layer expansion.' if success else 'Debug only retained failing phase; no layer expansion, additional forward, or rerun for collection.')
    report='# M414 第12层接入后的完整视觉特征质量闭合\n\n'+status+'，原rc '+str(v['gate_return_code'])+'，Build '+v['build_id']+'。原始SHA `'+v['raw_sha256']+'`。\n\n'
    report+='固定原末帧两个224视图。实际完整视觉前向次数 '+str(v['actual_visual_forward_calls'])+'，第12层PL执行批次数 '+str(v['actual_PL_rows'])+'。计划原版及候选各一次；未到达的步骤不算完成。保留前两层BF16、其余23层、Attention/GELU/norm、视觉Merger和语言路径。原版完整视觉SHA须等于已有参考；第12层真实输入/全部26包与wire须逐位核对已有M409精确量化参考。没有新增画像、性能样本或扩层。\n\n'
    if v['full_visual_quality']:
        q=v['full_visual_quality'];m=q['metrics'];t=q['thresholds']
        report+='|最终98×2560特征指标|实测|预先固定筛选线|\n|---|---:|---:|\n'
        report+=f'|相对L2|{m["relative_l2"]:.10f}（{m["relative_l2"]*100:.6f}%）|≤{t["maximum_relative_l2"]}|\n|整体余弦|{m["cosine"]:.10f}|≥{t["minimum_cosine"]}|\n|最低token余弦|{m["min_token_cosine"]:.10f}|≥{t["minimum_token_cosine"]}|\n|RMSE|{m["RMSE"]:.10f}|记录|\n|最大绝对差|{m["max_abs"]:.10f}|记录|\n'
    report+='\n|内存及生命周期|结果|\n|---|---|\n'
    for k in ('actual_visual_forward_calls','actual_language_forward_calls','actual_PL_rows','physical_transactions','allocations','releases','main_DMA_payload_bytes','minimum_observed_CmaFree_MiB','minimum_observed_MemAvailable_MiB','maximum_observed_RSS_growth_MiB','all_layer_memory_checkpoints','safe_buffers_released','PS_owner_closed','bindings_restored','DMA_allocator_restored','stable_restored'):
        report+=f'|{k}|{v[k]}|\n'
    report+='\nCMA统计仅记录，实际七块小DMA成功分配后封锁新增公共DMA。普通PS预算沿用完整视觉768MiB增长＋64MiB普通可用余量；逐层边界/提交采样不是连续native峰值证明。原35完整SHA、49源码及稳定rollback/boot/DTB/CMA保持。\n\n'
    report+='特征误差阈值是预先固定的数值筛选，不是已校准的识别准确率判据；尚未运行候选语言、logits/判断或多输入质量评估。两次视觉墙钟包含钩子和诊断，不构成性能比较；M412完整单MLP31.93%与原语言40.81%各自保持原范围。\n\n'
    if v['retained_visual_features']:
        report+='两份完整视觉特征留在板端本次结果目录，文件及张量SHA见原始结果；未导出数组到主机，不把元数据当作主机已拥有数组。\n\n'
    else:
        report+='本次未到达完整视觉特征文件保存；原版只有结果中的张量SHA，没有可供逐元素离线比较的已保存完整数组。bindings_restored 的 false 是未到成功汇总赋值，不单独证明钩子未释放；PS对象关闭及实际DMA释放见上表。\n\n'
    if v['errors']:report+='原失败（保留）：\n```json\n'+json.dumps(v['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+v['next_concrete_step']+'\n'
    out=BASE/'runs/M414-layer12-visual-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m414_layer12_visual_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=v['raw_sha256'],feature_quality_pass=v['feature_quality_pass'],semantic_quality_proven=False,expanded_layers=False),
         f'## M414 第12层完整视觉特征闭合（2026-10-06）\n\nSHA {sha(out)}，原raw {v["raw_sha256"]}保留，{status}。实际完整视觉{v["actual_visual_forward_calls"]}次，特征筛选{v["feature_quality_pass"]}；PL {v["actual_PL_rows"]}行、物理{v["physical_transactions"]}、分配/释放{v["allocations"]}/{v["releases"]}，稳定恢复{v["stable_restored"]}。最低CMA {v["minimum_observed_CmaFree_MiB"]}MiB，仅观察，普通PS增长768MiB预算。无语言/语义准确率/性能/扩层，阈值只数值筛选，下一步{v["next_concrete_step"]}。')
    print('M414_CLOSURE_SYNC',sha(out),status)
if __name__=='__main__':main()
