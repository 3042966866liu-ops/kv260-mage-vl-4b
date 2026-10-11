"""Saved-only export repair; no model or hardware re-execution."""
import ast
import base64
import contextlib
import hashlib
import io
import json
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

PKG = BASE / 'candidates/M427-saved-export-recovery-01'


def main():
    log = ROOT / 'tmp/m42702/run.log'
    text = log.read_text(encoding='utf-8-sig')
    assert 'M427_DONE gate_rc=0 export_rc=1' in text
    assert 'M427_RESULT_SAVED PASS_M427_HALF_FEATURES_TASK_PENDING' in text
    assert "CPU-only-cumulative-visual-MLP-range-screen" in text
    old = BASE / 'candidates/M427-half-ranges-software-01/m427_export.py'
    source = old.read_text(encoding='utf-8')
    wrong = 'CPU-only-cumulative-visual-MLP-range-screen'
    correct = 'CPU-only-two-half-visual-MLP-screen'
    assert source.count(wrong) == 1
    fixed = source.replace(wrong, correct)
    assert fixed.replace(correct, wrong) == source
    failure = dict(status='M427_SAVED_RESULT_EXPORT_REJECTED_NO_MODEL_REPEAT',
                   original_gate_rc=0, export_rc=1, control_rc=1,
                   source_sha256=sha(old), log_sha256=sha(log),
                   result_saved_marker_only=True, host_raw_collected=False,
                   feature_quality_claim_allowed=False, failure_cause='Exporter retained M426 gate_level literal.',
                   next_step='Only export already saved M427 bytes; never rerun gate, visual, model or PL.')
    out = BASE / 'runs/M427-export-failure-01/RESULT.json'
    atomic(out, encoded(failure), immutable=True)
    sync('latest_m427_export_failure', dict(status=failure['status'], result=out.relative_to(ROOT).as_posix(),
         sha256=sha(out), raw_collected=False, performance_pass=False),
         f'## M427 已保存结果导出拒绝（2026-10-06）\n\nSHA {sha(out)}；原gate rc0/export rc1，导出器仍要求旧M426 gate_level，导致0分块回收。两次候选视觉完成标志仅板端日志，完整raw尚未核对，不报告质量PASS。原包/日志保留，只修保存结果导出，不重跑模型、视觉或硬件。')
    review = ROOT / 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    old_review = review.read_text(encoding='utf-8-sig')
    note = '\n\n## M427 导出器门禁名称未随生产者改变（2026-10-06）\n\n'
    note += f'失败记录SHA `{sha(out)}`；软件gate rc0已保存结果，export rc1在旧M426 gate_level检查拒绝，0结果块。旧42回收负例只测试host decoder和人工合成export，没有实际执行冻结板端exporter，未覆盖该衔接。原包/原日志保留；独立恢复只改单一gate_level字面量并实际执行exporter的通过/错误/root/rc/预算检查。后续包必须让实际exporter读取producer同schema结果再经过实际decoder，不能以手写导出字符串代替producer-exporter配套证明。只回收既有原字节，绝不重新执行模型补收集。\n'
    if f'失败记录SHA `{sha(out)}`' not in old_review:
        atomic(review, (old_review.rstrip()+note).encode('utf-8'))
    # Execute actual exported function; root and pacing are explicit offline mocks.
    namespace = {'__name__': 'recovery_component'}
    exec(compile(fixed, 'm427_export_saved02.py', 'exec'), namespace)
    tests = []
    (ROOT / 'tmp/m427_recovery01').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp/m427_recovery01') as tmp:
        path = __import__('pathlib').Path(tmp) / 'BOARD_RESULT.json'
        namespace['OUTPUT'] = path
        def execute(raw, uid=0):
            path.write_bytes(raw)
            output = io.StringIO()
            with patch.object(namespace['os'], 'geteuid', return_value=uid, create=True), \
                 patch.object(namespace['time'], 'sleep', return_value=None), contextlib.redirect_stdout(output):
                namespace['emit_saved']()
            return output.getvalue()
        for rc in (0, 1):
            raw = encoded(dict(gate_level=correct, gate_return_code=rc, explicit_synthetic_fixture=True))
            emitted = execute(raw)
            assert f'M427_RESULT_SHA256={hashlib.sha256(raw).hexdigest()}' in emitted
            assert f'M427_SAVED_GATE_RC={rc}' in emitted
            chunks = [base64.b64decode(x.split(':', 1)[1], validate=True)
                      for x in emitted.splitlines() if x.startswith('M427_RESULT_CHUNK=')]
            assert b''.join(chunks) == raw and all(len(x) <= 900 for x in chunks)
            tests.append(f'actual-exporter-rc{rc}-full-original-byte-SHA')
        cases = [('old-gate-level', encoded(dict(gate_level=wrong, gate_return_code=0)), 0),
                 ('boolean-rc', encoded(dict(gate_level=correct, gate_return_code=True)), 0),
                 ('invalid-rc', encoded(dict(gate_level=correct, gate_return_code=2)), 0),
                 ('nonroot', encoded(dict(gate_level=correct, gate_return_code=0)), 1000),
                 ('oversized', encoded(dict(gate_level=correct, gate_return_code=0, padding='x'*(2<<20))), 0)]
        for name, raw, uid in cases:
            try:
                execute(raw, uid)
            except RuntimeError:
                tests.append(name)
            else:
                raise AssertionError('Invalid actual exporter input accepted: '+name)
    ast.parse(fixed, feature_version=(3, 10))
    runner = '''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
exec /usr/local/share/pynq-venv/bin/python -B ./m427_export_saved02.py
'''
    PKG.mkdir(exist_ok=False)
    atomic(PKG / 'm427_export_saved02.py', fixed.encode('utf-8'), immutable=True)
    atomic(PKG / 'collect_saved.sh', runner.encode('utf-8'), immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files),
                    files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    prepared = dict(status='PASS_M427_SAVED_ONLY_EXPORT_REPAIR_PREPARATION',
                    failure_sha256=sha(out), manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                    old_exporter_sha256=sha(old), new_exporter_sha256=sha(PKG / 'm427_export_saved02.py'),
                    only_one_gate_level_literal_changed=True, checks=tests,
                    offline_root_and_pacing_explicit_mocks=True, model_reexecution=False,
                    Python310_syntax=True, board_exported=False, performance_pass=False)
    prep = BASE / 'runs/M427-export-recovery-preparation-01/RESULT.json'
    atomic(prep, encoded(prepared), immutable=True)
    sync('latest_m427_export_recovery_preparation', dict(status=prepared['status'], result=prep.relative_to(ROOT).as_posix(),
         sha256=sha(prep), manifest_sha256=prepared['manifest_sha256']),
         f'## M427 保存结果导出恢复准备（2026-10-06）\n\nSHA {sha(prep)}；新小包manifest {prepared["manifest_sha256"]}，实际exporter的7项原字节/rc/root/旧level/预算检查通过，唯一变更gate_level字面量，Python3.10语法通过。默认只Collect既有结果，不可执行模型；尚未板端补取，原失败保留。')
    print('M427_EXPORT_RECOVERY_PREPARED', sha(prep), prepared['manifest_sha256'])


if __name__ == '__main__':
    main()
