"""Saved-only adjudication; no board access and no automatic promotion."""
import json
import sys
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m381_interpret import compare


def assess(samples):
    if len(samples)!=8 or ''.join(s['variant'] for s in samples)!='ABBABAAB':raise ValueError('Balanced8 order required')
    overall=compare(samples);orders=dict(ABBA=compare(samples[:4]),BAAB=compare(samples[4:]))
    t=overall['total_ms'];gain=min(v['total_ms']['saved_ms'] for v in orders.values())
    variation=max(t['A']['range_ms'],t['B']['range_ms']);separation=t['A']['minimum_ms']-t['B']['maximum_ms']
    criterion=dict(min_order_mean_saved_ms=gain,max_within_variant_range_ms=variation,minimum_A_minus_maximum_B_ms=separation,order_gain_exceeds_within_range=gain>variation,all_A_slower_than_all_B=separation>0)
    return overall,orders,criterion,gain>variation and separation>0


def self_test():
    def fixture(values):
        return [dict(index=i+1,variant=v,timing=dict(total_ms=x,first_token_ms=x-1,stages_ms=dict(vision=x*.1,prefill=x*.8,head=x*.1,preprocess=1),initialization_ms=1)) for i,(v,x) in enumerate(zip('ABBABAAB',values))]
    assert assess(fixture([100,80,81,101,80,102,100,81]))[-1]
    assert not assess(fixture([100,99,100,103,97,99,102,101]))[-1]
    assert not assess(fixture([100,99,99,100,103,100,100,103]))[-1]
    try:assess(fixture([1]*7))
    except ValueError:pass
    else:raise AssertionError('Missing trial accepted')
    print('M403_INTERPRET_SELF_TEST_PASS')


