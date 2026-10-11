"""Preserve failed serial-open attempt; change only fresh authorization log."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    old=w.HERE/'m441_performance_control10.ps1'
    new=w.HERE/'m441_performance_control11.ps1'
    source=old.read_text(encoding='utf-8')
    assert w.sha(old)=='b0c70138ee5827e617951553d38272b2687c6365730e42c0d79097f934daa2c1'
    assert source.count('${Mode}_sudo_renewed01.log')==1
    changed=source.replace('${Mode}_sudo_renewed01.log','${Mode}_sudo_renewed02.log')
    assert changed.replace('${Mode}_sudo_renewed02.log','${Mode}_sudo_renewed01.log')==source
    atomic(new,changed.encode('utf-8'),immutable=True)
    out=w.BASE/'runs/M441-performance-serial-access-11'
    err="m441_performance_control10.ps1 -Mode Upload returned exit code 1 at line 38. Exception calling Open with 0 arguments: Access to the path COM3 is denied. Serial open failed before any command was sent.\n"
    atomic(out/'OPEN_FAILURE.txt',err.encode('utf-8'),immutable=True)
    log=w.ROOT/'tmp/m441_performance09/Upload_sudo_renewed01.log'
    r=dict(status='M441_PERFORMANCE_SERIAL_OPEN_DENIED11',host_controller_return_code=1,
           error='Access to the path COM3 is denied',failure_stage='SerialPort.Open',
           shell_confirmed=False,sudo_command_sent=False,upload_started=False,
           overlay_loaded=False,fpga_transactions=0,root_cause='UNDETERMINED_PERMISSION_OR_BUSY',
           raw_log=log.relative_to(w.ROOT).as_posix(),raw_log_sha256=w.sha(log),
           failure_record_sha256=w.sha(out/'OPEN_FAILURE.txt'),old_controller_sha256=w.sha(old),
           next_controller=new.relative_to(w.ROOT).as_posix(),next_controller_sha256=w.sha(new),
           only_authorization_log_name_changed=True,
           next_step='One normal-tool-permission attempt with fresh log; do not infer port busy from sandbox denial.')
    atomic(out/'RESULT.json',w.encoded(r),immutable=True)
    d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_performance_serial_access',dict(status=r['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d),
           f'## M441 完整请求串口打开拒绝11（2026-10-09）\n\nSHA {d}；用户续期后control10在SerialPort.Open被Windows拒绝，未发送sudo/上传/Overlay/事务。原日志和失败保留，原因未定，不能断言串口占用；control11仅新授权日志名，正常工具权限一次尝试，不改冻结包或门禁。')
    print(r['status'],d,r['next_controller_sha256'])

if __name__=='__main__':main()
