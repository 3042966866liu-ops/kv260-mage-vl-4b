"""Offline source integrity and authorization-block evidence; no serial access."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import m351_workflow as w
from m355_workflow import PKG,PREP,RELEASE

def main():
    auth=w.BASE/'runs/M355-authorization-precheck-01'
    if auth.exists():raise RuntimeError('Existing authorization evidence; do not repeat')
    lp=RELEASE/'external_assets/weights/language_fourport/SIXPORT_LAYOUT_MANIFEST.json'
    layout=json.loads(lp.read_text(encoding='utf-8'));checked=[]
    for f in layout['files']:
        p=lp.parent/f['path'];before=p.stat();h=hashlib.sha256()
        with p.open('rb') as stream:
            for raw in iter(lambda:stream.read(4<<20),b''):h.update(raw)
        after=p.stat();got=h.hexdigest()
        assert got==f['sha256'] and before.st_size==f['bytes']
        assert (before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns)
        checked.append(dict(path=p.relative_to(w.ROOT).as_posix(),bytes=f['bytes'],sha256=got))
        print('M355_LOCAL_FULL_ORIGINAL_SHARD_SHA_PASS '+f['path'],flush=True)
    log=w.ROOT/'tmp/m355/sudo_precheck_02_uart.log';captured=log.read_text(encoding='utf-8-sig')
    assert 'Password:' in captured and 'sudo -n true' not in captured
    r=dict(status='BLOCKED_COM3_PASSWORD_PROMPT_BEFORE_COMMAND',build_id='0x4D395832',shell_confirmed=False,
        command_sent=False,sudo_checked=False,board_upload=False,overlay_loaded=False,fpga_transactions=0,
        log=log.relative_to(w.ROOT).as_posix(),log_sha256=w.sha(log),preparation_sha256=w.sha(PREP/'RESULT.json'),
        manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),local_full_original_shards_verified=checked,
        note='User reported renewal, but actual COM3 prompt is Password. No command sent. Await shell + sudo-v recovery; no repeated same blocking check.',
        next_step='One new shell/sudo check only after operator reports restored shell. Then manifest-first upload/run once; automatic optimization remains paused.')
    w.atomic(auth/'RESULT.json',w.encoded(r),immutable=True);sha=w.sha(auth/'RESULT.json')
    note='## M355 上板前置：COM3密码提示，未发送命令（2026-10-02）\n\n用户报告续期后，实际COM3仍显示Password；shell保护在发送命令前拒绝。没有上传、Overlay或设备事务，设备计时未执行。已请用户完成登录、确认ubuntu shell并同终端sudo-v后关闭PuTTY；新恢复确认前不重复串口检查。四份本地原语言权重完整SHA均匹配冻结布局，计时包与四条全输出参考已准备。前置证据 `'+(auth/'RESULT.json').relative_to(w.ROOT).as_posix()+'` SHA `'+sha+'`；自动推进保持PAUSED。本次独立测试完成后暂停，稳定Build0x4D395832及源/服务/回滚/boot/DTB/CMA保持。\n\n'
    w.sync('latest_m355_authorization_precheck',dict(status=r['status'],result=(auth/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,board_upload=False,fpga_transactions=0),note)
    print(json.dumps(dict(status=r['status'],sha256=sha,full_local_shards=len(checked))))

if __name__=='__main__':main()
