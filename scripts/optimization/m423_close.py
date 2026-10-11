"""Interpret only synchronized, saved M423 evidence; never operate the board."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m423_workflow02 import check, PKG


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m423_integrated_board']
    p = ROOT/e['result']
    assert sha(p) == e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
               for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    r = check(json.loads(p.read_bytes()))
    plan = json.loads((PKG/'PLAN.json').read_bytes())
    passed = r['status'] == 'PASS_M423_INTEGRATED_VIDEO_NUMERICAL'
    status = ('CLOSED_M423_INTEGRATED_LAYERS12_13_NUMERICAL_PASS' if passed
              else 'CLOSED_M423_INTEGRATED_VIDEO_FAILURE')
    next_step = (
        'Freeze one bounded warm complete-request performance protocol and lightweight measurement entry. '
        'Keep original versus layers12+13 inputs, cache policy and timing boundaries identical; '
        'no additional layers or production promotion.' if passed else
        'Debug only this integrated numerical level after interpreting the saved failure. '
        'Collection failure requires recovery of existing bytes, never a hardware replay.')
    v = dict(
        status=status, raw_sha256=e['sha256'], build_id=r['build_id'],
        gate_return_code=r['gate_return_code'], errors=r['errors'], selected_layers=[12,13],
        visual_reference_raw_sha256=plan['M420_raw_sha256'],
        integrated_sources_checked_before_overlay=r.get('integrated_sources_checked_before_overlay',False),
        visual_forward_calls=r.get('vision_forward_calls',0),
        language_forward_calls=r.get('model_forward_calls',0), decode_calls=r.get('decode_calls',0),
        prompt_tokens=len(r.get('prompt_token_ids',[])), output_budget=r.get('output_budget'),
        computed_visual=r.get('integrated_visual',[]),
        exact_saved_reference_comparisons=r.get('integrated_exact_comparisons',[]),
        logit_comparison=r.get('logit_comparison'),
        per_variant=[dict(variant=s['variant'],counts=s['counts'],decision=s['decision'])
                     for s in r.get('samples',[])],
        visual_transactions=len(r.get('visual_transactions',[])),
        visual_staging_bytes=sum(x['bytes'] for x in r.get('visual_staging',[])),
        physical_transactions=r['fpga_transactions'],
        language_physical_transactions=r.get('host_calls',0),
        original_seven_DMA_payload_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
        allocations=len(r['allocated_buffers']), releases=len(r['released_buffers']),
        borrowed_extra_DMA=r.get('borrowed_extra_DMA'),
        borrowed_buffer_identity_preserved=r.get('borrowed_buffer_identity_preserved',False),
        visual_static_cache_invalidated=r.get('visual_static_cache_invalidated',False),
        visual_provider_disposed=r.get('visual_provider_disposed',False),
        safe_buffers_released=r.get('safe_buffers_released',False),
        unsafe_buffers_retained=r['unsafe_buffers_retained'],
        stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),
        memory_checkpoints=[dict(label=x['label'],rss_bytes=x['memory']['process_bytes']['VmRSS'],
                                cma_free_bytes=x['memory']['system_bytes']['CmaFree'],
                                mem_available_bytes=x['memory']['system_bytes']['MemAvailable'])
                            for x in r.get('stage_memory',[])],
        per_request_sampled_memory=[s['sampled_memory'] for s in r.get('samples',[])],
        numerical_pass=passed, fixed_input_decision_consistency_pass=passed,
        dataset_accuracy_proven=False, performance_proven=False,
        expanded_24_layers=False, production_changed=False, next_concrete_step=next_step)
    report = '# M423 第12＋13层完整视觉—语言接入闭合\n\n'
    report += f'{status}，原raw SHA `{e["sha256"]}`，rc {r["gate_return_code"]}。\n\n'
    report += ('原版与候选各实际执行预处理、完整视觉和原语言/LM head。仅候选第12、13层的两个MLP Linear使用并行PL；'
               'Attention、GELU、归一化、语言量化及重试保持。输入仍为原四帧来源的末帧两视图、159 token和单token输出。\n\n'
               '与M420保存特征及M421保存语言结果逐位核对；原版和候选分别核对全部视觉特征、151936 logits、'
               '72份K/V、154个family及事务/重试。这是各变体接入前后的一致性，不要求量化候选与原版逐位相同。\n\n')
    report += '|变体|语言逻辑|语言物理|语言重试|head重试|判定|\n|---|---:|---:|---:|---:|---|\n'
    for s in v['per_variant']:
        c=s['counts']
        report += f'|{s["variant"]}|{c["logical_calls"]}|{c["host_calls"]}|{c["language_retries"]}|{c["head_retries"]}|{s["decision"]["verdict"]}|\n'
    report += (f'\n实际视觉/语言 {v["visual_forward_calls"]}/{v["language_forward_calls"]}次；'
               f'视觉事务{v["visual_transactions"]}、视觉权重暂存{v["visual_staging_bytes"]}B，'
               f'总物理事务{v["physical_transactions"]}（包含合法最小事务）。'
               f'原七块DMA {v["original_seven_DMA_payload_bytes"]}B，分配/释放{v["allocations"]}/{v["releases"]}，'
               f'额外DMA {v["borrowed_extra_DMA"]}；借用身份保持{v["borrowed_buffer_identity_preserved"]}，'
               f'静态寄存器缓存失效{v["visual_static_cache_invalidated"]}，provider释放{v["visual_provider_disposed"]}，'
               f'安全缓冲释放{v["safe_buffers_released"]}，稳定bit恢复{v["stable_overlay_reloaded"]}。\n\n')
    report += ('独立诊断没有固定64MiB CMA floor，新增DMA封锁及普通PS内存预算保留，生产入口未改。'
               '稳定Overlay恢复后的DMASR0只表示未提交事务，不是完成稳定DMA的证明。\n\n'
               '诊断哈希、完整数值记录不用于性能裁决。此结果只覆盖固定输入一致性，'
               '没有独立标注准确率或新的完整请求提速结论；没有扩大到24层或接入稳定服务。\n\n')
    if r['errors']:
        report += '原失败：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n\n'
    report += '下一步：'+next_step+'\n'
    out = BASE/'runs/M423-integrated-closure-01/RESULT.json'
    atomic(out,encoded(v),immutable=True)
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m423_integrated_closure',dict(
        status=status,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),
        raw_sha256=e['sha256'],build_id=r['build_id'],numerical_pass=passed,
        performance_pass=False,expanded_layers=False),
        f'## M423 两层完整视觉—语言接入闭合（2026-10-06）\n\nSHA {sha(out)}；raw {e["sha256"]}保留，'
        f'{status}，Build {r["build_id"]}。实际视觉/语言{v["visual_forward_calls"]}/{v["language_forward_calls"]}，'
        f'视觉物理{v["visual_transactions"]}，七DMA分配/释放{v["allocations"]}/{v["releases"]}，'
        f'额外DMA{v["borrowed_extra_DMA"]}，稳定bit恢复{v["stable_overlay_reloaded"]}。'
        f'无性能/独立标注准确率/24层/生产晋级。下一步：{next_step}')
    print('M423_CLOSURE_SYNC',sha(out),status)


if __name__ == '__main__':
    main()
