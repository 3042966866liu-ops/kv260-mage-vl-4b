"""Prepare same-input video reference/contract only. No board or model execution."""
import ast
import copy
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m397_last_layer_tail_scope import call_plan

def main():
    prerequisites={
        'text':('runs/M401-tail-text-closure-02/RESULT.json','0e3e6e2241fec9fb520f2334a84006b11991f052d58165f28c367506c25b914b'),
        'reference':('runs/M398-tail-reference-board-01/BOARD_RESULT.json','ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'),
        'layer':('runs/M400-tail-layer-board-02/BOARD_RESULT.json','bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c')}
    records={}
    for k,(rel,digest) in prerequisites.items():
        assert sha(BASE/rel)==digest
        records[k]=json.loads((BASE/rel).read_bytes())
    assert all(prerequisites['text'][1] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    assert records['text']['fixed_text_numerical_pass'] and records['text']['seven_original_DMA_released'] and records['text']['stable_overlay_restored']
    old=records['reference'];assert old['status']=='PASS_M398_ORIGINAL_TAIL_REFERENCE' and old['gate_return_code']==0
    layer=records['layer'];assert layer['status']=='PASS_M400_TAIL_LAYER_NUMERICAL' and layer['gate_return_code']==0
    pinpath=BASE/'candidates/M401-tail-text-02/TAIL_LAYER_PREREQUISITE.json'
    pin=json.loads(pinpath.read_bytes());assert pin['raw_sha256']==prerequisites['reference'][1]
    plan=call_plan(159);assert plan==dict(tokens=159,tail_start=128,tail_count=31,original_logical=778,logical=766)
    changed={'attention_out','gate_up','mlp_down'}
    candidate=copy.deepcopy(old['video_result'])
    for i,row in enumerate(candidate['families']):
        if row['layer']==35 and row['family'] in changed:
            candidate['families'][i]=copy.deepcopy(next(f for f in pin['expected_families'] if f['family']==row['family']))
    assert candidate['families'][-4:]==layer['layer_result']['families']
    assert candidate['keys'][35]==layer['layer_result']['key'] and candidate['values'][35]==layer['layer_result']['value']
    # Original completion order puts the last31 scale record at index3; the
    # existing on-board isolated layer proves exactly these retained records.
    scales=[];launches=[]
    for row in candidate['scale_attempts']:
        if row['layer']==35 and row['family'] in changed:
            if not any(s['layer']==35 and s['family']==row['family'] for s in scales):
                retained=next(s for s in pin['expected_scale_attempts'] if s['family']==row['family'])
                scales.append(copy.deepcopy(retained))
        else:scales.append(row)
    for row in old['transactions']:
        if row['layer']==35 and row['family'] in changed:
            if not any(s['layer']==35 and s['family']==row['family'] for s in launches):
                launches.append(copy.deepcopy(next(t for t in pin['expected_transactions'] if t['family']==row['family'])))
        else:launches.append(copy.deepcopy(row))
    language=sum(len(s['attempted_shifts'])-1 for s in scales if s['layer'] is not None)
    head=sum(len(s['attempted_shifts'])-1 for s in scales if s['layer'] is None)
    assert len(scales)==766 and language==1 and head==0 and len(launches)==767
    chains=pin['chains'];removed_logical_macros=4*sum(c['expected_macros'] for c in chains if c['family'] in changed)
    removed_retry_macros=2*next(c['expected_macros'] for c in chains if c['family']=='mlp_down')
    candidate.update(scale_attempts=scales,logical_calls=766,host_calls=767,retry_count=1,retry_launches=1,nonfinite_detections=1,language_retries=1,head_retries=0,
        logical_expected_macros=candidate['logical_expected_macros']-removed_logical_macros,expected_macros=candidate['expected_macros']-removed_logical_macros-removed_retry_macros)
    # Honest candidate metadata; original reference/proof keeps its 778 calls.
    proof=candidate['semantic']['proof']
    for key in ('pl_logical_chain_calls','expected_pl_logical_chain_calls'):assert proof[key]==778;proof[key]=766
    proof['pl_expected_macros']=candidate['logical_expected_macros']
    assert candidate['stage_bytes']==old['video_result']['stage_bytes']==2034890752
    assert candidate['logits']==old['reference_capture']['fixtures']['logits']['tensor']
    budgetpath=BASE/'candidates/M401-tail-text-02/VIDEO_BUDGET.json';budget=json.loads(budgetpath.read_bytes())
    assert budget['full_video_PS_growth_limit_bytes']==1024<<20 and budget['MemAvailable_margin_bytes']==64<<20
    assert budget['extra_explicit_CMA_after_original7_buffers_bytes']==0
    # Pin the actual stream rather than silently substituting fake counters.
    source=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'
    text=source.read_text(encoding='utf-8');tree=ast.parse(text)
    assert 'expected_calls = _server.expected_physical_calls(len(ids), 1)' in text
    assert 'call_delta == expected_calls and macro_delta > 0' in text
    stream_rule=dict(actual_stream_source_sha256=sha(source),original_expected_calls=778,candidate_expected_calls=766,
        isolated_adapter_required=True,adapter_scope='Only exact159/one-token original-count778, under this candidate scope and execution lock; return derived766. Unexpected arguments/source/count refuse. Restore binding before cleanup.',
        real_board_evidence_unchanged=True,no_fake_counter_offsets=True,
        required_checks='Exercise actual frozen stream with explicit CPU fake inputs/counters before Overlay; reject wrong build/call/macros, stale scope and missing restore. Independently compare all767 physical rows and scale records.')
    out=BASE/'runs/M402-tail-video-contract-01'
    atomic(out/'EXPECTED_VIDEO.json',encoded(dict(original_reference_sha256=prerequisites['reference'][1],derived_candidate_not_board_result=True,baseline=candidate,transactions=launches)),immutable=True)
    value=dict(status='PREPARED_FIXED159_TAIL_VIDEO_REFERENCE_AND_BUDGET_ONLY',prerequisites={k:dict(result=rel,sha256=h) for k,(rel,h) in prerequisites.items()},
        call_plan=plan,expected_video_sha256=sha(out/'EXPECTED_VIDEO.json'),expected_model_physical_if_same_retained_retry=767,total_with_minimal_if_same_retained_retry=768,
        removed_logical_calls=12,removed_retry_launches=2,removed_logical_macros=removed_logical_macros,removed_retry_macros=removed_retry_macros,
        staging_bytes_unchanged=2034890752,expected_language_retries=language,expected_head_retries=head,changed_family_count=3,full_family_count=154,
        full_KV_count=72,full_logits=151936,original_last_frame_two_views=True,temporal_four_frame_understanding=False,
        budget_sha256=sha(budgetpath),budget=budget,stream_rule=stream_rule,
        source_sha256=sha(HERE/'m402_prepare_contract.py'),numerical_pass=False,performance_pass=False,board_run=False,
        next_step='Implement default-off independent video package/actual-stream count adapter and strict reference collector; test resource ownership and actual collect destination/sync key before any upload. No new baseline/reference forward needed.')
    atomic(out/'RESULT.json',encoded(value),immutable=True);h=sha(out/'RESULT.json')
    report=f'''# M402 固定159视频参考与容量合同准备

前级固定文本原SHA `{prerequisites['text'][1]}` 已闭合。复用原M398同输入参考及M400单层结果，不重跑参考、画像或旧性能对照。

固定原最后帧两224视图、98视觉token、159语言token、原提示与权重；完整36层K/V及151936 logits。前三十五层、末层完整QKV/Attention和全部K/V保持；末层后三投影只保留128..158。原154个family中仅三个输入/输出参考换为已捕获和单层验证的31行，最终判断与logits参考保持。

逻辑778→766，少12次T32提交。参考中被省略的末层mlp_down首批有两次重试，保留部分预期仍有一次语言重试：模型物理781→767，同Overlay最小事务后总768。这是从原记录推导的严格候选合同，尚无新视频实测。匹配记录之外的重试变化需调查，不能把推导当实际PASS。权重暂存保持2,034,890,752B。

实际M276 stream仍按原 expected_physical_calls 算778；新隔离入口必须显式绑定仅159/单token的766合同，并保留真实计数、宏数、全部物理事务和反例检查，退出恢复绑定。不能使用假counter偏移或修改生产入口以通过旧检查。新适配器尚未实现。

复用原视频容量预算，不使用30-token预算：已知数组/临时项合计458,266,144B并非同时峰值；native workspace预留268,435,456B；完整诊断普通RSS增长预算1GiB、剩余预算外MemAvailable64MiB。七原DMA已分配后封锁新增DMA，阶段及提交前检查CMA调用计数。原生产64MiB政策不改，20ms采样不是瞬时峰值证明。

计划文件SHA `{h}`，预计结果SHA `{value['expected_video_sha256']}`。只准备参考与预算；视频包、CPU实际stream适配验证、上传和数值执行尚未完成，性能未解锁。
'''
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m402_tail_video_contract',dict(status=value['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,numerical_pass=False,performance_pass=False),
        f'## M402 固定159视频参考/预算合同准备（2026-10-04）\n\n{h}；复用同输入M398/M400参考，778→766逻辑，匹配保留重试下781→767模型物理加minimal768，权重暂存保持2034890752B。完整72KV/151936logits/视觉/判断保持，三个末层31行family参考推导。复用真实视频1GiB+64MiB普通内存预算，封锁额外DMA，生产政策保持。实际M276 stream原778合同需要独立有界适配及实际CPU拒绝/恢复检查；尚未实现视频包/上传/执行，无视频或性能PASS。')
    print(json.dumps(dict(status=value['status'],sha256=h,logical=766,physical_expected_not_measured=767,board_run=False)))

if __name__=='__main__':main()
