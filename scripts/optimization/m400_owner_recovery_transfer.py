"""Record each bounded CPU-sentinel upload receipt before Run."""
import json
import re
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    pkg=BASE/'candidates/M400-controlled-owner-recovery-01'
    m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());rows=[]
    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files']]:
        prefix='owner_recovery_upload_'+name.replace('.','_')
        final=ROOT/'tmp/m400'/(prefix+'_final.log');text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(pkg/name) not in text or '__M75C_UART_RC_0__' not in text:
            raise RuntimeError('Sentinel complete SHA receipt absent')
        count=((pkg/name).stat().st_size+899)//900
        chunks=sorted((ROOT/'tmp/m400').glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Sentinel chunk count differs')
        for i,p in enumerate(chunks,1):
            expected=r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,(pkg/name).stat().st_size))+r'\s'
            if not re.search(expected,p.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk byte/order differs')
        rows.append(dict(path=name,sha256=sha(pkg/name),chunks=count,receipt_sha256=sha(final)))
    syntax=ROOT/'tmp/m400/owner_recovery_syntax.log'
    if '__M400_RECOVER_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Root bash-n absent')
    out=BASE/'runs/M400-controlled-owner-recovery-transfer-01/RESULT.json'
    r=dict(status='PASS_CONTROLLED_OWNER_RECOVERY_BOUNDED_TRANSFER',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=rows,
           original_owner_attached=False,new_overlay_loads=0,new_DMA_allocations=0,syntax_receipt_sha256=sha(syntax))
    atomic(out,encoded(r),immutable=True);d=sha(out)
    sync('latest_m400_controlled_owner_recovery_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),
         f'## M400 原owner协作回收上传核对（2026-10-04）\n\nSHA `{d}`；manifest-first/900B全部顺序/字节/完整SHA及root bash-n通过。仅独立原owner协作回收，原PID22715/七DMA仍挂起；未附加原owner、未加载Overlay或DMA。下一步只运行一次已授权原owner协作回收；原close逐块检查，失败保留。')
    print(r['status'],d)


if __name__=='__main__':main()
