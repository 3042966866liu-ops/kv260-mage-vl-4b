"""Freeze a small stdlib-only read-only audit, independent of the model gate."""
import ast
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync

OLD=BASE/'candidates/M400-tail-layer-01'
PKG=BASE/'candidates/M400-owner-audit-01'


def main():
    if PKG.exists():
        raise RuntimeError('Fresh audit package required')
    spec=importlib.util.spec_from_file_location('owner_probe_test',HERE/'m400_owner_readonly_probe.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=ROOT/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    frozen=BASE/'runs/M400-source-compatibility-preparation-02/frozen_last_layer.py'
    pin=dict(original_package='/home/ubuntu/m400_tail_layer_candidate_01',
             original_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),
             original_raw='/home/ubuntu/m400_tail_layer_01/B1/load-memory.json',
             original_raw_sha256='de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9',
             original_source='/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py',
             original_source_sha256=sha(source),new_frozen_sha256=sha(frozen),
             source_sha256={n:sha(OLD/n) for n in ('m343_layer_scope.py','m400_tail_layer_scope.py','frozen_last_layer.py','m400_tail_layer_gate.py')})
    with tempfile.TemporaryDirectory(prefix='m400-owner-audit-',dir=ROOT/'tmp/m400') as d:
        stage=Path(d)
        shutil.copyfile(frozen,stage/'frozen_last_layer_02.py')
        local={**pin,'original_package':str(OLD),'original_source':str(source)}
        with patch.object(module,'HERE',stage):
            r=module.reproduce(local)
            assert r['old_text_equal'] and r['same_interpreter_AST_equal'] and r['new_guard']['deterministic_source_equal']
            original_unparse=ast.unparse
            def altered(node):
                text=original_unparse(node)
                return text.replace("'attention_out'",'"attention_out"') if text.startswith('def one_layer(') else text
            with patch.object(ast,'unparse',altered):
                r=module.reproduce(local)
                assert not r['old_text_equal'] and r['same_interpreter_AST_equal'] and r['exact_diff']
            for key in ('original_manifest_sha256','original_source_sha256','new_frozen_sha256'):
                bad={**local,key:'0'*64}
                try:module.reproduce(bad)
                except RuntimeError:pass
                else:raise RuntimeError('Source pin negative accepted')
    PKG.mkdir(parents=True)
    for name in ('m400_owner_readonly_probe.py','m400_tail_source_02.py'):
        atomic(PKG/name,(HERE/name).read_bytes(),immutable=True)
    atomic(PKG/'frozen_last_layer_02.py',frozen.read_bytes(),immutable=True)
    atomic(PKG/'PIN.json',encoded(pin),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
exec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_owner_readonly_probe.py" "$2" "$1"
'''
    atomic(PKG/'run_m400_owner_audit.sh',runner.encode(),immutable=True)
    files=[]
    for p in sorted(PKG.iterdir()):
        if p.suffix=='.py':ast.parse(p.read_bytes(),feature_version=(3,10))
        files.append(dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)))
    manifest=dict(schema='M400-owner-audit-readonly-v1',files=files,file_count=len(files),total_bytes=sum(f['bytes'] for f in files))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    out=BASE/'runs/M400-owner-audit-preparation-01/RESULT.json'
    value=dict(status='PASS_OFFLINE_READONLY_OWNER_AUDIT_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               file_count=len(files),total_bytes=manifest['total_bytes'],
               checks=['actual frozen derive functions in stdlib-only namespace',
                       'injected formatting-only mismatch preserves native AST and records diff',
                       'original manifest drift rejected','original M241 drift rejected','new frozen drift rejected'],
               tests_use_actual_proc=False,actual_board_python_tested=False,
               owner_recovery_performed=False,board_signals_in_probe=False,
               numpy_pynq_runtime_imports=False,hardware_gate_rerun=False,
               source_sha256={n:sha(HERE/n) for n in ('m400_owner_readonly_probe.py','m400_prepare_owner_audit.py','m400_pause_owner.ps1')})
    atomic(out,encoded(value),immutable=True);digest=sha(out)
    sync('latest_m400_owner_audit_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=value['manifest_sha256']),
         f'## M400 原owner只读调查包准备（2026-10-04）\n\nSHA `{digest}`，manifest `{value["manifest_sha256"]}`；5载荷/stdlib-only，冻结实际derive与格式差异注入、三种SHA拒绝检查通过，3.10仅语法。板端一次挂起已回shell，原owner/七DMA未退出或释放；COM3 sudo过期，等待人工续期。下一步只读取实际PID/线程/fd、退出入口和目标Python生成文本/AST及精确diff，不加载Overlay、不申请DMA、不释放或附加调试器；原失败保留。')
    print(json.dumps(dict(status=value['status'],sha256=digest,manifest_sha256=value['manifest_sha256'],bytes=value['total_bytes'])))


if __name__=='__main__':main()
