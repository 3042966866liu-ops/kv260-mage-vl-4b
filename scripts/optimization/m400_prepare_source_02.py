"""Offline-only preparation of deterministic M400 source; not a board retry."""
import ast
import hashlib
import json
from unittest.mock import patch
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync
from m400_tail_source_02 import derive, validate


def rejected(action):
    try:
        action()
    except RuntimeError:
        return
    raise RuntimeError('Invalid source was accepted')


def main():
    source_path = ROOT/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    source = source_path.read_bytes()
    with patch.object(ast, 'unparse', side_effect=RuntimeError('Must not use version-specific unparse')):
        frozen = derive(source).encode('utf-8')
    digest = hashlib.sha256(frozen).hexdigest()
    proof = validate(source, frozen, digest)
    old = BASE/'candidates/M400-tail-layer-01/frozen_last_layer.py'
    if ast.dump(ast.parse(frozen), include_attributes=False) != ast.dump(ast.parse(old.read_bytes()), include_attributes=False):
        raise RuntimeError('New source differs semantically from the tested frozen layer')
    ast.parse(frozen, feature_version=(3, 10))
    rejected(lambda: derive(source+b'\n'))
    rejected(lambda: validate(source, frozen+b'\n', digest))
    changed = frozen.replace(b'range(35, 36)', b'range(34, 36)')
    rejected(lambda: validate(source, changed, hashlib.sha256(changed).hexdigest()))
    changed = frozen.replace(b'_m400_select(self, layer, attended, residual)', b'_m400_select(self, layer, residual, attended)')
    rejected(lambda: validate(source, changed, hashlib.sha256(changed).hexdigest()))
    if derive(source).encode('utf-8') != frozen:
        raise RuntimeError('Repeated source extraction differs')
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    receipt = board['latest_m400_tail_layer_failure_closure']
    if sha(ROOT/receipt['result']) != receipt['sha256']:
        raise RuntimeError('Original failure closure differs')
    out = BASE/'runs/M400-source-compatibility-preparation-02/RESULT.json'
    atomic(out.parent/'frozen_last_layer.py', frozen, immutable=True)
    value = dict(status='PASS_OFFLINE_DETERMINISTIC_SOURCE_GUARD_ONLY', proof=proof,
                 original_failure_closure_sha256=receipt['sha256'], old_frozen_sha256=sha(old),
                 checks=['unparse disabled during extraction', 'original pinned source SHA',
                         'AST equal to old tested layer in the same interpreter', 'Python3.10 grammar only',
                         'wrong original bytes rejected', 'wrong frozen SHA rejected',
                         'changed layer range rejected despite matching file SHA',
                         'changed selector arguments rejected despite matching file SHA',
                         'repeated extraction byte identical'],
                 source_sha256={n:sha(HERE/n) for n in ('m400_tail_source_02.py','m400_prepare_source_02.py')},
                 actual_target_python_tested=False, board_package_prepared=False,
                 board_access=False, process_recovered=False, hardware_rerun=False,
                 layer_numerical_pass=False, performance_pass=False,
                 next_step='Integrate stdlib-only guard before any Overlay/DMA in a new immutable same-level package, after controlled recovery plan; preserve original failed package/process.')
    atomic(out, encoded(value), immutable=True)
    result_sha = sha(out)
    sync('latest_m400_source_compatibility_preparation',
         dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=result_sha),
         f'## M400 确定性源码检查离线准备02（2026-10-04）\n\nSHA `{result_sha}`。原M241完整SHA锁定，直接源码切片/单点插入，生成不使用unparse；两树在同解释器内核对，原测试单层AST一致。9项源码/拒绝/重复字节检查通过，3.10仅grammar非目标解释器。只stdlib检查、未组装新板端包/上板/回收，原失败进程/七DMA保持，生产政策不改；下一步受控回收方案和Overlay前检查的新不可变同级包，无文本/视频/性能晋级。')
    print(json.dumps(dict(status=value['status'], result_sha256=result_sha, frozen_sha256=digest)))


if __name__ == '__main__':
    main()