def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m403_tail_performance_board'];p=ROOT/e['result']
    assert sha(p)==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(p.read_bytes());ok=r['status']=='PASS_M403_LIGHT_VIDEO_MEASUREMENTS'
    overall=orders=criterion={};benefit=False
    if ok:
        assert not r['errors'] and r['gate_return_code']==0 and r['numerical_pass'] and r['fpga_transactions_total']==6200
        overall,orders,criterion,benefit=assess(r['samples'])
    status=('PASS_FIXED_VIDEO_LAST_LAYER_TAIL_NET_BENEFIT' if benefit else 'CLOSED_LAST_LAYER_TAIL_NET_BENEFIT_UNPROVEN') if ok else 'STOP_LAST_LAYER_TAIL_PERFORMANCE_AT_RECORDED_FAILURE'
    next_step=('Keep isolated fixed-request candidate; independently check production admission and bounded continuous-request lifetime before service integration' if benefit else 'Close this tail variant for deployment; keep numerical evidence and full final layer. No unchanged full request repeat') if ok else 'Stay at recorded failure; saved collection only, no hardware rerun for collection'
    value=dict(status=status,raw_sha256=e['sha256'],build_id='0x4D333537',numerical_pass=ok,performance_pass=benefit,formal_promotion_allowed=False,stable_service_changed=False,production_policy_changed=False,historical_hardware_40_81_percent_unchanged=True,original_parser_workers=1,PS_prefetch=False,SiLU_workspace=False,overall=overall,orders=orders,conservative_check=criterion,samples=r.get('samples',[]),errors=r['errors'],exact_native_peak_proven=False,next_step=next_step)
    out=BASE/'runs/M403-tail-performance-closure-01';atomic(out/'RESULT.json',encoded(value),immutable=True);h=sha(out/'RESULT.json')
    lines=['# 末层后三投影末T32裁剪：完整请求性能对照','',f'裁决：**{status}**。','',
           '同一并行核Build0x4D333537、原单解析worker、原159-token视频。A完整末层；B仅在最后一层完整Attention之后，将attention_out、gate_up、mlp_down限制为原末T32的31个token。前35层、完整最后层QKV/Attention/72KV、LM head保持；PS预读和SiLU工作缓冲关闭。','',
           '已有M402数值PASS独立保持；旧硬件约40.81%完整请求降幅独立保持。本次比较只评价新增末层裁剪。A778逻辑/781模型物理/3语言重试；B766逻辑/767模型物理/1语言重试。四次各一版，ABBABAAB，每次同Overlay合法minimal加1，合计6200物理事务。权重暂存仍为2,034,890,752B。','']
    if ok:
        t=overall['total_ms'];lines += [f'A完整请求均值 {t["A"]["mean_ms"]/1000:.6f}s；B {t["B"]["mean_ms"]/1000:.6f}s；描述均值差 {t["saved_ms"]/1000:.6f}s（{t["reduction_percent"]:.4f}%）。','',
            '| 顺序组 | A均值s | B均值s | 差s | 降幅% |','| --- | --- | --- | --- | --- |']
        for n,o in orders.items():
            t=o['total_ms'];lines.append(f'| {n} | {t["A"]["mean_ms"]/1000:.6f} | {t["B"]["mean_ms"]/1000:.6f} | {t["saved_ms"]/1000:.6f} | {t["reduction_percent"]:.4f} |')
        lines += ['',f'保守判据：两顺序组最小均值差 {criterion["min_order_mean_saved_ms"]/1000:.6f}s，最大组内范围 {criterion["max_within_variant_range_ms"]/1000:.6f}s，A最小减B最大 {criterion["minimum_A_minus_maximum_B_ms"]/1000:.6f}s。两组最小收益超过组内范围，并且所有B快于所有A，两项都成立才记录净收益；没有总体置信区间。','',
            '| 次序 | 版 | 请求s | 首tokens | 视觉s | Prefill含heads | heads | 实际读盘MiB |','| --- | --- | --- | --- | --- | --- | --- | --- |']
        for s in r['samples']:
            t=s['timing'];g=t['stages_ms'];lines.append(f'| {s["index"]} | {s["variant"]} | {t["total_ms"]/1000:.6f} | {t["first_token_ms"]/1000:.6f} | {g["vision"]/1000:.6f} | {g["prefill"]/1000:.6f} | {g["head"]/1000:.6f} | {s["io_delta"]["read_bytes"]/2**20:.6f} |')
        lines += ['','Prefill包含head，两列不能相加。B源码核对/绑定、末层选择、tail关闭在原Prefill/请求计时内；计数绑定恢复在原complete计时内，位于原首token计时结束之后。双方均使用原M276首token与complete边界。完整视觉/输入/151936logits/72KV及重试核对在计时后，未在计时内逐family导出/哈希。','',
            '原视觉懒缓存一次预热26项/66,699,264B；每次新Overlay和原七DMA构造在请求计时外，原PS对象驻留。自然文件缓存未清理，逐次实际读盘列出；同缓存政策不等于同驻留。不称冷启动、任意提示或时序四帧收益。各次绑定开销、纯PL计算周期、前景权重等待和解析等待未单独记录。','']
    else:lines += ['未完成全部请求数值与退出，停止性能解释；错误：'+json.dumps(r['errors'],ensure_ascii=False),'']
    lines += ['生产64MiB准入、稳定服务/rollback/boot/DTB/CMA保持；封锁新增DMA的独立诊断使用1GiB普通RSS增长停止预算及64MiB普通余量，100ms采样不证明瞬时峰值或长期服务稳定。七DMA/owner每次安全关闭，最终稳定Overlay恢复。','', '下一步：'+next_step+'。','',f'原始SHA `{e["sha256"]}`；解读SHA `{h}`。','']
    atomic(out/'REPORT.md','\n'.join(lines).encode('utf-8'),immutable=True)
    detail=f'A {overall["total_ms"]["A"]["mean_ms"]/1000:.6f}s/B {overall["total_ms"]["B"]["mean_ms"]/1000:.6f}s，描述降幅{overall["total_ms"]["reduction_percent"]:.4f}%' if ok else '全部请求未完成'
    sync('latest_m403_tail_performance_closure',dict(status=status,result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,raw_sha256=e['sha256'],numerical_pass=ok,performance_pass=benefit,formal_promotion_allowed=False),f'## M403 末层裁剪完整请求裁决（2026-10-04）\n\n原SHA {e["sha256"]}，闭合SHA {h}；{detail}，裁决{status}，判据{json.dumps(criterion)}。同并行核/单parser、ABBABAAB；PS预读/SiLU关闭、生产政策/服务不变，旧硬件40.81%独立保持。无自动晋级；下一步{next_step}。')
    print(json.dumps(dict(status=status,sha256=h,overall=overall,orders=orders,criterion=criterion,report=str(out/'REPORT.md'))))


if __name__=='__main__':
    if sys.argv[1:]==['SelfTest']:self_test()
    else:main()
