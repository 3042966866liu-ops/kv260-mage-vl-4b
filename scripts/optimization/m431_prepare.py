"""Audit and prepare the late11 adapter borrowing the resident language DMA."""
import ast
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites = {}
    for key in ('latest_m430_complete_visual_closure', 'latest_m429_late11_visual_numerical_closure', 'latest_m428_saved_language_closure'):
        e = board[key]
        assert sha(ROOT / e['result']) == e['sha256']
        assert all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prerequisites[key] = e
    assert prerequisites['latest_m430_complete_visual_closure']['performance_pass'] is True
    source = HERE / 'm422_borrowed_visual.py'
    old = source.read_text(encoding='utf-8')
    new = old.replace('index not in (12,13)', 'index not in range(13,24)').replace('Only layers12+13 four Linear stages', 'Only accepted layers13..23 MLP Linear stages')
    assert old.count('index not in (12,13)') == 2
    assert new.replace('index not in range(13,24)', 'index not in (12,13)').replace('Only accepted layers13..23 MLP Linear stages', 'Only layers12+13 four Linear stages') == old
    new = new.replace('Default-off visual transactions borrow the original seven language buffers.', 'Default-off late11 visual transactions borrow the original seven language buffers.')
    atomic(HERE / 'm431_borrowed_visual.py', new.encode('utf-8'), immutable=True)
    # No resource or arithmetic method changes besides the two accepted-layer guards.
    ot, nt = ast.parse(old), ast.parse(new)
    oc = next(n for n in ot.body if isinstance(n, ast.ClassDef))
    nc = next(n for n in nt.body if isinstance(n, ast.ClassDef))
    unchanged = []
    for name in ('__init__', 'check', '__enter__', '__exit__'):
        a = next(n for n in oc.body if getattr(n, 'name', None) == name)
        b = next(n for n in nc.body if getattr(n, 'name', None) == name)
        assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
        unchanged.append(name)
    for name in ('stage', 'submit'):
        a = next(n for n in oc.body if getattr(n, 'name', None) == name)
        b = next(n for n in ast.parse(new.replace('index not in range(13,24)', 'index not in (12,13)').replace('Only accepted layers13..23 MLP Linear stages', 'Only layers12+13 four Linear stages')).body if isinstance(n, ast.ClassDef)).body
        b = next(n for n in b if getattr(n, 'name', None) == name)
        assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
        unchanged.append(name + '_except_range_guard')
    test = (HERE / 'test_m422_borrowed_visual.py').read_text(encoding='utf-8')
    test = test.replace('from m422_borrowed_visual import', 'from m431_borrowed_visual import').replace("owner.submit(14,'fc2'", "owner.submit(24,'fc2'")
    # Explicit workspace fixture directory, avoiding system sandbox temp paths.
    test = test.replace('tempfile.TemporaryDirectory()', "tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'tmp')")
    test = test.replace("print('M422_COMPONENT='", "print('M431_COMPONENT='")
    atomic(HERE / 'test_m431_borrowed_visual.py', test.encode('utf-8'), immutable=True)
    cp = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(HERE / 'test_m431_borrowed_visual.py')], capture_output=True)
    folder = BASE / 'runs/M431-borrowed-late11-preparation-01'
    atomic(folder / 'component_stdout.bin', cp.stdout, immutable=True)
    atomic(folder / 'component_stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0
    line = next(x for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M431_COMPONENT='))
    result = json.loads(line.split('=', 1)[1])
    assert result['fake_DMA_MMIO_memory'] and result['extra_allocate_or_free_calls'] == 0 and result['timeout_preserves_original_owner']
    value = dict(status='PREPARED_M431_LATE11_BORROWED_DMA_ADAPTER_OFFLINE', prerequisites=prerequisites,
                 selected_layers=list(range(13, 24)), source_m422_sha256=sha(source), unchanged_AST_methods=unchanged,
                 source_sha256={n: sha(HERE / n) for n in ('m431_borrowed_visual.py', 'test_m431_borrowed_visual.py')},
                 component=result, scope='Offline real NumPy33MiB geometry with explicit fake DMA/MMIO/policy, not hardware or full-runtime proof.',
                 original_seven_DMA_sizes=[6963200]*4+[389152,2621440,2621440], additional_DMA_allocations=0,
                 new_control_or_bitstream=False, actual_full_request_numerics_pass=False, actual_full_request_performance_pass=False,
                 temperature_measurement_enabled=False, production_promoted=False,
                 next_step='Cover all286 original batch positions and22 stages with the strict saved-wire/late11 scope, then package isolated CPU component before integrated two-request numerical gate. Do not blindly replace two-layer ranges in original M425 trials.')
    out = folder / 'RESULT.json'
    atomic(out, encoded(value), immutable=True)
    sync('latest_m431_borrowed_late11_preparation', dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
         f'## M431 后11层完整请求借用DMA接入审计（2026-10-06）\n\nSHA {sha(out)}。M430完整视觉7.686577%净收益已闭合，继续完整请求接入。原M422借用七块DMA不新增分配/释放/Overlay，owner及退出AST保持，仅两处层范围改13–23；真实NumPy33MiB几何、明确fake DMA/MMIO/policy的拒绝/超时保留/缓存失效组件通过。尚未完整286批集成/板端CPU组件/完整请求数值或性能；不测温、不接生产。下一步补齐286批与22暂存覆盖并准备隔离组件。')
    print('M431_PREPARATION_SYNC', sha(out))


if __name__ == '__main__':
    main()
