"""Verify completed COM3 transfer receipts; no serial or FPGA access."""
import json
import re
import sys
sys.dont_write_bytecode=True
import m351_workflow as w
from m355_workflow import PKG,PREP

def main():
    target=w.BASE/'runs/M355-transfer-01/RESULT.json'
    if target.exists():raise RuntimeError('Immutable receipt exists')
    prior=json.loads((PREP/'RESULT.json').read_text(encoding='utf-8'))
    assert w.sha(PKG/'PACKAGE_MANIFEST.json')==prior['manifest_sha256']
    assert w.sha(w.HERE/'m355_control.ps1')==prior['controller_sha256']
    assert w.sha(w.HERE/'m355_workflow.py')==prior['workflow_sha256']
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size,sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'))]+manifest['files']
    receipts=[]
    for row in rows:
        name=row['path'];assert w.sha(PKG/name)==row['sha256']
        log=w.ROOT/'tmp/m355'/('upload_'+name.replace('.','_')+'_final.log')
        text=log.read_text(encoding='utf-8-sig')
        actual=re.findall(r'^\s*M212_CHUNKED_FILE_PASS (/home/ubuntu/\S+) (\d+) ([0-9a-f]{64})\s*$',text,re.M)
        assert actual==[('/home/ubuntu/m355_device_phase_01/'+name,str(row['bytes']),row['sha256'])]
        assert '__M75C_UART_RC_0__' in text
        receipts.append(dict(file=name,bytes=row['bytes'],sha256=row['sha256'],log_sha256=w.sha(log)))
    auth=w.ROOT/'tmp/m355/sudo_precheck_03_uart.log'
    assert '__M355_PRECHECK03_RC_0__' in auth.read_text(encoding='utf-8-sig')
    r=dict(status='PASS_COM3_FROZEN_PACKAGE_TRANSFER',build_id='0x4D395832',preparation_sha256=w.sha(PREP/'RESULT.json'),manifest_sha256=prior['manifest_sha256'],files=receipts,
        total_bytes=sum(row['bytes'] for row in rows),manifest_first=True,chunk_bytes=900,authorization_log_sha256=w.sha(auth),
        overlay_loaded=False,fpga_transactions=0,performance_pass=False,rejected_attempts=[],next_step='Run once after bash-n and same-terminal sudo; collect original bytes and pause.')
    w.atomic(target,w.encoded(r),immutable=True);sha=w.sha(target)
    note='## M355 COM3授权恢复与冻结包传输完成（2026-10-02）\n\n用户确认回shell并续期；同COM3 sudo rc0。manifest-first、900B分块，'+str(len(rows))+'份文件/'+str(r['total_bytes'])+'B在板端逐文件完整SHA一致，载荷未改，0Overlay/FPGA事务。传输证据 `'+target.relative_to(w.ROOT).as_posix()+'` SHA `'+sha+'`。下一步bash-n/同终端sudo及固定环境后执行四条原chain各一次，失败只收集原字节，不重跑；结束后暂停。稳定Build0x4D395832及源/服务/回滚/boot/DTB/CMA保持。\n\n'
    w.sync('latest_m355_transfer',dict(status=r['status'],result=target.relative_to(w.ROOT).as_posix(),sha256=sha,manifest_sha256=r['manifest_sha256'],fpga_transactions=0),note)
    print(json.dumps(dict(status=r['status'],files=len(rows),sha256=sha)))

if __name__=='__main__':main()
