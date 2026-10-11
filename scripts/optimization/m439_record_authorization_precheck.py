"""Record the existing COM3 refusal; never opens the serial port."""
import re,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
p=ROOT/'tmp/m439_board/sudo_bootstrap.log';text=p.read_text(encoding='utf-8-sig')
assert 'ubuntu@kria:' in text and 'sudo: a password is required' in text
assert re.findall(r'(?m)^__M439_BOOT_SUDO_RC_([01])__\s*$',text)==['1']
assert not (ROOT/'tmp/m439_board/bootstrap_absence.log').exists()
assert not list((ROOT/'tmp/m439_board').glob('bootstrap_*'))
package=BASE/'runs/M439-board-package-preparation-01/RESULT.json'
r=dict(status='BLOCKED_M439_SAME_TERMINAL_SUDO_RENEWAL_REQUIRED',build_id='0x4D343339',package_sha256=sha(package),controller_sha256=sha(HERE/'m439_control.ps1'),log_path=p.relative_to(ROOT).as_posix(),log_sha256=sha(p),shell_confirmed=True,sudo_rc=1,bootstrap_uploaded=False,package_uploaded=False,overlay_loaded=False,fpga_transactions=0,board_gate_executed=False,password_attempts=0,stable_M357_M437_unchanged=True,next_step='User sudo-v on same COM3 shell then close PuTTY. After explicit renewal, check once and upload prepared bootstrap directly; no new preparation or repeated probing while blocked.')
p=BASE/'runs/M439-authorization-precheck-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_authorization_precheck',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 COM3授权前置阻塞（2026-10-07）\n\nSHA '+sha(p)+'；shell确认，首次sudo-n rc1需要密码，控制停止于上传之前，0bootstrap/包上传/Overlay/FPGA事务。全离线及整壳已通过、包已冻结；只有用户同COM3续期确认后检查一次直接上传，不重复同阻塞或猜密码。原M357/M437与服务保持。')
print(r['status'],sha(p))
