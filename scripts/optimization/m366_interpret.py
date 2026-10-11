"""Adjudicate a saved fixed-text result; never execute or repeat hardware."""
import json
import m351_workflow as w


def main():
    path=w.BASE/'runs/M366-staged-text-board-01/BOARD_RESULT.json'
    r=json.loads(path.read_text(encoding='utf-8'));digest=w.sha(path)
    b=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert b['latest_m366_staged_layer_board']['sha256']==digest
    assert all(digest in (w.ROOT/name).read_text(encoding='utf-8') for name in ('CURRENT_STATE.md','docsMILESTONES.md'))
    passed=r['status']=='PASS_M366_FIXED_TEXT_DIAGNOSTIC'
    admission=next((x for x in r.get('stage_memory',[]) if x['label']=='diagnostic-admission-after-seven-real-buffers'),None)
    extrema=r.get('sampled_memory',{}).get('extrema')
    if passed:
        assert r['numerical_pass'] and not r['unsafe_buffers_retained'] and not r['errors'] and r['safe_buffers_released']
        assert len(r['allocated_buffers'])==len(r['released_buffers'])==7
        assert r['released_buffers']==list(reversed(r['allocated_buffers']))
        assert all(r['exact_comparison'].values()) and r['layer_result']['token']==17
    result=dict(status='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' if passed else 'STOP_AT_INDEPENDENT_FIXED_TEXT_DIAGNOSTIC',build_id=r['build_id'],raw_sha256=digest,gate_return_code=r['gate_return_code'],raw_status=r['status'],errors=r['errors'],admission=admission,sampled_memory=r.get('sampled_memory'),production_policy_changed=False,production_threshold_would_admit=r.get('production_threshold_would_admit'),numerical_pass=r['numerical_pass'],actual_video_tested=False,exact_native_peak_proven=False,performance_pass=False,promoted=False,allocation_count=len(r['allocated_buffers']),release_count=len(r['released_buffers']),next_step='Only after this scope PASS derive real159-video visual and language budgets and freeze the exact old video/reference; no performance gate.' if passed else 'Debug only the preserved fixed-text failure level; no video/higher gate and no hardware rerun for collection.')
    lines=['# M366 独立固定文本容量诊断','',f'候选 Build `{r["build_id"]}`，原返回码 `{r["gate_return_code"]}`，裁决 **{r["status"]}**。','',
        '原30-token固定文本，完整36层与LM head，完整原runtime对象保留。生产64MiB门槛不变；七缓冲分配后禁止额外PYNQ分配。当前未执行视觉forward、真实视频、decode或整体性能对照。','',
        f'原证据 `{path.relative_to(w.ROOT).as_posix()}`，SHA-256 `{digest}`。','',f'实际分配 {result["allocation_count"]} 块；已记录释放 {result["release_count"]} 块。']
    if admission:
        m=admission['memory']
        lines+=['',f'准入 CmaFree `{m["system_bytes"]["CmaFree"]/(1<<20):.6f} MiB`，MemAvailable `{m["system_bytes"]["MemAvailable"]/(1<<20):.6f} MiB`；原生产门槛会否放行 `{result["production_threshold_would_admit"]}`。']
    if extrema:
        lines+=['','| 20ms采样观测 | MiB |','|---|---:|',f'| 最低CmaFree | {extrema["min_cma"]/(1<<20):.6f} |',f'| 最低MemAvailable | {extrema["min_available"]/(1<<20):.6f} |',f'| 最大RSS | {extrema["max_rss"]/(1<<20):.6f} |',f'| 整个进程VmHWM | {extrema["max_hwm"]/(1<<20):.6f} |','','短峰可能漏过；VmHWM包含整个加载过程，不能称为精确文本或原生总峰值。']
    if passed:
        x=r['layer_result']
        lines+=['',f'154个语言family输入/输出、151936 logits、36K/36V以及缩放重试、全部权重字节和macros均与冻结稳定M344参考逐位一致。Token `{x["token"]}`，逻辑调用 `{x["logical_calls"]}`，物理调用 `{x["host_calls"]}`，另有合法同Overlay最小事务1次。','',
            '观察器已结束；原pack/parse执行器退出后，七缓冲严格逆序各释放一次。最终候选DMA/AP状态核对、稳定Overlay重载、boot/cmdline身份保持；稳定重载后未提交事务，初始DMA0不作为已完成事务空闲证明。','',
            '本次证明这一独立固定文本路径在观测容量条件下可运行；不能推断真实视频的视觉懒缓存/恢复权重/特征及159-token KV峰值已满足，也不能声称完整请求提速。']
    else:lines+=['','未通过本级，不进入视频。',*[f'- {e}' for e in r['errors']],'',f'活动或未知缓冲保留 `{r["unsafe_buffers_retained"]}`；原字节收集问题只修回收，不重复硬件。']
    out=w.BASE/'runs/M366-staged-text-closure-01'
    w.atomic(out/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    result['report_sha256']=w.sha(out/'REPORT.md');w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);final_sha=w.sha(out/'RESULT.json')
    w.sync('latest_m366_staged_text_closure',dict(status=result['status'],sha256=final_sha,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),raw_sha256=digest),f'## M366 独立固定文本诊断闭合\n\nBuild{r["build_id"]}，{result["status"]}，原rc{r["gate_return_code"]}；数值PASS={r["numerical_pass"]}，分配{result["allocation_count"]}/释放{result["release_count"]}。只原30-token/36层/head及72KV，完整对象保留；生产64MiB不改，20ms采样非精确原生峰值，无视频/整体性能/晋级。原SHA `{digest}`，闭合SHA `{final_sha}`。{result["next_step"]}')
    print(json.dumps(result))


if __name__=='__main__':main()
