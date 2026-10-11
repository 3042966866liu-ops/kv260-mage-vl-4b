"""All samples and both orders; no fastest-sample selection or promotion."""
import json
import statistics as stats
import m351_workflow as w
import m369_collect

def describe(values):
    return dict(n=len(values),mean_ms=stats.mean(values),median_ms=stats.median(values),minimum_ms=min(values),maximum_ms=max(values),range_ms=max(values)-min(values))

def compare(samples):
    result={}
    for metric in ('total_ms','first_token_ms'):
        a=describe([s['timing'][metric] for s in samples if s['variant']=='A'])
        b=describe([s['timing'][metric] for s in samples if s['variant']=='B'])
        result[metric]=dict(A=a,B=b,saved_ms=a['mean_ms']-b['mean_ms'],reduction_percent=100*(a['mean_ms']-b['mean_ms'])/a['mean_ms'],speedup=a['mean_ms']/b['mean_ms'])
    return result

def main():
    path=w.BASE/'runs/M369-light-video-board-01/BOARD_RESULT.json';r=json.loads(path.read_text(encoding='utf-8'))
    assert r['status']=='PASS_M369_LIGHT_VIDEO_MEASUREMENTS' and r['numerical_pass'] and not r['errors']
    digest=w.sha(path)
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m369_light_video_board']['sha256']==digest
    assert all(digest in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    overall=compare(r['samples']);orders=dict(ABBA=compare(r['samples'][:4]),BAAB=compare(r['samples'][4:]))
    total=overall['total_ms']
    max_range=max(total['A']['range_ms'],total['B']['range_ms'])
    order_gain=min(group['total_ms']['saved_ms'] for group in orders.values())
    separation=total['A']['minimum_ms']-total['B']['maximum_ms']
    benefit=order_gain>max_range and separation>0
    out=w.BASE/'runs/M369-light-video-closure-01'
    value=dict(status='PASS_FIXED_VIDEO_WARM_REQUEST_NET_BENEFIT' if benefit else 'CLOSED_PROMOTION_NET_BENEFIT_UNPROVEN',raw_sha256=digest,numerical_pass=True,performance_pass=benefit,formal_promotion_allowed=False,stable_service_changed=False,production64MiB_unchanged=True,scope=r['measurement_scope'],order=r['order'],overall=overall,orders=orders,conservative_check=dict(min_order_mean_saved_ms=order_gain,max_within_variant_range_ms=max_range,minimum_A_minus_maximum_B_ms=separation),native_instantaneous_peak_certified=False,all_samples=r['samples'],next_step='Keep stable rollback and production unchanged; fixed request evidence only, no arbitrary prompt/Web promotion')
    w.atomic(out/'RESULT.json',w.encoded(value),immutable=True);sha=w.sha(out/'RESULT.json')
    rows=[]
    for s in r['samples']:
        t=s['timing'];st=t['stages_ms']
        rows.append(f'| {s["index"]} | {s["variant"]} | {t["total_ms"]/1000:.3f} | {t["first_token_ms"]/1000:.3f} | {st["preprocess"]/1000:.3f} | {st["vision"]/1000:.3f} | {st["prefill"]/1000:.3f} | {st["head"]/1000:.3f} |')
    order_rows=[]
    for name,g in orders.items():
        t=g['total_ms'];order_rows.append(f'| {name} | {t["A"]["mean_ms"]/1000:.3f} | {t["B"]["mean_ms"]/1000:.3f} | {t["saved_ms"]/1000:.3f} | {t["reduction_percent"]:.2f}% |')
    io_rows=[]
    for s in r['samples']:
        x=s['sampled_memory']['extrema']
        io_rows.append(f'| {s["index"]} | {s["variant"]} | {s["io_delta"]["read_bytes"]/(1<<20):.3f} | {x["max_rss"]/(1<<20):.3f} | {x["min_cma"]/(1<<20):.3f} | {x["min_available"]/(1<<20):.3f} |')
    report=f'''# 固定159-token视频正确性与完整请求性能结果

真实视频正确性：通过。候选Build0x4D333537的视觉/154语言输出族/完整151936 logits/72份KV/最终判断和稳定参考一致。性能八次请求也逐次在计时结束后核对视觉、输入、完整logits/KV、判断、实际缩放重试、778逻辑/781物理以及七块缓冲释放。

完整请求平均耗时：稳定版 **{total['A']['mean_ms']/1000:.3f}s**，候选版 **{total['B']['mean_ms']/1000:.3f}s**；减少 **{total['saved_ms']/1000:.3f}s（{total['reduction_percent']:.2f}%）**，约 **{total['speedup']:.3f}×**。

裁决：**{value['status']}**。两种顺序最小均值收益{order_gain/1000:.3f}s；组内最大范围{max_range/1000:.3f}s；所有A最小值与所有B最大值差{separation/1000:.3f}s。使用全部八个样本，不取最快一次。这是有限次数、固定输入的实测，未给出总体统计置信度。

| 次序 | 版本 | 完整请求s | 首tokens | 预处理s | 视觉s | Prefill含heads | heads |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

| 顺序组 | 稳定均值s | 候选均值s | 减少s | 降幅 |
| --- | --- | --- | --- | --- |
{chr(10).join(order_rows)}

第1份稳定请求实际磁盘读取约{r['samples'][0]['io_delta']['read_bytes']/(1<<20):.3f}MiB，后续大多为0或少量；因此第一组包含自然文件缓存差异，不能把第1次与第2次的全部差值归因于核。反向BAAB组同样成立，完整请求降幅{orders['BAAB']['total_ms']['reduction_percent']:.2f}%，更接近后续文件缓存条件下的对照。这个关联不单独证明第1份额外耗时的全部原因。

| 样本 | 版本 | 实际磁盘读取MiB | 100ms最大RSS MiB | 最小CmaFree MiB | 最小MemAvailable MiB |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(io_rows)}

测量边界为原M276已加载runtime的请求，视觉原代码缓存预热一次后保留，两版同一PS对象、线程与测量方式。运行时构造、Overlay加载、发布资产校验以及所有数值SHA在原请求计时之外。Prefill包含head，因此不能把两列相加。两种实现是稳定核A0x4D395832和并行核B0x4D333537；PS权重预取未启用。

第1次完整发布校验/运行时构造记录在前级stages，随后PS预热也另记；样本initialization_ms从已预热PS对象进入该样本设置时开始，后7份包含换核/七缓冲重新构造，不等同于每份完整冷启动时间。系统文件页缓存自然变化，保存各请求前后Cached、CmaFree、RSS、MemAvailable、读I/O、缓存命中；未清缓存，不能把这份结果称为冷启动或任意输入的收益。

容量沿独立诊断规则：原七块CMA缓冲实际分配成功后封锁额外申请，普通PS增长预算及余量监测；没有改变生产64MiB门槛。20/100ms采样和进程HWM不证明全部native瞬时峰值。稳定服务/回滚/boot/DTB/CMA未替换，结束恢复稳定Overlay，未正式晋级。

八份请求中采样RSS逐渐上升，结果只覆盖本次有界实验，不能宣称长期驻留内存已稳定或已确定泄漏/缓存根因。全部事务总数使用原结果fpga_transactions_total={r['fpga_transactions_total']}，即8×(1次同Overlay最小事务+781次原请求物理事务)；顶层fpga_transactions是临时事务列表清空后的最终运行时快照，不能当成全实验总数。

输入是四个源帧中的最后一个源帧的全景/细节两224视图，98视觉token/159语言token，decode=0；不能称为四帧时序理解。

原始性能结果SHA：`{digest}`。
性能解读SHA：`{sha}`。
视频数值前级：M368-video-closure-02，SHA `964b1da3225cec57e21fae109ff7599e225aa221c3f2f11b52c61870e7599acc`。
'''
    w.atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    w.sync('latest_m369_light_video_closure',dict(status=value['status'],sha256=sha,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),raw_sha256=digest,numerical_pass=True,performance_pass=benefit,formal_promotion_allowed=False),f'## M369 完整固定视频交错性能裁决\n\n解读SHA `{sha}`，原SHA `{digest}`；八次ABBABAAB全部数值/事务/释放正确。原已加载暖缓存请求稳定均值{total["A"]["mean_ms"]/1000:.3f}s、候选{total["B"]["mean_ms"]/1000:.3f}s，降{total["reduction_percent"]:.2f}%；裁决{value["status"]}。两种顺序及全部样本保留，未清缓存；非冷启动/任意输入证明，生产64MiB/服务/回滚不变，稳定Overlay恢复，未正式晋级。')
    print(json.dumps(dict(status=value['status'],overall=overall,orders=orders,sha256=sha,report=str(out/'REPORT.md'))))

if __name__=='__main__':main()
