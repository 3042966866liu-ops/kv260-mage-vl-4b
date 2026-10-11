"""Record once-only sudo block; prepare fresh authorization logs only."""
import json
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import once

def main():
    p=w.ROOT/'tmp/m441_performance09/Upload_sudo.log';text=p.read_text(encoding='utf-8-sig')
    assert '__M441P_SUDO_RC_1__' in text and 'password is required' in text and 'ubuntu@kria:~$' in text
    old=w.HERE/'m441_performance_control09.ps1';new=w.HERE/'m441_performance_control10.ps1'
    source=old.read_text(encoding='utf-8');changed=once(source,'${Mode}_sudo.log','${Mode}_sudo_renewed01.log')
    assert changed.replace('${Mode}_sudo_renewed01.log','${Mode}_sudo.log')==source
    atomic(new,changed.encode('utf-8'),immutable=True)
    out=w.BASE/'runs/M441-performance-authorization-precheck-09';r=dict(status='BLOCKED_M441_PERFORMANCE_SAME_TTY_SUDO09',shell_confirmed=True,sudo_return_code=1,raw_log=p.relative_to(w.ROOT).as_posix(),raw_log_sha256=w.sha(p),upload_started=False,overlay_loaded=False,fpga_transactions=0,controller_old_sha256=w.sha(old),controller_new_sha256=w.sha(new),only_new_authorization_log_path_changed=True,old_log_preserved=True,next_controller=new.relative_to(w.ROOT).as_posix(),next_step='After explicit user renewal, Upload with control10 directly; no repeated unconfirmed COM3 probing')
    atomic(out/'RESULT.json',w.encoded(r),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_performance_authorization',dict(status=r['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d),f'## M441 完整请求sudo前置阻塞09（2026-10-09）\n\nSHA {d}；shell确认但同TTY sudo rc1，需要密码，0上传/Overlay/事务。完整视频已PASS、性能协议/包/支持已完成。原日志保留，新control10仅授权日志名renewed01，人工续期后直接Upload，未有确认不反复探测。')
    n=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json';v=json.loads(n.read_bytes());v['stages']['performance_authorization_blocked09']=dict(evidence=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d);atomic(n,w.encoded(v))
    print(r['status'],d,r['controller_new_sha256'])

if __name__=='__main__':main()
