"""Close saved M399 chain evidence only; no board access or gate execution."""
import json
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync
from m399_collect import PKG, decode, validate_chains


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    evidence = board['latest_m399_tail_chain_board']
    path = ROOT/evidence['result']
    assert sha(path) == evidence['sha256']
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        assert evidence['sha256'] in (ROOT/name).read_text(encoding='utf-8-sig')
    # Reuse the strict envelope validator with the saved original UART bytes.
    digest, raw, result = decode((ROOT/'tmp/m399/component_uart.log').read_text(encoding='utf-8-sig'))
    assert digest == evidence['sha256'] and raw == path.read_bytes()
    if result['status'] != 'PASS_M399_LAST31_CHAIN_NUMERICAL':
        raise RuntimeError('Failed chain level cannot unlock a layer gate')
    validate_chains(result)
    assert result['common_runner_sha256'] == sha(PKG/'m399_tail_chain_gate.py')
    manifest = json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        file = PKG/item['path']
        assert sha(file) == item['sha256'] and file.stat().st_size == item['bytes']
    for key in ('latest_m399_tail_chain_transfer', 'latest_m399_tail_chain_support'):
        receipt = board[key]
        assert sha(ROOT/receipt['result']) == receipt['sha256']
        assert receipt['manifest_sha256'] == result['manifest_sha256']
        assert all(receipt['sha256'] in (ROOT/name).read_text(encoding='utf-8-sig')
                   for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    assert result['original_reference_sha256'] == board['latest_m398_tail_reference_board']['sha256']
    checkpoints = [p['memory'] for p in result['stages'] if 'memory' in p]
    memory = dict(sampled_memory=result['sampled_memory'],
                  loaded_capacity=result['loaded_capacity'],
                  production_threshold_would_admit=result['production_threshold_would_admit'],
                  exact_instantaneous_peak_proven=False)
    if checkpoints:
        memory['min_checkpoint_CmaFree_MiB'] = min(p['system_bytes']['CmaFree'] for p in checkpoints)/(1<<20)
        memory['min_checkpoint_MemAvailable_MiB'] = min(p['system_bytes']['MemAvailable'] for p in checkpoints)/(1<<20)
        memory['max_checkpoint_RSS_MiB'] = max(p['process_bytes']['VmRSS'] for p in checkpoints)/(1<<20)
    value = dict(status='PASS_LAST31_THREE_CHAINS_ONLY', build_id=result['build_id'],
                 raw_result=evidence['result'], raw_sha256=digest,
                 manifest_sha256=result['manifest_sha256'],
                 original_reference_sha256=result['original_reference_sha256'],
                 last31_chains=result['last31_chains'], chain_call_delta=result['chain_call_delta'],
                 logical_calls=3, physical_chain_calls=3, total_physical_with_minimal=4,
                 stage_bytes=45268992, macros=42598400, extra_DMA=0,
                 full_chain_outputs_bitwise_equal=True,
                 reference_maps_and_owner_released=True, seven_original_DMA_released=True,
                 stable_restored=True, production_policy_unchanged=True,
                 chain_numerical_pass=True, candidate_full_model_executed=False,
                 performance_pass=False, formal_promotion_allowed=False,
                 memory_observation=memory,
                 source_sha256=sha(HERE/'m399_close_chains.py'),
                 next_gate='Prepare isolated layer35: full159 QKV/RoPE/Attention/KV, last31 post-attention families; compare original captured tensors. No full candidate or performance unlocked.',
                 timing_interpretation='Load, numerical observations, file hashing and recovery are diagnostic, not inference performance.')
    out = BASE/'runs/M399-tail-chain-closure-01/RESULT.json'
    atomic(out, encoded(value), immutable=True)
    closure_digest = sha(out)
    report = f'''# M399 三个末31 chain 数值闭合

末层后三个投影各独立处理原最后31个 token，完整输出与 M398 原路径保存的末批输出逐位一致。原输入起点128，隔离 chain 的本地起点0；未执行组合单层或完整模型候选。

| 投影 | 输入 FP32 尺寸 | 完整输出 FP32 尺寸 | 原权重暂存字节 |
|---|---|---|---:|
| attention_out | 31×4096 | 31×2560 | 5570560 |
| gate_up | 31×2560 | gate/up 各31×9728 | 26468352 |
| mlp_down | 31×9728 | 31×2560 | 13230080 |

Build `{result['build_id']}`；三次逻辑、三次 chain 物理调用，加同 Overlay 合法最小事务共四次。此输入的原末批没有缩放重试，本次保持一致。宏计数42598400为原合同计数单位，不是FLOPs。权重暂存仍为45268992字节，没有因减少 token 而减少。

完整 runtime 驻留，原七块 DMA 已分配并封锁新增分配；原 M238 打包、解析、缩放重试及原单解析 worker 保持。七个参考 NPY 在使用前后核对完整文件 SHA、tensor SHA、尺寸、类型和文件身份。scope、引用映射及原线程已关闭，七块 DMA 按原地址/字节逆序安全释放，稳定 Overlay 恢复。PS预读、双parser、SiLU工作缓冲均关闭。

内存采用已授权的独立诊断规则：无新增专用 DMA，普通 RSS 增长上限1GiB、普通可用余量64MiB；原生产64MiB CMA准入保持。检查点和采样不证明瞬时峰值，也不证明生产容量。

原始结果 SHA：`{digest}`。闭合结果 SHA：`{closure_digest}`。

下一步仅准备单层35组合：完整159-token Q/K/V、RoPE、Attention和K/V保持，随后只计算最后原T32批31行的后三投影；核对 Attention、K/V、各末批输入输出及hidden。全部通过后才进入固定文本、固定159视频和轻量交错性能。当前是隔离 chain 数值证据，没有新的完整请求提速或正式晋级；已有硬件40.81%结论独立保持。
'''
    atomic(out.parent/'REPORT.md', report.encode('utf-8'), immutable=True)
    sync('latest_m399_tail_chain_closure',
         dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=closure_digest,
              raw_sha256=digest, chain_numerical_pass=True, candidate_full_model_executed=False,
              performance_pass=False, formal_promotion_allowed=False),
         f'## M399 三个末31 chain闭合（2026-10-04）\n\nBuild0x4D333537，raw `{digest}`，闭合 `{closure_digest}`。三个原末31完整输出逐位相同，3逻辑/3chain物理加minimal4、原stage45268992B/宏42598400；参考七NPY前后完整身份核对、scope/map关闭、七DMA安全释放及稳定恢复。仅隔离chain，未组合单层/完整模型/新性能，生产政策保持。下一步只准备layer35全159QKV/Attention/KV加末31后三投影数值门禁；失败停本级，不自动视频性能。')
    print(json.dumps(dict(status=value['status'], raw_sha256=digest, closure_sha256=closure_digest)))


if __name__ == '__main__':
    main()
