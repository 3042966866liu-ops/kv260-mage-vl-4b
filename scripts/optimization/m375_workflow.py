"""Versioned manifest-first transfer receipts; saved-byte collection only."""
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,encoded,atomic,sync
PKG=BASE/'candidates/M375-video-future-wait-01'
OLD=BASE/'candidates/M369-light-video-01'

def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    oldhashes={r['sha256'] for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files'] if r['sha256'] not in oldhashes]
    verified=[]
    for name in names:
        stem='tmp/m375/upload_'+name.replace('.','_')
        final=ROOT/(stem+'_final.log');text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise RuntimeError('File receipt missing')
        count=((PKG/name).stat().st_size+899)//900
        chunks=sorted((ROOT/'tmp/m375').glob('upload_'+name.replace('.','_')+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Chunk count differs')
        for i,path in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,(PKG/name).stat().st_size))+r'\s',path.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk order/length differs')
        verified.append(dict(path=name,sha256=sha(PKG/name),final_log_sha256=sha(final),chunks=count))
    assembly=ROOT/'tmp/m375/assembly_uart.log';syntax=ROOT/'tmp/m375/root_syntax_uart.log'
    text=assembly.read_text(encoding='utf-8-sig')
    if 'M375_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' not in text or '__M375_ASSEMBLY_RC_0__' not in text:raise RuntimeError('Assembly SHA/rc absent')
    if '__M375_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Root bash-n absent')
    out=BASE/'runs/M375-video-wait-transfer-01/RESULT.json'
    r=dict(status='PASS_MANIFEST_FIRST_900B_ALL_PAYLOAD_SHA_NO_GATE',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        new_files=verified,old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),assembly_log_sha256=sha(assembly),syntax_log_sha256=sha(syntax),board_gate_started=False)
    atomic(out,encoded(r),immutable=True);digest=sha(out)
    sync('latest_m375_video_wait_transfer',dict(status=r['status'],sha256=digest,result=out.relative_to(ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),
        f'## M375 窄视频等待包传输核对\n\nmanifest-first900B逐块/全SHA、同SHA旧依赖组装及root bash-n通过；尚无Overlay/forward。证据SHA {digest}。下一步唯一一次候选原视频观察，已有result/runlog只能Collect。')
    print('M375_TRANSFER_SYNCHRONIZED',digest)

if __name__=='__main__':
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':
        from m375_collect import collect
        collect(ROOT/sys.argv[2])
    else:raise SystemExit('transfer | collect logpath')
