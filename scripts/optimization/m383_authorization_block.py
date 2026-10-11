"""Preserve failed authorization, freeze recovery controller; no board I/O."""
import json,subprocess
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
log=ROOT/'tmp/m383/sudo_precheck_01.log'
assert '__M383_CHECK_SUDO_RC_1__' in log.read_text(encoding='utf-8-sig')
path=BASE/'runs/M383-authorization-precheck-01/RESULT.json'
r=dict(status='BLOCKED_SUDO_EXPIRED_BEFORE_TRANSFER',shell_confirmed=True,sudo_return_code=1,log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),package_uploaded=False,board_gate_started=False,overlay_loaded=False,fpga_transactions=0,next_step='Human COM3 sudo-v and shell recovery; check once into new 02 log, never overwrite failed 01 receipt')
atomic(path,encoded(r),immutable=True);digest=sha(path)
sync('latest_m383_authorization',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest),f'## M383 上传前授权阻塞\n\nCOM3 shell已确认，sudo rc1；原日志与结果SHA {digest}保留。M383未上传/执行；M382 slot已PASS不重跑。等待人工续期，仅新02日志检查一次。')
source=(HERE/'m383_control.ps1').read_text(encoding='utf-8').replace('sudo_precheck_01.log','sudo_precheck_02.log')
atomic(HERE/'m383_control_recovered.ps1',source.encode('utf-8'))
pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
tested=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m383_control_recovered.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
assert tested.returncode==0 and 'M383_CONTROL_SELF_TEST_PASS' in tested.stdout
board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m383_ps_descriptor_support'];assert sha(ROOT/prior['result'])==prior['sha256']
support=json.loads((ROOT/prior['result']).read_text(encoding='utf-8'));support['source_sha256']['m383_control_recovered.ps1']=sha(HERE/'m383_control_recovered.ps1');support['prior_support_sha256']=prior['sha256'];support['authorization_recovery_only']=True;support['next_authorization_log']='tmp/m383/sudo_precheck_02.log';support['package_changed']=False
out=BASE/'runs/M383-ps-descriptor-support-02/RESULT.json';atomic(out,encoded(support),immutable=True);sd=sha(out)
sync('latest_m383_ps_descriptor_support',dict(status=support['status'],result=out.relative_to(ROOT).as_posix(),sha256=sd,manifest_sha256=support['manifest_sha256']),f'## M383 授权恢复控制闭合\n\n原控制器/失败01日志保留；独立recovered控制器仅改授权log为02，故意失败仍收集/语法通过，原包及数值入口未变；原支持SHA {prior["sha256"]}，支持02 SHA {sd}。人工恢复确认前不重复探测COM3。')
print('M383_AUTHORIZATION_BLOCK_SAVED',digest,sd)
