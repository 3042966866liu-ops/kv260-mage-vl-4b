"""Record bounded audit transfer receipts before the read-only board probe."""
import json
import re
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    pkg=BASE/'candidates/M400-owner-audit-01'
    m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    rows=[]
    for name in ['PACKAGE_MANIFEST.json']+[f['path'] for f in m['files']]:
        prefix='owner_upload_'+name.replace('.','_')
        final=ROOT/'tmp/m400'/(prefix+'_final.log')
        text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(pkg/name) not in text or '__M75C_UART_RC_0__' not in text:
            raise RuntimeError('Audit file receipt absent')
        count=((pkg/name).stat().st_size+899)//900
        chunks=sorted((ROOT/'tmp/m400').glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Audit transfer chunks differ')
        for i,p in enumerate(chunks,1):
            expected=r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,(pkg/name).stat().st_size))+r'\s'
            if not re.search(expected,p.read_text(encoding='utf-8-sig')):raise RuntimeError('Audit chunk receipt differs')
        rows.append(dict(path=name,sha256=sha(pkg/name),receipt_sha256=sha(final),chunks=count))
    syntax=ROOT/'tmp/m400/owner_audit_syntax.log'
    if '__M400_OWNER_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Root bash-n absent')
    out=BASE/'runs/M400-owner-audit-transfer-01/RESULT.json'
    value=dict(status='PASS_READONLY_AUDIT_BOUNDED_TRANSFER',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               files=rows,syntax_receipt_sha256=sha(syntax),new_overlay_loads=0,new_DMA_allocations=0,
               owner_release_performed=False,source_sha256=sha(HERE/'m400_owner_audit_transfer.py'))
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_owner_audit_transfer',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 原owner只读包传输核对（2026-10-04）\n\nSHA `{d}`；manifest-first/900B全部顺序字节和每文件完整SHA、root bash-n通过；原挂起owner/七DMA未释放。下一步一次只读proc/源码重现调查，不执行模型或Overlay，不由寄存器快照直接回收。')
    print(json.dumps(dict(status=value['status'],sha256=d)))


if __name__=='__main__':main()
