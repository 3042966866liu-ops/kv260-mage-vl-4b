"""Interpret the already collected balanced board comparison; no board calls."""
import json
import m351_workflow as w
base=w.BASE
path=base/'runs/M357-compare-board-01/BOARD_RESULT.json'
assert w.sha(path)=='ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'
r=json.loads(path.read_text(encoding='utf-8'))
assert r['status']=='PASS_M357_COMPARE' and r['chain_performance_pass'] and r['stable_restored']
c=r['comparison'];a=c['original_median_ns']/1e6;b=c['candidate_median_ns']/1e6
out=path.parent/'INTERPRETATION.json'
v=dict(status='PASS_REPRESENTATIVE_Q_CHAIN_ONLY',build_id='0x4D333537',stable_build_id='0x4D395832',
 raw_sha256=w.sha(path),original_ms=[x/1e6 for x in c['original_ns']],candidate_ms=[x/1e6 for x in c['candidate_ns']],
 original_median_ms=a,candidate_median_ms=b,speed_ratio=a/b,latency_reduction_fraction=c['gain_fraction'],
 output_bytes_each=524288,balanced_orders=r['balanced_orders'],all_eight_outputs_bitwise_exact=True,
 actual_ps_clocks_equal=c['same_observed_ps_clocks'],boundary=c['boundary'],pure_compute=False,
 full_model_proven=False,video_proven=False,promoted=False,stable_restored=True,
 candidate_change='Four private readonly activation/scale banks; unchanged arithmetic, descriptor, weight and merge organization.',
 next_step='Independent complete-runtime capacity prerequisite, then single-layer, fixed-text and fixed159-video numerical gates before full-request performance.')
w.atomic(out,w.encoded(v),immutable=True);digest=w.sha(out)
note=f'## M357 代表性Q链上板交错收益成立（2026-10-02）\n\n候选Build0x4D333537，稳定0x4D395832；A-B-B-A/B-A-A-B各4次，8份524288B输出逐位一致。原版中位{a:.6f}ms，候选{b:.6f}ms，耗时减少{100*c["gain_fraction"]:.4f}%，比值{a/b:.4f}；实际PS时钟相同。边界为S2MM提交前至AP_DONE及两DMA空闲，排除Overlay/暂存/pack/输出同步哈希，非纯计算或完整请求提速。54块拥有缓冲安全释放，稳定Overlay恢复；boot/DTB/CMA/服务未改。原始证据 `{path.relative_to(w.ROOT).as_posix()}` SHA `{w.sha(path)}`；解读SHA `{digest}`。仅单chain，无全模型/视频或晋级；下一步完整runtime实际容量前置，再单层/固定文本/159视频数值。'
w.sync('latest_m357_chain_comparison',dict(status=v['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),note)
report=base/'M356_RTL_SHARD_OVERLAP_INVESTIGATION.md'
text=report.read_text(encoding='utf-8')
text=text.replace('COM3已实际确认ubuntu shell，但一次`sudo -n true`返回rc1要求密码，尚未上传bootstrap/候选，没有Overlay或FPGA事务。等待用户同终端sudo-v及回shell/关闭PuTTY确认后，才按BuildID→descriptor→chain→ABBABAAB比较执行；每级原字节收集与三份记录同步后再解锁下一级。','首次sudo授权检查rc1已保留。用户续期后同COM3 sudo-n确认rc0，整包传输及临时地址恢复通过。普通用户bash-n被root-only目录拒绝rc126，尚无Overlay；随后仅修控制端为root语法检查，包及权限不改，失败证据保留。BuildID、descriptor、chain及ABBABAAB对照已依次通过并同步。')
text=text.replace('当前没有新候选板端提速、稳定性或晋级结论。先前完整runtime的CMA失败仍独立有效；单链收益成立后，完整模型/视频还须独立容量与数值门禁，不能用本次静态实现或空闲内存代替。','新候选目前具有代表性Q单链板端收益，尚无完整模型/视频或晋级结论。先前完整runtime的CMA失败仍独立有效；完整模型/视频还须独立容量与数值门禁，不能用本次静态实现或空闲内存代替。')
if digest not in text:
 text+='\n## 实际板端交错对照（2026-10-02）\n\n'+note.split('\n\n',1)[1]+'\n\n| 对照 | 四次耗时(ms) |\n|---|---|\n| 原版A | '+', '.join(f'{x:.6f}' for x in v['original_ms'])+' |\n| 候选B | '+', '.join(f'{x:.6f}' for x in v['candidate_ms'])+' |\n\n单descriptor输出262144B、Q整chain输出524288B、合法零事务4096B均完整比较。最终AP_CTRL=4，两DMASR=4098无错误，返回稳定Build0x4D395832。实现资源URAM64/64、DSP1184/1248；整机WNS+0.082837738ns/WHS+0.010186963ns，未提高时钟。\n'
w.atomic(report,text.encode('utf-8'))
print(json.dumps(v))
