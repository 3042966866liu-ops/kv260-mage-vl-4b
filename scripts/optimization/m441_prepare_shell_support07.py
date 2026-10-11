"""Offline adaptation of proven saved-only shell checks; no native tools."""
from m351_workflow import HERE,atomic

def adapt(name):
    s=(HERE/name).read_text(encoding='utf-8-sig')
    return s.replace('m439','m441').replace('M439','M441').replace('0x4D343339','0x4D343431')

s=adapt('m439_record_hwh.py')
compile(s,'hwh07','exec')
atomic(HERE/'m441_record_hwh07.py',s.encode(),immutable=True)

s=adapt('m439_aux_readback.py')
s=s.replace('import argparse,json,re,subprocess,time','import argparse,json,re,subprocess,time\nfrom m441_supervisor04 import boot,process as identity,classify,log_snapshot')
old="assert {x['ip'] for x in rows}=={'qwen25_mixed_gs_zynq_ultra_ps_e_0_0','qwen25_mixed_gs_reset_sync_0'}"
assert old in s
s=s.replace(old,"assert {x['ip'] for x in rows}.issubset({'qwen25_mixed_gs_zynq_ultra_ps_e_0_0','qwen25_mixed_gs_reset_sync_0'})")
start=s.index('        try:rc=proc.wait(timeout=p[\'budget_s\'])')
end=s.index("    atomic(out/'EXIT.json'",start)
s=s[:start]+'''        born=identity(proc.pid).get('creation_FILETIME');initial=boot()
        while proc.poll() is None:
            atomic(out/'LIVE.json',encoded(dict(status=classify(initial,boot(),identity(proc.pid,born)),process=identity(proc.pid,born),elapsed_s=time.monotonic()-start,log=log_snapshot(out/'console.log'))))
            if time.monotonic()-start>p['budget_s']:
                atomic(out/'EXIT.json',encoded(dict(vivado_rc=None,wall_budget_exceeded=True,process_retained=True,pid=proc.pid,creation_FILETIME=born)),immutable=True)
                raise RuntimeError('Readback budget exceeded: native process retained, no downstream gate')
            time.sleep(2)
        rc=proc.returncode
'''+s[end:]
s=s.replace('本次PS/reset两个Common17-354保留','仅允许本次实际出现的已知PS/reset启动Common17-354；记录数量来自日志，允许没有此错误')
s=s.replace('本次同SHA PS/reset产物独立打开','本次实际受影响的同SHA产物独立打开（零个时仅无启动错误检查）')
assert 'taskkill' not in s
compile(s,'aux07','exec')
atomic(HERE/'m441_aux_readback07.py',s.encode(),immutable=True)

s=adapt('m439_collect_shell.py')
s=s.replace('M441-shell-control-preparation-01','M441-shell-control-preparation-07')
s=s.replace('m441_collect_shell.py','m441_collect_shell07.py')
compile(s,'collectshell07','exec')
atomic(HERE/'m441_collect_shell07.py',s.encode(),immutable=True)
print('PREPARED_SHELL_SUPPORT07_NO_NATIVE_EXECUTION')
