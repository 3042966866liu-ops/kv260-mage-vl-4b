import json
import m351_workflow as w
import m36803_collect

def main():
    log=w.ROOT/'tmp/m368_saved_recovery_01/merged.log'
    digest,raw,r=m36803_collect.decode(log.read_text(encoding='utf-8'))
    path=w.BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json'
    assert digest==w.sha(path)=='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf'
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m368_staged_layer_board']['sha256']==digest
    assert all(digest in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    out=w.BASE/'runs/M368-video-closure-02'
    value=dict(status='PASS_INDEPENDENT_VIDEO_CAPACITY_AND_NUMERICS',raw_status=r['status'],raw_sha256=digest,raw_result=path.relative_to(w.ROOT).as_posix(),build_id=r['build_id'],numerical_pass=True,actual_fixed159_video_completed=True,logical_calls=778,physical_calls=781,total_including_same_overlay_minimal=782,language_retries=3,head_retries=0,full_exact_comparison=r['exact_comparison'],visual_exact_comparison=r['visual_exact_comparison'],semantic=r['video_result']['semantic'],loaded_capacity=r['loaded_capacity'],sampled_memory=r['sampled_memory'],buffer_bytes=[b['bytes'] for b in r['allocated_buffers']],extra_CMA_bytes=0,safe_buffers_released=True,stable_overlay_reloaded=True,production64MiB_unchanged=True,production_gate_would_admit=False,native_peak_certified=False,performance_pass=False,formal_promotion_allowed=False,prior_rejected_loader_attempt_sha256='ccdb2d478c5b0f586fca1bc2869f304a2b5b7d5ec52df60113034ec120af19fa',next_step='Freeze balanced light original request timing, then one ABBABAAB run; no production promotion')
    w.atomic(out/'RESULT.json',w.encoded(value),immutable=True);sha=w.sha(out/'RESULT.json')
    extrema=r['sampled_memory']['extrema']
    report=f'''# M368 固定159-token真实视频正确性闭合

候选核0x4D333537完成原视频请求。视觉特征/预处理/token ID、154 family、完整151936 logits、36份K和36份V、所有缩放重试与最终判断逐位/逐字段和原稳定参考一致。

- 原输入：四源帧只选择最后帧，两224视图，98视觉token，159语言token；decode=0。
- 778逻辑/781物理，3语言保护重试、0head重试；加同Overlay合法最小事务共782。
- 最终token15/文本0/ABSENT，score={r['video_result']['semantic']['token']['knife_score']}。
- 原七块缓冲共33,484,832B，额外CMA0；七块逆序安全释放、稳定核重载、boot/cmdline不变。
- 完整加载后CmaFree={r['loaded_capacity']['cma_free_bytes']/(1<<20):.6f}MiB。20ms采样最小CMA={extrema['min_cma']/(1<<20):.6f}MiB、最大RSS={extrema['max_rss']/(1<<20):.6f}MiB、最小MemAvailable={extrema['min_available']/(1<<20):.6f}MiB。

这是独立固定输入诊断入口的完成证据，七块实际分配后封锁额外CMA；没有修改生产64MiB门槛。低CMA统计值不等于4GB耗尽，实际采样也不证明任意输入/native瞬时峰值或生产稳定性。

全程423.700秒包括加载、哈希和数值观察，不能用作正常请求速度。下一步以原请求计时做ABBABAAB交错对照，哈希仅在计时结束后执行。

原始结果SHA：`{digest}`。
解读SHA：`{sha}`。
首次错误是观察器提前改发布身份，已在实际原加载检查级修复并验证；本次成功原结果的串口缺失/截断142块只补取保存字节，未硬件重跑。
'''
    w.atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    w.sync('latest_m368_video_closure',dict(status=value['status'],sha256=sha,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),raw_sha256=digest,numerical_pass=True,performance_pass=False),f'## M368 真实视频数值与独立容量闭合\n\n解读SHA `{sha}`，原SHA `{digest}`；候选0x4D333537实际固定159视频完整视觉/154family/151936logits/72KV/判断全部同参考。778逻辑781物理、3语言重试、额外CMA0、七块逆序释放/稳定重载。20ms最小CMA{extrema["min_cma"]/(1<<20):.6f}MiB，说明固定诊断可完成，非生产64MiB/任意输入/native峰值证明。下一步只轻量ABBABAAB完整原请求对照；性能未测，未晋级。')
    print(json.dumps(dict(status=value['status'],sha256=sha)))

if __name__=='__main__':main()
