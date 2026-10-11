"""Interpret recovered original-reference bytes only. Never accesses the board."""
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m398_collect import PKG,validate_capture

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    evidence=board['latest_m398_tail_reference_board'];raw=ROOT/evidence['result']
    assert sha(raw)==evidence['sha256']
    assert all(evidence['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(raw.read_text(encoding='utf-8'));expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    if r['status']!='PASS_M398_ORIGINAL_TAIL_REFERENCE' or r['gate_return_code']:
        raise RuntimeError('Only saved failure recovery/debug at this level; no next gate')
    assert r['video_result']==expected and r['reference_capture_pass'] and not r['tail_candidate_executed'] and not r['candidate_numerical_pass']
    validate_capture(r,expected)
    assert all(r['exact_comparison'].values()) and all(r['visual_exact_comparison'].values())
    assert r['scope_weakref_dead'] and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert r['original_buffer_release_count']==7 and r['stable_overlay_reloaded'] and r['patch_registry_cleared']
    assert r['video_result']['logical_calls']==778 and r['video_result']['host_calls']==781 and r['fpga_transactions']==782
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert r['manifest_sha256']==sha(PKG/'PACKAGE_MANIFEST.json')
    assert r['common_runner_sha256']==sha(PKG/'m398_tail_reference_gate.py')
    assert all(sha(PKG/f['path'])==f['sha256'] and (PKG/f['path']).stat().st_size==f['bytes'] for f in m['files'])
    value=dict(status='PASS_ORIGINAL_TAIL_REFERENCE_ONLY',build_id=r['build_id'],raw_result=evidence['result'],raw_sha256=evidence['sha256'],
               manifest_sha256=r['manifest_sha256'],fixture_manifest=r['reference_capture'],logical_calls=778,physical_model_calls=781,
               total_physical_calls_with_minimal=782,retry_count=r['video_result']['retry_count'],last_layer=35,original_tail_start=128,tail_tokens=31,
               original_full_video_numerical_pass=True,candidate_tail_executed=False,candidate_numerical_pass=False,performance_pass=False,
               output_logit_count=151936,KV_arrays=72,seven_original_DMA_released=True,capture_owner_and_callbacks_released=True,
               stable_restored=True,production_policy_unchanged=True,source_sha256=sha(HERE/'m398_close_reference.py'),
               next_gate='Three independent original last31 family chains using captured inputs and outputs; stop on any failure before isolated layer.',
               future_reference_rule='Before and after use: verify raw SHA, exact manifest, each NPY full-file SHA, dtype/shape/tensor SHA and unchanged file identity. No trust in path alone.',
               timing_interpretation='Full numerical capture includes observations and serialization; not a new speed result.')
    out=BASE/'runs/M398-tail-reference-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);digest=sha(out)
    c=r['reference_capture']
    report='''# M398 原末层参考捕获闭合

这是原计算路径的参考捕获，末层裁剪候选尚未执行，不能计为新增加速。

同一固定159-token视频、最后帧两视图、原提示词与量化策略，Build 0x4D333537；完整36层、154个family、778次逻辑调用、781次模型物理调用（3次缩放重试），加最小事务共782次。完整视觉特征、语言各family、151936个logits、72份K/V及Token15/ABSENT判断与已有参考精确一致。

只增加观察与保存：末层35的完整Attention输出/原残差、后三个投影的原末批31输入输出、最终hidden末批、norm和logits，共12项NPY。三观察调用剥离后AST等于冻结原M241；捕获中原算法、运算顺序、全159计算保持。每项保存后重新核对tensor与原数组及文件SHA；元数据通过回收检查。后级仍需在使用前后核对实际板端文件，路径本身不构成身份依据。

| 参考文件 | FP32尺寸 | 文件字节 | 原token起点 |
|---|---|---:|---:|
'''
    for name,f in c['fixtures'].items():report+=f"| {name}.npy | {'×'.join(map(str,f['tensor']['shape']))} | {f['file_bytes']} | {f['original_token_start']} |\n"
    report+=f'''\n总文件字节 {c['file_bytes']}，限制16MiB。捕获对象、回调和原线程已关闭；七块原DMA按逆序安全释放，稳定Overlay恢复，无新增DMA。原生产64MiB政策、服务和回滚保持。

原始结果SHA：`{evidence['sha256']}`。本解读SHA：`{digest}`。

下一步仅验证三个末批chain：`attention_out`、`gate_up`、`mlp_down`各31行，输入来自本次原参考，输出逐位核对各对应NPY；原M238打包/解析/缩放重试与权重暂存保持。任一失败停在chain级。全部通过才验证原layer35完整Attention和K/V加末批后三投影的组合，再固定文本、固定159视频和轻量交错性能。

预期完整视频逻辑调用766，物理调用按实际重试记录。调用数推导不是板端PASS；本次带诊断与文件保存的时间也不是新的性能结果。已有并行硬件40.81%结论保持，闭合的SiLU workspace、双parser、PS预读变体仍关闭。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m398_tail_reference_closure',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,raw_sha256=evidence['sha256'],
         reference_capture_pass=True,candidate_numerical_pass=False,performance_pass=False),
         f'## M398 原末层参考捕获闭合（2026-10-04）\n\nBuild0x4D333537，原raw `{evidence["sha256"]}`，解读 `{digest}`。原固定159完整154family/778逻辑/781模型物理、3重试，视觉/72KV/151936logits/判断精确一致；12项末层NPY共{c["file_bytes"]}B核验，owner/回调关闭、七DMA安全逆序释放/稳定恢复。仅原参考捕获，裁剪候选未执行，无新性能，生产64MiB保持。下一步三独立末31 chain逐位核对后才单层；使用参考前后必须实际NPY SHA/shape/tensor/file identity核对。')
    print(json.dumps(dict(status=value['status'],raw_sha256=evidence['sha256'],closure_sha256=digest,fixture_bytes=c['file_bytes'])))

if __name__=='__main__':main()
