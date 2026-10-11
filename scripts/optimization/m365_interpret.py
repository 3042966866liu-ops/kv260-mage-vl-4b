"""Adjudicate only the immutable, already collected independent layer result."""
import json
import m351_workflow as w


def main():
    path=w.BASE/'runs/M365-staged-layer-board-01/BOARD_RESULT.json'
    r=json.loads(path.read_text(encoding='utf-8'))
    digest=w.sha(path)
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m365_staged_layer_board']['sha256']==digest
    assert all(digest in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    passed=r['status']=='PASS_M365_SINGLE_LAYER_DIAGNOSTIC'
    rows=r.get('stage_memory',[])
    admission=next((x for x in rows if x['label']=='diagnostic-admission-after-seven-real-buffers'),None)
    extrema=r.get('sampled_memory',{}).get('extrema')
    if passed:
        assert r['numerical_pass'] and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
        assert len(r['allocated_buffers'])==len(r['released_buffers'])==7
        assert not r['sampled_memory']['stop_reason'] and r['sampled_memory']['observer_stopped']
        assert all(r['exact_comparison'].values()) and r['stable_overlay_reloaded']
    result=dict(
        status=('PASS_ONE_LAYER_UNDER_INDEPENDENT_POLICY' if passed else 'STOP_AT_INDEPENDENT_SINGLE_LAYER_DIAGNOSTIC'),
        build_id=r['build_id'], raw_sha256=digest, raw_status=r['status'], gate_return_code=r['gate_return_code'],
        errors=r['errors'], numerical_pass=r['numerical_pass'],
        production_threshold_would_admit=r.get('production_threshold_would_admit'),
        admission=admission, sampled_extrema=extrema,
        sampler=r.get('sampled_memory'),
        explicit_allocated_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
        allocation_count=len(r['allocated_buffers']), release_count=len(r.get('released_buffers',[])),
        original_64mib_production_policy_changed=False,
        additional_explicit_pynq_allocations_allowed=False,
        exact_native_peak_proven=False, actual_video_input=False,
        full_model_capacity_proven=False, performance_pass=False, promotion=False,
        next_step=('Derive a separate fixed-text full-layer/head PS budget and numerical reference before a new package/run; video remains unopened.' if passed else 'Keep this failed diagnostic level; inspect the preserved error and lifecycle without repeating completed gates or starting fixed text/video.'),
    )
    def mib(x):return f'{x/(1<<20):.6f}'
    lines=['# M365 独立单层容量诊断结果','',
        f'候选 Build `{r["build_id"]}`，原始返回码 `{r["gate_return_code"]}`，结果 **{r["status"]}**。',
        '', '本次保留完整原运行时对象，但推理范围只有 layer 0；输入是 159 行重复固定文本 embedding，尚未执行真实视频、视觉 forward、LM head 或完整模型。生产入口与其 64 MiB CMA 门槛保持。','',
        f'原始证据：`{path.relative_to(w.ROOT).as_posix()}`，SHA-256 `{digest}`。','',
        f'实际缓冲分配 {result["allocation_count"]} 块，合计 {result["explicit_allocated_bytes"]} B；已记录释放 {result["release_count"]} 块。']
    if admission:
        m=admission['memory']; d=admission['admission']
        lines += ['', '| 单层准入时 | MiB |','|---|---:|',
            f'| CmaFree | {mib(m["system_bytes"]["CmaFree"])} |',
            f'| MemAvailable | {mib(m["system_bytes"]["MemAvailable"])} |',
            f'| 进程 RSS | {mib(m["process_bytes"]["VmRSS"])} |',
            f'| 普通内存准入预算 | {mib(d["required_mem_available_bytes"])} |',
            '', f'原生产门槛会否放行：`{r.get("production_threshold_would_admit")}`。独立入口在七块缓冲成功后封锁额外 PYNQ 分配，检查普通 PS 增长预算及 CMA API 计数；不能将这次独立准入推广到生产入口。']
    if extrema:
        lines += ['', '| 单层监测值 | MiB |','|---|---:|',
            f'| 最低 CmaFree | {mib(extrema["min_cma"])} |',
            f'| 最低 MemAvailable | {mib(extrema["min_available"])} |',
            f'| 最大 RSS | {mib(extrema["max_rss"])} |',
            f'| 整个进程 VmHWM | {mib(extrema["max_hwm"])} |',
            '', '采样间隔为 20 ms，可能漏过短峰；VmHWM 包含此前加载，不能视为精确单层峰值。']
    if passed:
        layer=r['layer_result']
        lines += ['', f'五个 family 的全部输出、hidden、K/V 及缩放重试记录均与冻结稳定参考一致。逻辑调用 {layer["logical_calls"]} 次，物理调用 {layer["host_calls"]} 次，另有同 Overlay 最小事务 1 次。',
            '', '已核对候选最终 AP/DMA 状态、七缓冲逆序各释放一次和稳定 Overlay 重载。稳定重载后未提交恢复事务，DMASR=0 只表示新实例尚未提交事务。',
            '', '本结果只回答这次单层路径是否能运行。如果原生产门槛拒绝而独立单层通过，可以说明门槛挡住了这一有限路径；尚不能说明完整文本或视频没有内存问题。下一阶段须先核算完整 36 层 KV 与 LM head 的普通内存需求，冻结独立准入和全部数值参考，再扩展验证。']
    else:
        lines += ['', '本次没有通过单层诊断，保留失败阶段和原返回码，不进入固定文本或视频。', '', '错误：', *[f'- {x}' for x in r['errors']], '', f'活动或未知缓冲保留：`{r["unsafe_buffers_retained"]}`。回收失败只修复原结果收集，不能重跑硬件掩盖错误。']
    out=w.BASE/'runs/M365-staged-layer-closure-01'
    w.atomic(out/'REPORT.md', ('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    result['report_sha256']=w.sha(out/'REPORT.md')
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True)
    closure_sha=w.sha(out/'RESULT.json')
    w.sync('latest_m365_staged_layer_closure',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=closure_sha,raw_sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),
        f'## M365 独立单层裁决闭合\n\nBuild{r["build_id"]}，{result["status"]}，原rc{r["gate_return_code"]}，数值通过={r["numerical_pass"]}；只159重复文本输入的一层及完整对象保留，非实际视频/完整模型。实际{result["allocation_count"]}缓冲，释放{result["release_count"]}；生产64MiB保持，20ms采样非精确原生峰值。02作用域遮蔽在首次执行前修复于03，旧02只传输不执行。原SHA `{digest}`，闭合SHA `{closure_sha}`。{result["next_step"]}')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
