"""Prospective one-shot full-request kernel comparison; no hardware action."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    b=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior={}
    for k in ('latest_m441_fixed_video_board','latest_m441_fixed_video_closure','latest_m441_board_compare','latest_m441_kernel_switch_component','latest_m437_natural_IO_protocol'):
        e=b[k];assert w.sha(w.ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prior[k]=e
    old=(w.ROOT/prior['latest_m437_natural_IO_protocol']['result']).with_name('PROTOCOL.json')
    assert w.sha(old)==prior['latest_m437_natural_IO_protocol']['protocol_sha256']
    p=json.loads(old.read_bytes())
    p.update(schema='m441-same-late11-kernel-complete-request-v09',prerequisites=prior,scope='M357-versus-M441-both-late13-through23-visual',measurement_question='Does the new record pipeline reduce complete fixed159 requests under the same accepted visual policy?',supersedes_protocol_sha256=w.sha(old),expected_total_physical=12813)
    p['variants']={'A':{'build_id':'0x4D333537','visual_layers':list(range(13,24))},'B':{'build_id':'0x4D343431','visual_layers':list(range(13,24))}}
    p['kernel_transitions']=dict(initial_build='0x4D343431',initial_minimal=1,order='ABBAABBABAAB',expected_switches=8,expected_switch_minimals=8,full4096_output_and_Build_idle_required=True,original_seven_owners_retained=True,additional_DMA=0,environment_preflight_before_every_overlay=True,all_switching_and_proofs_outside_request_timer=True,programming_failure_retains_owners=True)
    p['measurement'].update(both_variants_same_accepted_visual_language_reference=True,loaded_resident_runtime=True,overlay_programming_included=False,legal_minimal_included=False,all_vision_staging_language_parsing_head_included=True)
    p['runtime_conditions']['identical_source_asset_storage_threads_CPU_policy_PL_clocks']=True
    p['request_accounting']=dict(each_language_logical=778,each_language_physical=781,each_visual_physical=286,requests=12,expected_formal=8,expected_primer=4,all_endpoint_hashes_after_timer=True)
    p['unchanged_optimizations']=dict(selected_visual_layers=list(range(13,24)),PS_prefetch=False,parser_workers=1,last_layer_tail=False,SiLU_workspace=False)
    p['excluded_interpretations']=['cold-start or Overlay-load latency','long-term unattended service stability','automatic promotion','pure PL compute time']
    out=w.BASE/'runs/M441-complete-request-protocol-09'
    atomic(out/'PROTOCOL.json',w.encoded(p),immutable=True)
    report='''# M441 同视觉路径的完整请求性能协议

A为原M357，B为新M441；双方均采用已接受的后11层视觉MLP PL路径、原159-token末帧两视图和单输出，单parser／预读关闭。只比较硬件核组织的增量收益。

同一完整runtime和七DMA驻留：4次ABBA预处理后固定8次ABBABAAB正式。每次778逻辑、781语言及286视觉物理；初始合法minimal和8次核切换minimal在请求计时之外，总预期12813物理。每次切换前确认原owner、全部异步任务和DMA完成；同root/XRT/package环境预检、七缓冲身份保持、新Build及4096B全输出证明后才进入请求。失败保留原owner，不强杀或另起实验。

主指标是原stream的complete.total_ms；完整视觉、权重读取/暂存、CPU运算、语言设备事务、解析和LM head在原边界内。LM head含在Prefill，不重复相加。切换及模型构造不含在计时内，所以结论仅是驻留请求，不是冷启动。

固定自然缓存，无清缓存/强制预载。全部八正式样本保留，实际I/O、fault、缓存、内存及环境前后记录，不以读盘量排除样本或事后匹配。双方同样在计时后核对完整特征、72KV、151936logits和物理序列；这可能影响后续缓存，不能直接声称长期服务稳定。

ABBA和BAAB两组平均收益均>0，四个预定A−B配对差95%区间下界>0才通过；否则结束该实验，不加测。预算3600秒，每请求240秒；超限不kill活动资源。不测温、不增加DMA/PS槽、不改生产。完整原字节及三记录闭合后独立裁决。
'''
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    r=dict(status='FROZEN_M441_SAME_VISUAL_FULL_REQUEST_PROTOCOL09',protocol_sha256=w.sha(out/'PROTOCOL.json'),source_sha256=w.sha(w.HERE/'m441_performance_protocol09.py'),prerequisites=prior,board_run=False,performance_pass=False,maximum_requests=12,expected_physical=12813)
    atomic(out/'RESULT.json',w.encoded(r),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_complete_request_protocol',dict(result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,**r),f'## M441 同视觉完整请求性能协议09（2026-10-09）\n\nSHA {d}，协议{r["protocol_sha256"]}；A原M357/B新M441均M437后11层视觉、原单parser/无预读，同驻留七DMA。固定ABBA四预处理＋ABBABAAB八正式，自然I/O全样本、原stream边界、完整数值在计时外。8次切换与全输出minimal在计时外，预期12813物理；同环境/owner/Build检查，失败保留。双组正与配对95%下界正判据，不加测/生产，尚未性能执行。')
    print(r['status'],d,r['protocol_sha256'])

if __name__=='__main__':main()
