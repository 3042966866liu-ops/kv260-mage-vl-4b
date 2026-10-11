"""One startup-only change after saved GDB attach timeout: no auto solib symbols."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    old=BASE/'candidates/M400-native-stack-01';pkg=BASE/'candidates/M400-native-stack-02'
    if pkg.exists():raise RuntimeError('Fresh stack02 package required')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior=board['latest_m400_native_stack_board']
    if sha(ROOT/prior['result'])!=prior['sha256']:raise RuntimeError('Saved native timeout differs')
    evidence=json.loads((ROOT/prior['result']).read_bytes())
    if evidence.get('saved_python_owner') is not None or evidence['proc_status'].find('TracerPid:\t0\n')<0:
        raise RuntimeError('Unexpected live proof or residual tracer')
    script=(old/'m400_debugger_snapshot.py').read_text(encoding='utf-8')
    script=script.replace('m400_debugger_snapshot_01','m400_debugger_snapshot_02')
    anchor="'-iex','set auto-load off','-p','22715'"
    if script.count(anchor)!=1:raise RuntimeError('Exact GDB startup anchor differs')
    script=script.replace(anchor,"'-iex','set auto-load off','-iex','set auto-solib-add off','-p','22715'")
    script=script.replace("'-ex','info threads'","'-ex','echo M400_ATTACH_COMPLETE\\n','-ex','info threads'")
    ast.parse(script,feature_version=(3,10))
    pkg.mkdir(parents=True)
    for name in ('m400_owner_readonly_probe.py','run_m400_stack_snapshot.sh'):
        atomic(pkg/name,(old/name).read_bytes(),immutable=True)
    atomic(pkg/'m400_debugger_snapshot.py',script.encode(),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-native-stack-preparation-02/RESULT.json'
    r=dict(status='PREPARED_READONLY_NATIVE_STACK_NO_AUTO_SOLIB',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
           prior_failure_sha256=prior['sha256'],only_startup_behavior_change='set auto-solib-add off',
           function_calls_forbidden=True,owner_resume_planned=False,resources_release_planned=False,new_overlay_loads=0,
           actual_cause_of_prior_timeout_unproven=True,timeout_s=15,backtrace_may_be_incomplete=True)
    atomic(out,encoded(r),immutable=True);d=sha(out)
    sync('latest_m400_native_stack_preparation_02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),
         f'## M400 调试启动只读检查02准备（2026-10-04）\n\nSHA `{d}`；保留01失败，唯一启动组织改变set auto-solib-add off，增加附加完成标记，15秒同预算。禁止函数调用/无SIGCONT/close/Overlay/DMA；只判断调试附加是否可完成，先前超时根因未证明。原owner/七DMA保持，回收与单层重试仍未解锁。')
    print(r['status'],r['manifest_sha256'])


if __name__=='__main__':main()
