"""Adjudicate all saved PS-pre-read samples with the existing conservative rule."""
import json,statistics
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m381_interpret import compare
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m388_ps_performance_board'];path=ROOT/prior['result'];d=sha(path)
    assert d==prior['sha256'] and all(d in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(path.read_text(encoding='utf-8'));passed=r['status']=='PASS_M388_LIGHT_VIDEO_MEASUREMENTS'
    overall=orders={};conservative={};benefit=False
    if passed:
        assert r['numerical_pass'] and not r['errors'] and not r['performance_pass'] and r['order']=='ABBABAAB' and len(r['samples'])==8
        overall=compare(r['samples']);orders=dict(ABBA=compare(r['samples'][:4]),BAAB=compare(r['samples'][4:]))
        total=overall['total_ms'];within=max(total['A']['range_ms'],total['B']['range_ms']);gain=min(x['total_ms']['saved_ms'] for x in orders.values());separation=total['A']['minimum_ms']-total['B']['maximum_ms'];benefit=gain>within and separation>0
        conservative=dict(min_order_mean_saved_ms=gain,max_within_variant_range_ms=within,minimum_A_minus_maximum_B_ms=separation)
        status='PASS_FIXED_VIDEO_PS_PREFETCH_NET_BENEFIT' if benefit else 'CLOSED_PS_PREFETCH_VARIANT_NET_BENEFIT_UNPROVEN'
    else:status='STOP_PS_PERFORMANCE_AT_RECORDED_FAILURE'
    value=dict(status=status,raw_sha256=d,build_id='0x4D333537',numerical_pass=passed,performance_pass=benefit,formal_promotion_allowed=False,stable_service_changed=False,production_admission_changed=False,historical_hardware40_81_percent_unchanged=True,original_parser_workers=1,order=r.get('order'),measurement_scope=r.get('measurement_scope'),overall=overall,orders=orders,conservative_check=conservative,all_samples=r.get('samples',[]),errors=r['errors'],native_instantaneous_peak_certified=False,next_step='Keep isolated PS candidate for this fixed warm request only; daily-service admission and bounded continuous requests need separate evidence before service integration. Do not add another concurrent variant' if benefit else ('Close PS-pre-read performance variant; keep original staging and one parser. Retain numeric and lifetime evidence; do not scan worker counts or rerun full request without a new specific hypothesis' if passed else 'Stop expansion. Diagnose only recorded capacity/lifecycle/numerical failure at this level; recover saved bytes without repeating hardware'))
    out=BASE/'runs/M388-ps-performance-closure-01';atomic(out/'RESULT.json',encoded(value),immutable=True);closure=sha(out/'RESULT.json')
    lines=['# M388 普通 PS 权重预读完整视频请求对照','',f'裁决：**{status}**。','','两组都是并行核 Build **0x4D333537** 和原单解析 worker。A 为原暂存；B 为已有的一槽普通 PS 预读。原输入、权重、打包、解析、数学和缩放重试保持，零新增 DMA。此前硬件调整的约40.81%完整请求降幅保持独立结论。','']
    if passed:
        t=overall['total_ms'];lines += [f'完整请求均值 A **{t["A"]["mean_ms"]/1000:.3f}s**，B **{t["B"]["mean_ms"]/1000:.3f}s**，平均差 **{t["saved_ms"]/1000:.3f}s（{t["reduction_percent"]:.2f}%）**。', '',f'全部八次 ABBABAAB 样本；两种顺序最小均值差 {conservative["min_order_mean_saved_ms"]/1000:.3f}s，组内最大范围 {conservative["max_within_variant_range_ms"]/1000:.3f}s，A最小值减B最大值 {conservative["minimum_A_minus_maximum_B_ms"]/1000:.3f}s。沿用既有保守标准，前者超过组内范围且后者为正才记净收益成立；没有统计总体置信度，也没有挑最快样本。','', '| 次序 | 变体 | 完整请求s | 首tokens | 视觉s | Prefill含heads | heads |', '| --- | --- | --- | --- | --- | --- | --- |']
        for s in r['samples']:
            t=s['timing'];stage=t['stages_ms'];lines.append(f'| {s["index"]} | {s["variant"]} | {t["total_ms"]/1000:.3f} | {t["first_token_ms"]/1000:.3f} | {stage["vision"]/1000:.3f} | {stage["prefill"]/1000:.3f} | {stage["head"]/1000:.3f} |')
        lines+=['','Prefill已包含head，不能将两列相加。B的slot分配、路径身份检查、worker启动、首窗口等待、前景复制/同步和安全关闭，都发生在原请求/Prefill计时内；计划组装、资产SHA、构造/Overlay初始化和完整数值哈希在计时外。','', '| 次序 | 变体 | 实际磁盘读取MiB | 100ms最大RSS MiB | 最小CmaFree MiB | 最小MemAvailable MiB |', '| --- | --- | --- | --- | --- | --- |']
        for s in r['samples']:
            e=s['sampled_memory']['extrema'];lines.append(f'| {s["index"]} | {s["variant"]} | {s["io_delta"]["read_bytes"]/(1<<20):.3f} | {e["max_rss"]/(1<<20):.3f} | {e["min_cma"]/(1<<20):.3f} | {e["min_available"]/(1<<20):.3f} |')
        lines+=['','每个B请求使用27,852,800B普通PSslot和一个读取worker，162窗口/2,034,890,752B权重暂存；slot/worker/fd/views/session安全释放。每请求完整数值在计时后核对，七DMA逆序释放及五个owner覆盖绑定恢复；原778逻辑/781物理/三次重试及八个head物理观察保持。','', '| B次序 | 读取worker累计s | 主线程等待读取s | 前景复制s | 前景同步s |', '| --- | --- | --- | --- | --- |']
        for s in r['samples']:
            if s['variant']=='B':
                c=s['ps_session']['component'];lines.append(f'| {s["index"]} | {c["read_work_ms"]/1000:.3f} | {c["foreground_wait_ms"]/1000:.3f} | {c["foreground_copy_ms"]/1000:.3f} | {c["foreground_sync_ms"]/1000:.3f} |')
        lines+=['','读取worker累计时间可与PL/PS重叠，不能与请求或Prefill相加，也不能直接当作可节省时间。完整请求差值用于裁决净收益。','']
    else:lines+=['本级未完成全部数值/生命周期门禁，不能解释性能；原失败及错误记录保留：'+json.dumps(r['errors'],ensure_ascii=False),'']
    lines+=['原视觉懒缓存一次预热，26项/66,699,264B；不清文件缓存，逐请求记录实际I/O和缓存状态。这是固定159-token、最后帧两视图、decode=0、原PS缓存已热的对照，不能称为冷启动、时序四帧或任意请求收益。100ms采样不是精确native瞬时峰值或长期泄漏证明。','', '独立诊断保留完整PS对象和封锁额外DMA，普通内存1GiB RSS停止上限包含slot并保留64MiB普通余量。原生产64MiB准入、稳定服务/rollback/boot/DTB/CMA保持，结束恢复稳定Overlay，没有正式晋级。','', '下一步：'+value['next_step']+'。','',f'原始SHA：`{d}`。解读SHA：`{closure}`。','']
    atomic(out/'REPORT.md','\n'.join(lines).encode('utf-8'),immutable=True)
    summary=f'完整请求均值 A {overall["total_ms"]["A"]["mean_ms"]/1000:.3f}s/B {overall["total_ms"]["B"]["mean_ms"]/1000:.3f}s，差{overall["total_ms"]["reduction_percent"]:.2f}%' if passed else '未完成八次，停止扩大'
    sync('latest_m388_ps_performance_closure',dict(status=status,result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=closure,raw_sha256=d,numerical_pass=passed,performance_pass=benefit,formal_promotion_allowed=False),f'## M388 普通PS预读完整请求裁决（2026-10-03）\n\n原SHA {d}，闭合SHA {closure}；{summary}，裁决{status}。两组同Build0x4D333537/原单parser，ABBABAAB，B普通26.5625MiB slot/零新增DMA；计时后完整数值和退出释放。旧硬件40.81%独立结论保持，原生产准入/服务/回滚不变且恢复稳定Overlay，无正式晋级。下一步 {value["next_step"]}。')
    print(json.dumps(dict(status=status,sha256=closure,overall=overall,orders=orders,report=str(out/'REPORT.md'))))
if __name__=='__main__':main()
