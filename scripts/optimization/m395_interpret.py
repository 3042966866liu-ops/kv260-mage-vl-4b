"""Saved-only complete request verdict; keep conservative original criterion."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m381_interpret import compare

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));e=b['latest_m395_silu_performance_board'];p=ROOT/e['result'];d=sha(p)
    assert d==e['sha256'] and all(d in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(p.read_text(encoding='utf-8'));ok=r['status']=='PASS_M395_LIGHT_VIDEO_MEASUREMENTS'
    overall={};orders={};criterion={};benefit=False
    if ok:
        assert r['numerical_pass'] and not r['gate_return_code'] and not r['errors'] and len(r['samples'])==8 and r['order']=='ABBABAAB'
        overall=compare(r['samples']);orders=dict(ABBA=compare(r['samples'][:4]),BAAB=compare(r['samples'][4:]))
        t=overall['total_ms'];gain=min(x['total_ms']['saved_ms'] for x in orders.values());variation=max(t['A']['range_ms'],t['B']['range_ms']);separation=t['A']['minimum_ms']-t['B']['maximum_ms']
        criterion=dict(min_order_mean_saved_ms=gain,max_within_variant_range_ms=variation,minimum_A_minus_maximum_B_ms=separation,
                       order_gain_exceeds_within_range=gain>variation,all_A_slower_than_all_B=separation>0)
        benefit=gain>variation and separation>0
    status=('PASS_FIXED_VIDEO_SILU_WORKSPACE_NET_BENEFIT' if benefit else 'CLOSED_SILU_WORKSPACE_NET_BENEFIT_UNPROVEN') if ok else 'STOP_SILU_PERFORMANCE_AT_RECORDED_FAILURE'
    next_step='Keep isolated candidate only for this fixed request; production admission and bounded continuous-request lifecycle need independent evidence before service integration' if benefit else ('Close this SiLU variant; retain component/numeric evidence, keep original expression. No arbitrary array/worker scan or unchanged full request rerun' if ok else 'Stop at recorded failure; saved recovery only')
    value=dict(status=status,raw_sha256=d,build_id='0x4D333537',numerical_pass=ok,performance_pass=benefit,formal_promotion_allowed=False,stable_service_changed=False,
               production_admission_changed=False,historical_hardware_40_81_percent_unchanged=True,original_parser_workers=1,PS_prefetch=False,order=r.get('order'),overall=overall,orders=orders,
               conservative_check=criterion,measurement_scope=r.get('measurement_scope'),samples=r.get('samples',[]),errors=r['errors'],exact_native_peak_proven=False,next_step=next_step)
    out=BASE/'runs/M395-silu-performance-closure-01';atomic(out/'RESULT.json',encoded(value),immutable=True);h=sha(out/'RESULT.json')
    lines=['# SiLU工作缓冲：本轮完整验证与请求对照','',f'裁决：**{status}**。','',
           '两组都是并行核 Build0x4D333537、原单解析 worker、原固定159-token视频（最后帧两视图，decode=0）。A保留原 `silu(gate) * up`，B仅使用一个5.900390625MiB普通FP32工作缓冲，按原取负、exp、加法、除法、乘法顺序使用out；gate/up保持不变。PS权重预读和双解析worker关闭、没有新增DMA。','',
           '此前硬件调整的约40.81%完整请求降幅是独立已验证结论。本轮板端真实输入组件约10.48%的运算延迟下降，也是组件结论；两者都不能替代下面的完整请求裁决。','',
           '组件、单层、固定30-token文本和原159-token视频数值门禁逐级完成。原36层、151936logits、72份K/V、视觉输出、受限判断、778逻辑/781物理及三次保护重试均核对，工作缓冲、绑定/owner、七原DMA安全释放，结束恢复稳定Overlay。','']
    if ok:
        t=overall['total_ms'];lines += [f'八次完整请求均值：A {t["A"]["mean_ms"]/1000:.6f}s，B {t["B"]["mean_ms"]/1000:.6f}s，均值差 {t["saved_ms"]/1000:.6f}s（{t["reduction_percent"]:.4f}%）。均值差只作描述，沿用既有保守判据裁决净收益。','',
                   '| 组 | A均值s | B均值s | 均值差s | 降幅% |','| --- | --- | --- | --- | --- |']
        for name,v in orders.items():
            t=v['total_ms'];lines.append(f'| {name} | {t["A"]["mean_ms"]/1000:.6f} | {t["B"]["mean_ms"]/1000:.6f} | {t["saved_ms"]/1000:.6f} | {t["reduction_percent"]:.4f} |')
        lines +=['',f'两组顺序的最小均值差：{criterion["min_order_mean_saved_ms"]/1000:.6f}s；全部A/B样本中最大组内范围：{criterion["max_within_variant_range_ms"]/1000:.6f}s；A最小减B最大：{criterion["minimum_A_minus_maximum_B_ms"]/1000:.6f}s。最小顺序差超过组内范围且A最小仍大于B最大，两项都成立才记稳定净收益。没有统计总体置信区间。','',
                  '| 次序 | 变体 | 请求s | 首tokens | 视觉s | Prefill含heads | heads | 实际读盘MiB |','| --- | --- | --- | --- | --- | --- | --- | --- |']
        for s in r['samples']:
            t=s['timing'];g=t['stages_ms'];lines.append(f'| {s["index"]} | {s["variant"]} | {t["total_ms"]/1000:.6f} | {t["first_token_ms"]/1000:.6f} | {g["vision"]/1000:.6f} | {g["prefill"]/1000:.6f} | {g["head"]/1000:.6f} | {s["io_delta"]["read_bytes"]/2**20:.6f} |')
        lines +=['','Prefill含head，两列不能相加。B的源码身份核对/绑定、工作缓冲创建、36次借用、完成屏障及安全关闭包含在原请求和Prefill计时内。资产校验/Overlay构造、完整数值哈希和导出位于计时外。100ms内存监控和两组相同的物理调用观察保留。单独每次SiLU耗时、各次分配/关闭耗时未记录，不能由完整请求差值反推。','',
                  '原视觉懒缓存预先构造一次（26项/66,699,264B），未清文件缓存；实际读盘逐次列出。既有缓存策略相同不代表驻留相同；不称为冷启动、任意提示词或时序四帧收益。八次完整数值均在计时后检查，6256次物理事务完成，七DMA每次逆序释放与五个owner覆盖绑定恢复。','']
    else:lines+=['未完成全部请求数值/生命周期，停止解释性能；错误：'+json.dumps(r['errors'],ensure_ascii=False),'']
    lines+=['生产64MiB准入、稳定服务/rollback/boot/DTB/CMA保持。独立封锁新增DMA的诊断使用1GiB普通RSS停止预算和64MiB普通余量；采样/检查点不是精确瞬时峰值、长期服务或泄漏证明。没有正式接入服务或晋级。','', '下一步：'+next_step+'。','',f'原始SHA `{d}`；解读SHA `{h}`。','']
    atomic(out/'REPORT.md','\n'.join(lines).encode('utf-8'),immutable=True)
    summary=f'A {overall["total_ms"]["A"]["mean_ms"]/1000:.6f}s/B {overall["total_ms"]["B"]["mean_ms"]/1000:.6f}s，描述差{overall["total_ms"]["reduction_percent"]:.4f}%' if ok else '未完成全部请求'
    sync('latest_m395_silu_performance_closure',dict(status=status,sha256=h,result=(out/'RESULT.json').relative_to(ROOT).as_posix(),raw_sha256=d,numerical_pass=ok,performance_pass=benefit,formal_promotion_allowed=False),
         f'## M395 SiLU完整请求裁决（2026-10-04）\n\n原SHA {d}，闭合SHA {h}；{summary}；裁决{status}，判据{json.dumps(criterion)}。同并行Build/原单parser、原159视频，A原表达式/B5.900390625MiB普通工作缓冲，ABBABAAB，绑定/分配/关闭含原计时，完整数值计时后核对。PS预读/双parser关闭，原生产准入/服务/回滚不改，稳定Overlay恢复，旧硬件40.81%独立保持；无正式晋级。下一步{next_step}。')
    print(json.dumps(dict(status=status,sha256=h,overall=overall,orders=orders,conservative_check=criterion,report=str(out/'REPORT.md'))))

if __name__=='__main__':main()
