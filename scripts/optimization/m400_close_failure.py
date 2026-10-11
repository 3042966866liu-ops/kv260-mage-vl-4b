"""Close the saved source-check failure without contacting the board."""
import json
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync
from m400_collect import PKG, decode


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    evidence = board['latest_m400_tail_layer_board']
    path = ROOT/evidence['result']
    digest, raw, result = decode((ROOT/'tmp/m400/component_uart.log').read_text(encoding='utf-8-sig'))
    if sha(path) != evidence['sha256'] or digest != evidence['sha256'] or raw != path.read_bytes():
        raise RuntimeError('Saved raw and UART identity differ')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        if digest not in (ROOT/name).read_text(encoding='utf-8-sig'):
            raise RuntimeError('Failure triad incomplete')
    if result['status'] != 'FAIL_UNSAFE_RETAINED' or result['gate_return_code'] != 1:
        raise RuntimeError('Unexpected failure status')
    if 'Generated final layer source differs' not in result['traceback']:
        raise RuntimeError('Not the recorded source validation failure')
    if result['fpga_transactions'] != 1 or result['logical_calls'] or result['host_calls'] or result.get('transactions'):
        raise RuntimeError('Unexpected model submission')
    if not result['unsafe_buffers_retained'] or result.get('safe_buffers_released', False) or result.get('released_buffers'):
        raise RuntimeError('Unexpected ownership release')
    if result.get('stable_overlay_reloaded') or not result['same_overlay_minimal_proof']['full_output_exact']:
        raise RuntimeError('Restore/minimal evidence differs')
    out = BASE/'runs/M400-tail-layer-failure-closure-01/RESULT.json'
    atomic(out.parent/'UART.log', (ROOT/'tmp/m400/component_uart.log').read_bytes(), immutable=True)
    value = dict(status='FAIL_SOURCE_CHECK_BEFORE_LINEAR_PROCESS_RETAINED',
                 build_id=result['build_id'], raw_result=evidence['result'], raw_sha256=digest,
                 uart_sha256=sha(out.parent/'UART.log'), manifest_sha256=result['manifest_sha256'],
                 traceback=result['traceback'], model_logical_calls=0, model_physical_calls=0,
                 total_physical_with_minimal=1, original_DMA_count=len(result['allocated_buffers']),
                 released_DMA_count=0, final_snapshot=result['final_snapshot'],
                 sampled_memory=result['sampled_memory'], loaded_capacity=result['loaded_capacity'],
                 process_and_scope_retained=True, stable_overlay_restored=False,
                 stable_rollback_files_preserved=True, hardware_rerun=False,
                 windows_wait_controller_stopped=True, board_signal_sent=False,
                 source_mismatch_cause_confirmed=False,
                 suspected_cause='Version-dependent ast.unparse formatting; target generated text not captured, so exact cause remains unproven.',
                 layer_numerical_pass=False, candidate_full_model_executed=False,
                 performance_pass=False, formal_promotion_allowed=False,
                 source_sha256=sha(HERE/'m400_close_failure.py'),
                 next_step='Offline source compatibility and fail-before-overlay checks; keep board process/owners intact pending a controlled recovery plan. No fixed text/video/performance.')
    atomic(out, encoded(value), immutable=True)
    closure = sha(out)
    report = f'''# M400 单层源码检查失败闭合

单层包已经完整上传并核验。完整runtime构造、原七块DMA分配及同Overlay最小事务完成；进入单层scope时，冻结源码文本和板端重新生成的文本不相同，门禁拒绝。

尚未提交任何模型Linear：逻辑0、模型物理0，仅最小事务1次。没有单层张量数值比较，也没有新的性能结论。末态AP_CTRL4、MM2S/S2MM均4098，无DMA错误；这些状态证明已完成最小事务，不替代保留scope的受控释放。

板端进程、scope及七块DMA仍保留，释放数0，稳定Overlay尚未恢复。原稳定回滚文件保持。只停止了Windows等待控制器，没有发送板端信号、没有强杀或释放缓冲。

当前发现run把ast.unparse生成的文本逐字比较。Python版本可能影响格式；没有捕获板端生成文本，具体差异尚未证实，不能直接认定数值或硬件错误。后续必须先离线修源码兼容检查，在Overlay前完成检查，并准备保留进程的受控回收方案。原冻结包、失败和UART保持，不重跑硬件补日志。

原始SHA `{digest}`；失败闭合SHA `{closure}`。完整283个不超过900B分块及原SHA核对完成，BOARD/CURRENT_STATE/docsMILESTONES同步。停在单层级，固定文本、候选视频和新性能未解锁；既有硬件40.81%结论独立保持。
'''
    atomic(out.parent/'REPORT.md', report.encode('utf-8'), immutable=True)
    sync('latest_m400_tail_layer_failure_closure',
         dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=closure,
              raw_sha256=digest, process_and_scope_retained=True, stable_overlay_restored=False,
              layer_numerical_pass=False, performance_pass=False),
         f'## M400 单层源码检查失败闭合（2026-10-04）\n\nBuild0x4D333537，raw `{digest}`，闭合 `{closure}`；Generated final layer source differs发生在模型Linear前，0逻辑/0模型物理，仅minimal1。完整283块原字节核对；末态AP4/两DMA4098无错，scope/进程/七DMA保留，释放0、稳定Overlay未恢复。仅停止Windows等待，无板端信号/重跑；原稳定回滚文件保持。跨版本unparse格式仅待验证推测，不能认定数值或硬件故障。下一步离线源码兼容及Overlay前拒绝检查、受控回收方案；停单层级，文本/视频/性能未解锁。')
    print(json.dumps(dict(status=value['status'], raw_sha256=digest, closure_sha256=closure)))


if __name__ == '__main__':
    main()
