"""Saved-only final interpretation of combination-feature language consistency."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m421_workflow import check,PKG

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m421_saved_language_board'];p=ROOT/e['result']
    assert sha(p)==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=check(json.loads(p.read_bytes()));passed=r['status']=='PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY';plan=json.loads((PKG/'PLAN.json').read_bytes())
    status='CLOSED_M421_LAYERS12_13_ONE_INPUT_DECISION_CONSISTENCY_PASS' if passed else 'CLOSED_M421_COMBINATION_LANGUAGE_FAILURE'
    v=dict(status=status,raw_sha256=e['sha256'],gate_return_code=r['gate_return_code'],errors=r['errors'],selected_layers=[12,13],saved_feature_source_sha256=plan['M420_raw_sha256'],
        original_reference_pass=r.get('original_reference_pass',False),fixed_input_decision_consistency_pass=passed,actual_visual_forward_calls=r.get('vision_forward_calls',0),actual_language_forward_calls=r['model_forward_calls'],prompt_tokens=len(r.get('prompt_token_ids',[])),output_budget=r.get('output_budget'),decode_calls=r.get('decode_calls',0),
        logit_comparison=r.get('logit_comparison'),per_variant=[dict(variant=s['variant'],logical_calls=s['counts']['logical_calls'],physical_calls=s['counts']['host_calls'],language_retries=s['counts']['language_retries'],head_retries=s['counts']['head_retries'],decision=s['decision'],logits=s['logits']) for s in r.get('samples',[])],
        retained_board_logits=r.get('logit_files',[]),physical_transactions=r['fpga_transactions'],original_seven_DMA_payload_bytes=sum(x['bytes'] for x in r['allocated_buffers']),allocations=len(r['allocated_buffers']),releases=len(r['released_buffers']),safe_buffers_released=r.get('safe_buffers_released',False),unsafe_buffers_retained=r['unsafe_buffers_retained'],stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),
        board_result_directory='/home/ubuntu/m421_saved_feature_language_01',dataset_accuracy_proven=False,object_category_or_location_quality_proven=False,motion_direction_quality_proven=False,performance_proven=False,expanded_24_layers=False,production_changed=False,
        next_concrete_step='Prepare a bounded balanced complete-request comparison of fixed original versus layers12+13. Keep this quality result separate from performance; do not expand layers or promote service before full-request benefit and admission are verified.' if passed else 'Debug only the saved-feature language failing level; collection failure means original byte recovery only, no visual/hardware replay or expansion.')
    report=f'# M421 第12＋13层保存特征语言质量闭合\n\n{status}，原raw SHA `{e["sha256"]}`，rc {r["gate_return_code"]}。\n\n'
    report+='复用M420已保存原版和两层候选98×2560特征，各接相同原M238/M241与0x4D333537并行核。159-token提示、末帧两视图、权重、单token输出和原缩放重试保持；没有重算视觉。原版须逐位核对全部151936 logits、72KV、154family及事务/重试；候选完整有限输出及固定输入判定一致，距离只记录，不拟合阈值。\n\n'
    if v['logit_comparison']:
        q=v['logit_comparison'];report+='|指标|原版|12＋13候选|\n|---|---:|---:|\n'
        for label,k in [('判定','verdict'),('token','token_id'),('刀具分数（未校准）','knife_score'),('yes−no logit','logit_margin_yes_minus_no')]:report+=f'|{label}|{q["original"][k]}|{q["candidate"][k]}|\n'
        report+='\n|全词表比较|结果|\n|---|---:|\n'
        for k in ('full_logits_bit_equal','changed_FP32_words','relative_l2','cosine','RMSE','max_abs','knife_score_delta'):report+=f'|{k}|{q[k]}|\n'
    report+='\n|变体|逻辑|物理|语言重试|head重试|\n|---|---:|---:|---:|---:|\n'
    for s in v['per_variant']:report+=f'|{s["variant"]}|{s["logical_calls"]}|{s["physical_calls"]}|{s["language_retries"]}|{s["head_retries"]}|\n'
    report+=f'\n实际视觉 {v["actual_visual_forward_calls"]}次、语言 {v["actual_language_forward_calls"]}次、总物理事务 {v["physical_transactions"]}；七块原DMA {v["original_seven_DMA_payload_bytes"]}B，分配/释放{v["allocations"]}/{v["releases"]}，安全释放{v["safe_buffers_released"]}，稳定bit恢复{v["stable_overlay_reloaded"]}。原固定64MiB CMA floor未用于独立诊断；封锁新增DMA，普通PS1024MiB增长及64MiB普通余量保留。恢复Overlay初始DMASR0仅从未提交事务，不能当作已完成稳定DMA证明。\n\n'
    report+='这是单份固定输入的原版/候选判定一致性，没有独立标注准确率、对象类别/位置或时序方向覆盖。诊断含大量哈希和输出记录，不提供新的视觉或完整请求耗时收益；旧语言40.81%与各单MLP收益不能相加。\n\n'
    if r['errors']:report+='原失败：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report+='下一步：'+v['next_concrete_step']+'\n'
    out=BASE/'runs/M421-saved-language-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m421_saved_language_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],decision_consistency_pass=passed,accuracy_proven=False,performance_pass=False,expanded_layers=False),f'## M421 两层保存特征语言质量闭合（2026-10-06）\n\nSHA {sha(out)}；raw {e["sha256"]}保留，{status}。0视觉重算，原参考{v["original_reference_pass"]}、159固定输入判定一致性{passed}，七DMA分配/释放{v["allocations"]}/{v["releases"]}，稳定bit恢复{v["stable_overlay_reloaded"]}；非独立准确率/性能/24层/生产晋级。下一步{v["next_concrete_step"]}')
    print('M421_CLOSURE_SYNC',sha(out),status)
if __name__=='__main__':main()
