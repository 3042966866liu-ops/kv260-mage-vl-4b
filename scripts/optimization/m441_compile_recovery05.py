"""Preserve compile04 failure; isolated identical-input verbose tool recovery."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

def main():
    policy = BASE/'runs/M441-W4-compile-recovery-05/RESULT.json'
    assert not policy.exists()
    oldprep=BASE/'runs/M441-long-A-mlp_down-RTL-preparation-04/RESULT.json'
    failure=BASE/'runs/M441-long-A-mlp_down-compile-04/RESULT.json'
    old=json.loads(oldprep.read_bytes()); failed=json.loads(failure.read_bytes())
    assert failed['original_rc']==1 and failed['mode']=='compile' and not failed['RTL_run']
    for row in old['files']: assert sha(ROOT/row['path'])==row['sha256']
    log=ROOT/'tmp/m441_long_A_mlp_down_04/verilog/compile_console.log'
    assert 'Failed to compile generated C file' in log.read_text(encoding='utf-8-sig')
    files=[]
    for name in ('m441_prepare_long_rtl','m441_run_long_rtl','m441_collect_long_rtl'):
        ext='.ps1' if name=='m441_run_long_rtl' else '.py'
        src=HERE/(name+'04'+ext); dst=HERE/(name+'05'+ext)
        s=src.read_text(encoding='utf-8-sig')
        # Versioned paths and metadata only; leave shared observer03 unchanged.
        s=s.replace('_04','_05').replace('-04','-05').replace("'04'","'05'")
        s=s.replace('rtl04.py','rtl05.py').replace('preparation04','preparation05')
        if name=='m441_prepare_long_rtl': s=s.replace('_RTL_preparation03','_RTL_preparation05')
        if ext=='.ps1': s=s.replace('-log compile.log *>','-v 2 -log compile.log *>')
        else: ast.parse(s)
        assert not dst.exists(); atomic(dst,s.encode('utf-8'),immutable=True)
        files.append(dict(path=dst.relative_to(ROOT).as_posix(),sha256=sha(dst)))
    src=HERE/'m441_continue04.py'; dst=HERE/'m441_continue05.py'
    s=src.read_text(encoding='utf-8-sig')
    s=s.replace('M441-W4-zero-continuation-04','M441-W4-zero-continuation-05')
    s=s.replace('rtl04','rtl05').replace('preparation-04','preparation-05')
    s=s.replace("'_04'","'_05'").replace('_04/verilog','_05/verilog')
    s=s.replace(",'04']", ",'05']").replace('-{mode}-04/','-{mode}-05/')
    s=s.replace("=='04'","=='05'").replace('zero04','zero05')
    s=s.replace("def verified():\n", "POLICY=BASE/'runs/M441-W4-compile-recovery-05/RESULT.json'\n\ndef verified():\n    policy=json.loads(POLICY.read_bytes())\n    for f in policy['new_files']:assert sha(ROOT/f['path'])==f['sha256']\n")
    s=s.replace("held=held,last_live_sha256", "held=held,last_live_sha256")
    # Retain every actually live owner on failure, including wrapper jobs.
    s=s.replace("    observe()\n    final.update", "    observation=observe()\n    held=[j for j in observation['jobs'] if j['identity']['status']=='ALIVE']\n    final.update")
    ast.parse(s);assert not dst.exists();atomic(dst,s.encode('utf-8'),immutable=True)
    files.append(dict(path=dst.relative_to(ROOT).as_posix(),sha256=sha(dst)))
    r=dict(status='PREPARED_M441_IDENTICAL_W4_VERBOSE_COMPILE_RECOVERY05',
        failed_compile_sha256=sha(failure),failed_log_sha256=sha(log),original_A_preparation_sha256=sha(oldprep),
        new_files=files,changes=['Independent05 paths/metadata','Correct preparation version key','xelab verbosity2 only'],
        unchanged=['DUT','observer03 logic','fixture','12M cycle budget','8h wall budget','full-output and protocol checks'],
        diagnostics=dict(gcc_syntax_rc=0,gcc_object_rc=0,clang_syntax_rc=0,
          limits='Independent compiler probes are not xelab compile PASS; original native compiler command and reason not yet captured.'),
        source_c_sha256=sha(ROOT/'tmp/m441_long_A_mlp_down_04/verilog/xsim.dir/m441_trace/obj/xsim_63.c'),
        diagnostic_obj_sha256=sha(ROOT/'tmp/m441_compile_diagnostic_01/xsim_63.obj'),
        board=False,RTL_run=False,old_failure_changed=False)
    atomic(policy,encoded(r),immutable=True)
    sync('latest_m441_W4_compile_recovery05',dict(status=r['status'],sha256=sha(policy),result=policy.relative_to(ROOT).as_posix(),board=False),
        '## M441 W4编译失败隔离诊断05（2026-10-09）\n\nSHA '+sha(policy)+'；04 xelab生成C编译失败原rc1保持，独立GCC语法及对象/Clang语法检查通过，尚未定位原工具原因。05仅新路径/版本键与verbose2，不改DUT、观察算法、输入、12M/8h或严格判据；仅准备，0新仿真/板端。下一步记录详细xelab编译输出，失败停编译级。')
    print(r['status'],sha(policy))

if __name__=='__main__':main()
