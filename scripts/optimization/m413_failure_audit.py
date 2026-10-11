"""Read retained results and frozen code only; no UART, model, or replay."""
import ast
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def runtime_contexts(path):
    rows = []
    def visit(node, contexts):
        if isinstance(node, (ast.With, ast.AsyncWith)):
            contexts = contexts + [ast.unparse(x.context_expr) for x in node.items]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'runtime':
            rows.append(dict(line=node.lineno, contexts=contexts))
        for child in ast.iter_child_nodes(node):
            visit(child, contexts)
    visit(ast.parse(path.read_text(encoding='utf-8-sig')), [])
    return rows


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    row = board['latest_m413_layer12_visual_board']
    raw = ROOT/row['result']
    assert sha(raw) == row['sha256']
    assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    result = json.loads(raw.read_bytes())
    old = BASE/'runs/M408-local-MLP-A8-board-04/BOARD_RESULT.json'
    reference = json.loads(old.read_bytes())
    assert result['gate_return_code'] == 1 and result['errors'][0]['message'] == 'Original complete visual SHA differs'
    assert result['visual_forward_calls'] == 1 and not result['PL_rows'] and not result['language_forward_calls']
    assert result['safe_buffers_released'] and result['PS_owner_closed'] and result['stable_restored']
    old_gate = BASE/'candidates/M408-local-MLP-A8-capture-04/m408_gate.py'
    new_gate = BASE/'candidates/M413-layer12-full-visual-01/m413_gate.py'
    matches = {key: result[key] == reference[key] for key in ('preprocessed', 'backend_before', 'target_resolution', 'target_matrices', 'resolved_modules')}
    assert all(matches.values())
    original_contexts = runtime_contexts(old_gate)
    new_contexts = runtime_contexts(new_gate)
    assert len(original_contexts) == 1 and len(new_contexts) == 2
    assert not any('torch.inference_mode' in x for x in original_contexts[0]['contexts'])
    assert all(any('torch.inference_mode' in x for x in r['contexts']) for r in new_contexts)
    value = dict(status='M413_RETAINED_ORIGINAL_REFERENCE_DIFFERENCE_UNRESOLVED',
                 raw_sha256=row['sha256'], old_reference_sha256=sha(old),
                 same_recorded_conditions=matches,
                 expected_visual=reference['visual'], actual_visual=result['original_visual'],
                 original_runtime_call_contexts=original_contexts, new_runtime_call_contexts=new_contexts,
                 source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in (old_gate, new_gate,
                     BASE/'candidates/M413-layer12-full-visual-01/test_m413_quality.py',
                     ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m273_latest_vision_runtime.py')},
                 additional_component_before_constructor=True,
                 component_in_same_process_manual_seed_413=True,
                 original_runtime_has_own_internal_inference_mode=True,
                 execution_context_is_proven_root_cause=False,
                 missing=['Full original feature values not saved before failed SHA assertion',
                          'Layer12 capture hashes not recorded before failed SHA assertion',
                          'Backend/RNG/native dispatch or floating-point state before/after component not recorded'],
                 current_result_phase_is_last_recovery_phase_not_failure_location=True,
                 real_candidate_MLP_calls=0, physical_transactions=2,
                 transactions_scope='Candidate Build-ID legal minimal and restored stable legal minimal only',
                 actual_allocations=len(result['allocations']), actual_releases=len(result['releases']),
                 safe_buffers_released=result['safe_buffers_released'], stable_restored=result['stable_restored'],
                 new_board_work=False, feature_quality_pass=False, semantic_quality_pass=False, performance_pass=False,
                 next_concrete_step='Prepare a CPU-only reference isolation at this failed level: original M408 call boundary and component process isolation; record feature/capture evidence before strict comparison. Do not change expected SHA, thresholds, weights, or expand layers. Validate source and lifecycle before any new board attempt.')
    out = BASE/'runs/M413-original-reference-audit-01/RESULT.json'
    atomic(out, encoded(value), immutable=True)
    report = '# M413 原版视觉参考差异：已有结果只读审计\n\n'
    report += '原始失败裁决保留。实际原版完整视觉1次，候选MLP为0次；两次物理事务仅为候选与稳定Build-ID最小事务。19块分配/释放闭合，PS所有者关闭，稳定Overlay恢复。\n\n'
    report += '已记录的预处理、后端/线程、实际解析模块、目标拓扑与矩阵身份全部等于M408原参考。旧特征SHA为 `'+reference['visual']['sha256']+'`，本次为 `'+result['original_visual']['sha256']+'`。形状和dtype一致，SHA差异只说明字节不同，没有数组可计算差异大小。\n\n'
    report += '代码审计发现新入口的原版调用外增加了 `torch.inference_mode()`，而冻结M273入口本身已有内部上下文；新组件又在构造前同进程执行，含manual_seed和BF16 fixture。它们是需要隔离的执行条件差异，尚未证明因果；不能直接认定为权重、PL、缓存或精度问题。\n\n'
    report += '失败断言先于完整特征文件保存和局部capture元数据记录，因此不能离线定位首个变化层。raw中的phase是恢复阶段，原失败位置应以traceback为准。bindings_restored=False的成功汇总尚未到达，不能单独当作泄漏证明。没有额外硬件、模型或校验重跑。\n\n'
    report += '下一步仅在失败级准备CPU参考隔离：保留旧调用边界、隔离组件进程，严格比较前先保留特征和capture证据。原SHA、阈值、权重与输入不放宽，不扩层，不把这次失败当作第12层候选质量下降。\n'
    atomic(out.with_name('REPORT.md'), report.encode('utf-8'), immutable=True)
    sync('latest_m413_original_reference_audit', dict(status=value['status'], result=out.relative_to(ROOT).as_posix(),
         sha256=sha(out), raw_sha256=row['sha256'], root_cause_proven=False, new_board_work=False),
         '## M413 原版参考差异只读审计（2026-10-06）\n\nSHA '+sha(out)+'，原raw '+row['sha256']+' FAIL保留。预处理、后端/线程、11解析模块、目标拓扑及矩阵身份同旧M408；原版1次、PL候选0次，19/19释放及稳定恢复。发现新增外围inference上下文与同进程组件/RNG差异，根因未证明；原完整数组/capture未在断言前保留，不能量化误差。仅离线读取，没有重跑。下一步CPU参考隔离当前失败级，原SHA与阈值不放宽、不扩层。')
    print('M413_FAILURE_AUDIT_SYNC', sha(out))


if __name__ == '__main__':
    main()
