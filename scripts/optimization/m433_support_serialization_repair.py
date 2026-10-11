"""Use the actual gate writer for fixtures; no relaxed byte budget or candidate change."""
import ast
import copy
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once


def main():
    s = (HERE / 'm433_support03.py').read_text(encoding='utf-8')
    record = dict(status='REJECTED_M433_PRETTY_JSON_FIXTURE_BUDGET',
        reason='The fixture passed encoded(r) with indentation to actual exporter. The candidate gate write_json uses compact separators and a trailing newline. Prior sparse-template rejection alone did not resolve this representation mismatch.',
        support_source_sha256=sha(HERE / 'm433_support03.py'), component_stdout_sha256=sha(ROOT / 'tmp/m43304/component/stdout.bin'),
        component_stderr_sha256=sha(ROOT / 'tmp/m43304/component/stderr.bin'),
        component_return_code=0, host_structural_check_passed=True, exporter_not_executed=True,
        packet_changed=False, byte_budget_changed=False, board_run=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-offline-support-rejection-03/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_offline_support_rejection_03', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
        f'## M433 合成保存编码差异闭合（2026-10-07）\n\nSHA {sha(out)}；前次fixture仅省重复快照仍未解决：实际gate write_json是紧凑JSON加换行，fixture却用了encoded带缩进，4MiB门禁提前拒绝。原组件rc0、host结构通过，0export/板端；两次预算拒绝限制更正为fixture序列化原因，旧记录保留。04直接执行实际gate保存函数再喂实际exporter，原包/算法/4MiB上限不改。')
    s = s.replace('tmp/m43304/', 'tmp/m43305/').replace('M433-performance-support-03', 'M433-performance-support-04')
    anchor = "    def export(value):\n        payload=encoded(value);exporter.OUTPUT.write_bytes(payload);out=io.StringIO()"
    replacement = """    import os
    writer=next(n for n in ast.parse((w.PKG/'m433_gate.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='write_json')
    writer_namespace=dict(Path=Path,json=json,os=os)
    exec(compile(ast.Module(body=[writer],type_ignores=[]),str(w.PKG/'m433_gate.py'),'exec'),writer_namespace)
    def payload_bytes(value):
        writer_namespace['write_json'](exporter.OUTPUT,value)
        return exporter.OUTPUT.read_bytes()
    def export(value):
        payload=payload_bytes(value);out=io.StringIO()"""
    s = once(s, anchor, replacement)
    s = once(s, '    raw=encoded(r);assert len(raw)<4<<20;', '    raw=payload_bytes(r);assert len(raw)<4<<20;')
    s = s.replace("'m433_support03.py'", "'m433_support04.py'").replace('actual_exporter_and_atomic_collector=True', 'actual_gate_writer_exporter_and_atomic_collector=True')
    atomic(HERE / 'm433_support04.py', s.encode('utf-8'), immutable=True)
    print('M433_ACTUAL_WRITER_SUPPORT_READY', sha(out))


if __name__ == '__main__':
    main()
