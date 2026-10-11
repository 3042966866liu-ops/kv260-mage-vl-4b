"""Interpret exactly the saved combination result; no board or extra forwards."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m420_workflow03 import validate
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m420_combination_board'];p=ROOT/e['result'];assert sha(p)==e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(p.read_bytes());validate(r);passed=r['gate_return_code']==0
    memory=r['memory']+r['PS_checkpoints'];status='CLOSED_M420_LAYERS12_13_FIXED_FEATURE_SCREEN_PASS' if passed else 'CLOSED_M420_ORIGINAL_COMBINATION_FAILURE'
    v=dict(status=status,raw_sha256=e['sha256'],gate_return_code=r['gate_return_code'],build_id=r['build_id'],phase=r['phase'],errors=r['errors'],selected_layers=r['selected_layers'],
        actual_visual_forward_calls=r['visual_forward_calls'],actual_language_forward_calls=r['language_forward_calls'],numerical_pass=r['numerical_pass'],feature_quality_pass=r['feature_quality_pass'],
        full_visual_quality=r.get('full_visual_quality'),actual_changed_layer13_input=r.get('layer13_input_changed'),software_PL_complete_features_exact=r.get('software_PL_complete_features_exact',False),
        original_visual=r.get('original_visual'),software_visual=r.get('software_visual'),candidate_visual=r.get('candidate_visual'),local_quality=r.get('local_quality'),
        retained_visual_features=r.get('retained_visual_features',[]),board_result_directory='/home/ubuntu/m420_combination_visual_02',full_wire_batches=r.get('full_wire_reference_batches_exact',0),
        physical_transactions=r['physical_transactions_started'],PL_rows=len(r['PL_rows']),allocations=len(r['allocations']),releases=len(r['releases']),main_DMA_payload_bytes=3440656,
        minimum_CmaFree_MiB=min((x['CmaFree']/2**20 for x in memory),default=None),minimum_MemAvailable_MiB=min((x['MemAvailable']/2**20 for x in memory),default=None),maximum_RSS_growth_MiB=max((x['RSS_growth_bytes']/2**20 for x in memory),default=None),
        safe_buffers_released=r['safe_buffers_released'],unsafe_retained=r['unsafe_dma_buffers_retained'],PS_owner_closed=r['PS_owner_closed'],bindings_restored=r['bindings_restored'],DMA_allocator_restored=r['DMA_allocator_restored'],stable_restored=r['stable_restored'],
        semantic_accuracy_proven=False,performance_claim=False,expanded_24_layers=False,production_changed=False,replayed_for_collection=False,
        next_concrete_step='Reuse the two retained visual features through the identical original159-token language path; compare full logits/KV and fixed-input decision without rerunning visual. Do not expand beyond12+13.' if passed else 'Debug only the saved current failure level. No expansion, full-model/performance retry or hardware rerun for collection.')
    report=f'# M420 第12＋13层完整视觉质量闭合\n\n{status}，原rc {r["gate_return_code"]}；raw SHA `{e["sha256"]}`。\n\n'
    report+='固定原末帧两个视图。原版A、两层软件量化/FP16/FTZ参考、PL组合各一次；13层的软件参考使用12层替换后实际改变的输入。完整PL包/wire、两个MLP的全部中间输出及最终特征须逐位等于动态软件参考，随后与固定原版作特征筛选。只替换12＋13的四个Linear，Attention/GELU/norm/Merger/其他22层和语言不变。\n\n'
    if v['full_visual_quality']:
        q=v['full_visual_quality'];m=q['metrics'];t=q['thresholds'];report+='|最终98×2560特征指标|实测|原阈值|\n|---|---:|---:|\n'
        for label,k,tk in [('相对L2','relative_l2','maximum_relative_l2'),('整体余弦','cosine','minimum_cosine'),('最低token余弦','min_token_cosine','minimum_token_cosine')]:report+=f'|{label}|{m[k]:.10f}|{t[tk]}|\n'
    report+='\n|生命周期与内存|结果|\n|---|---|\n'
    for k in ('actual_visual_forward_calls','actual_language_forward_calls','actual_changed_layer13_input','software_PL_complete_features_exact','full_wire_batches','physical_transactions','allocations','releases','main_DMA_payload_bytes','minimum_CmaFree_MiB','minimum_MemAvailable_MiB','maximum_RSS_growth_MiB','safe_buffers_released','unsafe_retained','PS_owner_closed','bindings_restored','DMA_allocator_restored','stable_restored'):report+=f'|{k}|{v[k]}|\n'
    report+='\n七块3,440,656B原DMA重复用于两层，分配后封锁新增；无固定64MiB CMA floor，原普通PS768MiB增长预算＋64MiB普通可用余量保持。逐边界观察不是连续native峰值或任意输入长期认证。\n\n这只是固定输入特征数值筛选，没有语言/logits/最终判定或独立标签准确率证据。三次前向含软件参考和诊断，不能作为视觉/请求性能比较。第13层单MLP30.65%、第12层单MLP31.93%和旧语言40.81%各自保持原范围，不能相加成完整请求收益。\n\n'
    if r['errors']:report+='原失败：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+v['next_concrete_step']+'\n'
    out=BASE/'runs/M420-combination-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m420_combination_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],feature_quality_pass=v['feature_quality_pass'],semantic_accuracy_proven=False,performance_pass=False,expanded_24_layers=False),f'## M420 仅两层完整视觉质量闭合（2026-10-06）\n\nSHA {sha(out)}；raw {e["sha256"]}保留，{status}。实际视觉{v["actual_visual_forward_calls"]}/语言{v["actual_language_forward_calls"]}，全部wire {v["full_wire_batches"]}、物理{v["physical_transactions"]}、分配/释放{v["allocations"]}/{v["releases"]}，稳定恢复{v["stable_restored"]}；最低CMA {v["minimum_CmaFree_MiB"]}MiB仅记录。固定原版特征筛选{v["feature_quality_pass"]}，未证明语义准确率/请求收益或24层。下一步 {v["next_concrete_step"]}')
    print('M420_CLOSURE_SYNC',sha(out),status)
if __name__=='__main__':main()
