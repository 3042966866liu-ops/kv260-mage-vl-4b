"""Saved-only COM3 bootstrap upload closure, no control commands."""
import json,re
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
logs=ROOT/'tmp/m439_board';boot=BASE/'candidates/M439-transfer-bootstrap-01'
spec=json.loads((boot/'PACKAGE_MANIFEST.json').read_bytes())
items=[dict(path='PACKAGE_MANIFEST.json',bytes=(boot/'PACKAGE_MANIFEST.json').stat().st_size,sha256=sha(boot/'PACKAGE_MANIFEST.json'))]+spec['files']
evidence=[]
for name,marker in [('sudo_bootstrap.log','__M439_BOOT_SUDO_RC_'),('bootstrap_absence.log','__M439_BOOT_ABSENT_RC_'),('bootstrap_syntax.log','__M439_BOOT_SYNTAX_RC_')]:
    p=logs/name;s=p.read_text(encoding='utf-8-sig');assert re.findall(r'(?m)^'+marker+r'([01])__\s*$',s)==['0']
    target=BASE/'runs/M439-bootstrap-upload-01/logs'/name;atomic(target,p.read_bytes(),immutable=True);evidence.append(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target)))
for item in items:
    stem='bootstrap_'+item['path'].replace('.','_');count=(item['bytes']+899)//900
    for kind in ['init']+['chunk_'+format(i,'03d') for i in range(1,count+1)]+['final']:
        p=logs/(stem+'_'+kind+'.log');s=p.read_text(encoding='utf-8-sig')
        assert re.findall(r'(?m)^__M75C_UART_RC_([01])__\s*$',s)==['0']
        if kind=='final':
            assert re.findall(r'(?m)^M212_CHUNKED_FILE_PASS (\S+) (\d+) ([0-9a-f]{64})\s*$',s)==[('/home/ubuntu/m439_transfer_bootstrap_01/'+item['path'],str(item['bytes']),item['sha256'])]
        if kind.startswith('chunk_'):
            index=int(kind[6:]);assert re.findall(r'(?m)^M212_CHUNK_PASS (\d+) (\d+) (\d+)\s*$',s)==[(str(index),str(count),str(min(index*900,item['bytes'])))]
        evidence.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
r=dict(status='PASS_M439_BOOTSTRAP_MANIFEST_FIRST_UPLOAD_ONLY',build_id='0x4D343339',bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),files=items,evidence=evidence,root_same_terminal=True,runner_bash_n=True,maximum_chunk_bytes=900,package_uploaded=False,overlay_loaded=False,fpga_transactions=0,board_gate_executed=False,original_controller_sha256=sha(HERE/'m439_control.ps1'),next_controller_sha256=sha(HERE/'m439_control02.ps1'))
p=BASE/'runs/M439-bootstrap-upload-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_bootstrap_upload',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 续期后bootstrap上传闭合（2026-10-07）\n\nSHA '+sha(p)+'；COM3 shell/同TTY sudo rc0、manifest先传、4文件全部≤900B分块/完整SHA及bash-n PASS。只bootstrap，0新核包/Overlay/FPGA事务；原工具和板端包不改。下一步有界指定对端传完整51文件，必须网络回读/逐SHA闭合后Build-ID。')
print(r['status'],sha(p))
