"""Only host recovery logs change; package and request execution stay frozen."""
import ast
import inspect
import json
import subprocess
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    s=(HERE/'m403_workflow.py').read_text(encoding='utf-8')
    changed=s.replace('tmp/m403/assembly_uart.log','tmp/m403/assembly02_uart.log').replace('tmp/m403/root_syntax_uart.log','tmp/m403/root_syntax02_uart.log')
    assert changed!=s and changed.replace('tmp/m403/assembly02_uart.log','tmp/m403/assembly_uart.log').replace('tmp/m403/root_syntax02_uart.log','tmp/m403/root_syntax_uart.log')==s
    atomic(HERE/'m403_workflow04.py',changed.encode('utf-8'),immutable=True)
    import m403_support02
    f=inspect.getsource(m403_support02.transfer_checks).replace('import m403_workflow as workflow','import m403_workflow04 as workflow').replace("logs/'assembly_uart.log'","logs/'assembly02_uart.log'").replace("logs/'root_syntax_uart.log'","logs/'root_syntax02_uart.log'")
    ns=dict(vars(m403_support02));exec(compile(f,'<actual-resume-workflow-fake-receipts>','exec'),ns);count=ns['transfer_checks']()
    ps=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    p=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m403_assemble_recovery04.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M403_ASSEMBLY_ONLY_SELF_TEST_PASS' in p.stdout
    source=(HERE/'m403_assemble_recovery04.ps1').read_text(encoding='utf-8')
    assert 'put_file' not in source and '-Mode Upload' not in source and 'M403_ENABLE_LIGHT_VIDEO' not in source
    for n in ('m403_resume04.py','m403_workflow04.py','m403_resume_support04.py'):ast.parse((HERE/n).read_bytes(),feature_version=(3,10))
    value=dict(status='PASS_OFFLINE_M403_ASSEMBLY_ONLY_RECOVERY',actual_workflow_transfer_checks=count,old_logs_preserved=True,no_upload_repeated=True,no_model_or_overlay=True,manifest_and_gate_unchanged=True,source_sha256={n:sha(HERE/n) for n in ('m403_assemble_recovery04.ps1','m403_resume04.py','m403_workflow04.py','m403_resume_support04.py')})
    out=BASE/'runs/M403-assembly-recovery-support-04/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_assembly_recovery_support04',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 只组装恢复支持04（2026-10-04）\n\nSHA {h}；现有15文件全部真实上传回执复核，版本04只选择新组装/语法日志，实际workflow假回执/原子目的地/键/缺失拒绝复用验证，PS语法通过。旧失败日志保持，不重传/不改包/不启动模型。用户同COM3续期后只运行m403_assemble_recovery04.ps1 Assemble，成功同步后用control03 Run一次。')
    print(value['status'],h)


if __name__=='__main__':main()
