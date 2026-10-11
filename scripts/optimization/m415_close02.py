"""Read and close the one saved-feature language quality run, no UART."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m415_workflow04 import check
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());row=board['latest_m415_saved_feature_language_board'];path=ROOT/row['result']
    assert sha(path)==row['sha256'] and all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=check(json.loads(path.read_bytes()));passed=r['status']=='PASS_M415_SAVED_FEATURE_DECISION_CONSISTENCY'
    if passed:assert r['decision_consistency_pass'] and r['original_reference_pass'] and r['safe_buffers_released'] and r['stable_overlay_reloaded']
    status='CLOSED_M415_ONE_INPUT_SAVED_FEATURE_DECISION_CONSISTENCY_PASS' if passed else 'CLOSED_M415_SAVED_FEATURE_LANGUAGE_FAILURE'
    q=r.get('logit_comparison');samples=r.get('samples',[])
    v=dict(status=status,raw_sha256=row['sha256'],gate_return_code=r['gate_return_code'],build_id=r['build_id'],errors=r['errors'],
        original_reference_pass=r.get('original_reference_pass',False),fixed_input_decision_consistency_pass=passed,
        saved_visual_feature_source_sha256='5733f75049b8bee7aae6da9d8a1cdc451416a637d5a4e7b28c617aa767043408',
        actual_visual_forward_calls=r.get('vision_forward_calls',0),actual_language_forward_calls=r['model_forward_calls'],
        prompt=r.get('prompt'),prompt_tokens=len(r.get('prompt_token_ids',[])),output_budget=r.get('output_budget'),decode_calls=r.get('decode_calls',0),
        selected_layers=[12],selected_frame_indices=[3],views=2,logit_comparison=q,
        per_variant=[dict(variant=s['variant'],logical_calls=s['counts']['logical_calls'],physical_calls=s['counts']['host_calls'],language_retries=s['counts']['language_retries'],head_retries=s['counts']['head_retries'],decision=s['decision'],logits=s['logits']) for s in samples],
        retained_board_logits=r.get('logit_files',[]),board_result_directory='/home/ubuntu/m415_saved_feature_language_02',
        original_seven_DMA_payload_bytes=sum(x['bytes'] for x in r['allocated_buffers']),allocations=len(r['allocated_buffers']),releases=len(r['released_buffers']),
        sealed_after_initial_allocation=r.get('additional_cma_requests_allowed') is False,
        safe_buffers_released=r.get('safe_buffers_released',False),unsafe_buffers_retained=r['unsafe_buffers_retained'],
        stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),stable_restore_transaction_submitted=r.get('stable_restore_transaction_submitted'),
        stable_reload_note='Pinned original stable bit SHA and reload verified; initial DMASR0 at reloaded Overlay is never-submitted lifecycle, not completed stable DMA proof',
        dataset_accuracy_proven=False,object_category_or_spatial_location_quality_proven=False,motion_direction_quality_proven=False,
        performance_proven=False,expanded_layers=False,production_source_changed=False,
        next_concrete_step='Keep fixed original A as reference. Prepare one additional FP32-layer MLP contract and local A8 screen, then a small combination against original; no all24 expansion and no accuracy/performance claim from one input.' if passed else 'Debug only saved-feature language failing level; do not repeat visual or hardware for collection, no expansion.')
    report='# M415 保存视觉特征接原语言路径质量闭合\n\n'+status+'，原SHA `'+row['sha256']+'`。\n\n'
    report+='复用M414板端两份98×2560 FP32特征，原版和第12层候选各接同一M238/M241语言和并行PL核0x4D333537。提示、159-token IDs、权重、时间戳3.0和单token输出保持，0视觉重算、0Decode。原版必须逐位复现旧全部logits/72KV/154family及事务/重试；候选完整有限输出，比较全词表并核对受限刀具判定。\n\n'
    if q:
        report+='|指标|原版|第12层候选|\n|---|---:|---:|\n'
        for label,key in [('判定','verdict'),('token','token_id'),('刀具分数（未校准）','knife_score'),('yes−no logit','logit_margin_yes_minus_no'),('全词表argmax','full_vocabulary_argmax_token_id')]:
            report+=f'|{label}|{q["original"][key]}|{q["candidate"][key]}|\n'
        report+='\n|全部151936 logits比较|结果|\n|---|---:|\n'
        for label,key in [('逐位相同','full_logits_bit_equal'),('不同FP32字数','changed_FP32_words'),('相对L2','relative_l2'),('余弦','cosine'),('RMSE','RMSE'),('最大绝对差','max_abs'),('刀具分数差','knife_score_delta')]:report+=f'|{label}|{q[key]}|\n'
    report+='\n|变体|逻辑调用|物理调用|语言重试|head重试|\n|---|---:|---:|---:|---:|\n'
    for s in v['per_variant']:report+=f'|{s["variant"]}|{s["logical_calls"]}|{s["physical_calls"]}|{s["language_retries"]}|{s["head_retries"]}|\n'
    report+='\n判定一致只证明本份末帧两个视图输入的原版/候选一致性，没有独立标注的准确率或类别/位置覆盖。运动方向需要时序信息，未拿来裁决这条末帧路径。logits距离只完整记录，没有看到结果后调阈值；全部时间含诊断不构成新性能比较。\n\n'
    report+=f'原七块DMA载荷 {v["original_seven_DMA_payload_bytes"]} B；分配/释放 {v["allocations"]}/{v["releases"]}；安全释放 {v["safe_buffers_released"]}；稳定bit恢复 {v["stable_overlay_reloaded"]}。原64MiB固定CMA门槛未用于诊断准入，普通PS增长预算1024MiB加64MiB普通可用余量不变。恢复稳定Overlay后的DMASR0属于尚未提交事务的生命周期，不能称为稳定DMA已完成证明。两份logits留在板端结果目录，SHA见原raw，没有为补收集重新执行硬件。\n\n'
    if r['errors']:report+='失败原文：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+v['next_concrete_step']+'\n'
    out=BASE/'runs/M415-saved-feature-language-closure-02/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m415_saved_feature_language_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=row['sha256'],decision_consistency_pass=passed,accuracy_proven=False,performance_pass=False,expanded_layers=False),
         f'## M415 保存特征语言质量闭合（2026-10-06）\n\nSHA {sha(out)}，raw {row["sha256"]}保留，{status}。实际视觉{v["actual_visual_forward_calls"]}次/语言{v["actual_language_forward_calls"]}次，同159提示及单token；原版参考{v["original_reference_pass"]}，固定输入判定一致性{passed}，7DMA分配/释放{v["allocations"]}/{v["releases"]}，稳定bit恢复{v["stable_overlay_reloaded"]}。非独立标注准确率/类别位置/时序方向/性能/扩层，下一步{v["next_concrete_step"]}。')
    print('M415_CLOSURE_SYNC',sha(out),status)
if __name__=='__main__':main()
