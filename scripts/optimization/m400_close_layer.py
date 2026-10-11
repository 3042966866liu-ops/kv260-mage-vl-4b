"""Close saved M400 layer evidence only; never access or rerun the board."""
import json
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync
from m400_collect import PKG, decode, validate_layer


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    require('latest_m400_tail_layer_board' in board, 'No saved M400 board evidence; closure remains locked')
    evidence = board['latest_m400_tail_layer_board']
    path = ROOT/evidence['result']
    require(sha(path) == evidence['sha256'], 'Saved raw SHA differs')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        require(evidence['sha256'] in (ROOT/name).read_text(encoding='utf-8-sig'), 'Board triad incomplete')
    digest, raw, result = decode((ROOT/'tmp/m400/component_uart.log').read_text(encoding='utf-8-sig'))
    require(digest == evidence['sha256'] and raw == path.read_bytes(), 'Saved UART and raw bytes differ')
    require(result['status'] == 'PASS_M400_TAIL_LAYER_NUMERICAL', 'Failed layer cannot unlock fixed text')
    validate_layer(result)
    require(result['common_runner_sha256'] == sha(PKG/'m400_tail_layer_gate.py'), 'Frozen producer differs')
    manifest = json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        file = PKG/item['path']
        require(sha(file) == item['sha256'] and file.stat().st_size == item['bytes'], 'Frozen payload differs')
    for key in ('latest_m400_tail_layer_transfer', 'latest_m400_tail_layer_support'):
        receipt = board[key]
        require(sha(ROOT/receipt['result']) == receipt['sha256'], 'Support/transfer SHA differs')
        require(receipt['manifest_sha256'] == result['manifest_sha256'], 'Support/transfer package differs')
        for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
            require(receipt['sha256'] in (ROOT/name).read_text(encoding='utf-8-sig'), 'Support/transfer triad incomplete')
    require(result['original_reference_sha256'] == board['latest_m398_tail_reference_board']['sha256'], 'Original reference differs')
    require(result['chain_prerequisite_sha256'] == board['latest_m399_tail_chain_board']['sha256'], 'Prior chain differs')
    checkpoints = [p['memory'] for p in result['stages'] if 'memory' in p]
    memory = dict(sampled_memory=result['sampled_memory'], loaded_capacity=result['loaded_capacity'],
                  production_threshold_would_admit=result['production_threshold_would_admit'],
                  exact_instantaneous_peak_proven=False)
    if checkpoints:
        memory['min_checkpoint_CmaFree_MiB'] = min(p['system_bytes']['CmaFree'] for p in checkpoints)/(1<<20)
        memory['min_checkpoint_MemAvailable_MiB'] = min(p['system_bytes']['MemAvailable'] for p in checkpoints)/(1<<20)
        memory['max_checkpoint_RSS_MiB'] = max(p['process_bytes']['VmRSS'] for p in checkpoints)/(1<<20)
    value = dict(status='PASS_ISOLATED_LAYER35_LAST31_ONLY', build_id=result['build_id'],
                 raw_result=evidence['result'], raw_sha256=digest, manifest_sha256=result['manifest_sha256'],
                 original_reference_sha256=result['original_reference_sha256'],
                 chain_prerequisite_sha256=result['chain_prerequisite_sha256'],
                 layer_result=result['layer_result'], layer_call_delta=result['layer_call_delta'],
                 logical_calls=8, physical_layer_calls=8, total_physical_with_minimal=9,
                 stage_bytes=53624832, macros=81920000, extra_DMA=0,
                 full_QKV_KV_SHA_equal=True, full_attention_and_tail_tensors_bitwise_equal=True,
                 reference_maps_and_owner_released=True, seven_original_DMA_released=True,
                 stable_restored=True, production_policy_unchanged=True,
                 layer_numerical_pass=True, candidate_full_model_executed=False,
                 performance_pass=False, formal_promotion_allowed=False,
                 memory_observation=memory, source_sha256=sha(HERE/'m400_close_layer.py'),
                 next_gate='Prepare fixed30 text complete36 layers and LM head; preserve full output/KV checks. No video/performance unlocked.',
                 timing_interpretation='Load, numerical observations, hashing and recovery are diagnostic, not inference performance.')
    out = BASE/'runs/M400-tail-layer-closure-01/RESULT.json'
    atomic(out, encoded(value), immutable=True)
    closure_digest = sha(out)
    report = f'''# M400 末层组合数值闭合

Build `{result['build_id']}`，由原M398末层输入重算第35层。完整159-token QKV、RoPE、Attention和K/V保持，后三个投影只处理原末批31行。完整QKV/KV哈希相同，Attention、末批输入输出、hidden和最终norm逐位相同。

8次逻辑、8次层物理调用，加同Overlay最小事务共9次。原权重暂存53624832字节、宏计数81920000；宏为原合同单位，不是FLOPs。具体保留批次的原选档和零重试核对完成。

11项原NPY在使用前后核对完整SHA和身份。scope/map/原family绑定与owner已关闭，原七块DMA逆序安全释放，稳定Overlay恢复。原单解析worker、原SiLU、原M238打包/解析/重试保持；PS预读及双parser关闭。

完整runtime驻留，封锁新增DMA，使用独立1GiB普通RSS增长预算和64MiB普通余量。原生产64MiB CMA政策保持；采样不证明瞬时峰值或生产容量。

原始SHA `{digest}`；闭合SHA `{closure_digest}`。

本级只证明隔离单层数值与生命周期，未执行完整模型候选，也没有新的性能或晋级结论。下一步固定30文本完整36层与LM head；之后才固定159视频和轻量交错性能。旧硬件40.81%结论独立保持。
'''
    atomic(out.parent/'REPORT.md', report.encode('utf-8'), immutable=True)
    sync('latest_m400_tail_layer_closure',
         dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=closure_digest,
              raw_sha256=digest, layer_numerical_pass=True, candidate_full_model_executed=False,
              performance_pass=False, formal_promotion_allowed=False),
         f'## M400 末层组合闭合（2026-10-04）\n\nBuild0x4D333537，raw `{digest}`，闭合 `{closure_digest}`。全159QKV/Attention/KV和末31后三投影/hidden/norm精确一致；8逻辑/8层物理加minimal9，原stage53624832B/宏81920000。11NPY身份与owner/map/绑定、七DMA安全释放和稳定恢复核对。仅隔离单层，无完整候选或新性能，生产政策保持；下一步固定30文本36层完整head。')
    print(json.dumps(dict(status=value['status'], raw_sha256=digest, closure_sha256=closure_digest)))


if __name__ == '__main__':
    main()
