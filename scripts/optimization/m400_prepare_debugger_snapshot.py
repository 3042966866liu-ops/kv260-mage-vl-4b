"""Freeze saved-artifact/native-stack collection; no Python C-API calls."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    pkg=BASE/'candidates/M400-native-stack-01'
    if pkg.exists():raise RuntimeError('Fresh stack snapshot package required')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior=board['latest_m400_owner_live_inspect_board']
    if sha(ROOT/prior['result'])!=prior['sha256']:raise RuntimeError('Saved inspection failure SHA differs')
    pkg.mkdir(parents=True)
    for n in ('m400_debugger_snapshot.py','m400_owner_readonly_probe.py'):
        ast.parse((HERE/n).read_bytes(),feature_version=(3,10));atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    runner=b'''#!/usr/bin/env bash\nset -euo pipefail\n[[ $EUID == 0 && $# == 1 ]] || exit 65\ntask_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\nexec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_debugger_snapshot.py" --enable-native-stack-snapshot "$1"\n'''
    atomic(pkg/'run_m400_stack_snapshot.sh',runner,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-native-stack-preparation-01/RESULT.json'
    r=dict(status='PREPARED_READONLY_NATIVE_STACK_COLLECTION',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
           prior_failure_sha256=prior['sha256'],function_calls_forbidden=True,owner_resume_planned=False,
           resources_release_planned=False,new_overlay_loads=0,new_DMA_allocations=0,
           Python3_10_check='grammar only',readnever_backtrace_may_be_incomplete=True,
           official_GDB_options='https://sourceware.org/gdb/current/onlinedocs/gdb.html/File-Options.html')
    atomic(out,encoded(r),immutable=True);d=sha(out)
    sync('latest_m400_native_stack_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),
         f'## M400 GDB超时现场只读收集准备（2026-10-04）\n\nSHA `{d}`；只读取保存的Python结果是否存在及原挂起owner的native stack，GDB禁用函数调用、无SIGCONT/close/Overlay/DMA。--readnever避免加载符号调试信息，回溯可能不完整；15秒预算、stdout始终保存。原超时不重跑C-API注入/模型，不把缺少日志解释为已经释放。')
    print(r['status'],r['manifest_sha256'])


if __name__=='__main__':main()
