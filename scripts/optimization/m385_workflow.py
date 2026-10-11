"""Controller receipts and recovery only; no hardware execution."""
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,encoded,atomic,sync
PKG=BASE/'candidates/M385-ps-layer-02'
OLD=BASE/'candidates/M384-ps-chain-01'

def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files'] if old.get(r['path'])!=r]
    verified=[]
    for name in names:
        stem='tmp/m385/upload_'+name.replace('.','_')
        final=ROOT/(stem+'_final.log')
        text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise RuntimeError('File receipt missing')
        count=((PKG/name).stat().st_size+899)//900
        chunks=sorted((ROOT/'tmp/m385').glob('upload_'+name.replace('.','_')+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Transfer chunk count differs')
        for i,path in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,(PKG/name).stat().st_size))+r'\s',path.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk receipt differs')
        verified.append(dict(path=name,sha256=sha(PKG/name),final_log_sha256=sha(final),chunks=count))
    assembly=ROOT/'tmp/m385/assembly_uart.log';syntax=ROOT/'tmp/m385/root_syntax_uart.log'
    if 'M385_ASSEMBLY_SHA_PASS '+sha(PKG/'PACKAGE_MANIFEST.json') not in assembly.read_text(encoding='utf-8-sig') or '__M385_ASSEMBLY_RC_0__' not in assembly.read_text(encoding='utf-8-sig'):raise RuntimeError('Board package SHA absent')
    if '__M385_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Root bash-n absent')
    path=BASE/'runs/M385-ps-layer-transfer-01/RESULT.json'
    r=dict(status='PASS_MANIFEST_FIRST_900B_AND_EXACT_PRIOR_DEPENDENCIES',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        new_files=verified,old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),assembly_log_sha256=sha(assembly),syntax_log_sha256=sha(syntax),
        overlay_loaded=False,model_forward_calls=0,board_gate_started=False)
    atomic(path,encoded(r),immutable=True);digest=sha(path)
    sync('latest_m385_ps_layer_transfer',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M385 PS单层五窗口诊断包传输核对（2026-10-03）\n\nmanifest-first/900B全部新字节逐块及全SHA通过；未变依赖只从精确M384已验证包复制，31载荷完整白名单/字节/逐SHA/root bash-n通过。尚未Overlay/forward。证据 SHA {digest}；下一步一次PS暂存单层五窗口完整输出数值门禁，已有result/runlog只能Collect。')
    print('M385_TRANSFER_SYNCHRONIZED',digest)

if __name__=='__main__':
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':
        from m385_collect import collect
        collect(ROOT/sys.argv[2])
    else:raise SystemExit('transfer | collect logpath')
