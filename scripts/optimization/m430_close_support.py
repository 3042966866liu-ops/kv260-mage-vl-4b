"""Exercise saved-result closure without changing authoritative board records."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import m430_close as close
from m430_support import fixture
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m430_workflow03 import score


def main():
    good = fixture()
    no_gain = copy.deepcopy(good)
    for s in no_gain['formal_samples']:
        s['elapsed_ns'] = 40000000000
        s['timing']['total_ms'] = 40000.
    no_gain['performance_adjudication'] = score(no_gain['formal_samples'])
    no_gain['performance_pass'] = False
    failure = copy.deepcopy(good)
    failure.update(status='FAIL_M430_COMPLETE_VISUAL_WARM', gate_return_code=1,
                   errors=['Explicit closure fixture failure'], numerical_hardware_proven=False)
    checks = []
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='m430_closure_') as temporary:
        root = Path(temporary)
        for label, raw, passed in [('pass', good, True), ('no_gain', no_gain, False), ('failure', failure, False)]:
            case = root / label
            raw_path = case / 'saved.json'
            atomic(raw_path, encoded(raw))
            digest = sha(raw_path)
            atomic(case / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json', encoded({'latest_m430_complete_visual_board': dict(result='saved.json', sha256=digest)}))
            for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
                atomic(case / n, digest.encode('ascii'))
            captured = []
            with patch.object(close, 'ROOT', case), patch.object(close, 'BASE', case / 'output'), patch.object(close, 'sync', lambda *args: captured.append(args)):
                close.main()
            result = json.loads((case / 'output/runs/M430-complete-visual-warm-closure-01/RESULT.json').read_bytes())
            report = (case / 'output/runs/M430-complete-visual-warm-closure-01/REPORT.md').read_text(encoding='utf-8')
            assert result['performance_pass'] is passed and result['full_request_gate_preparation_unlocked'] is passed
            assert result['production_promoted'] is False and result['full_request_performance_proven'] is False
            assert len(captured) == 1 and captured[0][1]['sha256'] == sha(case / 'output/runs/M430-complete-visual-warm-closure-01/RESULT.json')
            assert digest in report and '不是' in report
            checks.append(label + '_saved_only_scope_and_original_decision')
    record = dict(status='PASS_M430_SAVED_CLOSURE_SUPPORT', explicit_synthetic_timers_and_PL_fixture=True,
                  checks=checks, source_sha256={n: sha(ROOT / 'scripts/optimization' / n) for n in ('m430_close.py', 'm430_close_support.py')},
                  board_execution=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M430-closure-support-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m430_complete_visual_closure_support', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
         f'## M430 保存结果闭合支持（2026-10-06）\n\nSHA {sha(out)}；实际闭合入口在隔离目录分别裁决明确synthetic PASS/无收益/FAIL，保留原SHA、范围与裁决，不写真实board raw或触发模型。不证明性能，不测温。')
    print('M430_CLOSURE_SUPPORT_SYNC', sha(out))


if __name__ == '__main__':
    main()
