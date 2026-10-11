"""Freeze exact shell controls and known export-failure prevention."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import json
prep=BASE/'runs/M439-shell-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
assert p['status']=='PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES'
expected=(HERE/'m357_build_shell.tcl').read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439').replace('0x4D333537','0x4D343339')
expected=expected.replace('write_hw_platform -fixed -include_bit -file','write_hw_platform -fixed -file')
assert expected==(HERE/'m439_build_shell.tcl').read_text(encoding='utf-8')
assert (HERE/'m357_run_shell.ps1').read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439')==(HERE/'m439_run_shell.ps1').read_text(encoding='utf-8')
r=dict(status='PREPARED_M439_FROZEN_SHELL_CONTROLS',build_id='0x4D343339',shell_preparation_sha256=sha(prep),
       controller_sha256=sha(HERE/'m439_run_shell.ps1'),Tcl_sha256=sha(HERE/'m439_build_shell.tcl'),
       original_controller_sha256=sha(HERE/'m357_run_shell.ps1'),original_Tcl_sha256=sha(HERE/'m357_build_shell.tcl'),
       inherited_export_repair='Separate manually generated bit and matching HWH, XSA exported without include-bit. Prevent original M357 include-bit export failure without changing circuit/topology/clock.',
       temporary_short_path_mapping='T: only if absent; verify mapped workspace/preparation SHA, finally remove only own mapping.',
       shell_executed=False,board=False,promotion=False)
ev=BASE/'runs/M439-shell-control-preparation-01/RESULT.json';atomic(ev,encoded(r),immutable=True)
sync('latest_m439_shell_control_preparation',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
     '## M439 整壳控制冻结（2026-10-07）\n\nSHA '+sha(ev)+'；复用原M357控制/板级拓扑/时钟，只改隔离名称与Build；XSA导出复用原已闭合不嵌bit路径，避免旧manual-bit/include-bit错误。T:仅缺席时创建并finally回收。尚未实现/上板。')
print(r['status'],sha(ev))
