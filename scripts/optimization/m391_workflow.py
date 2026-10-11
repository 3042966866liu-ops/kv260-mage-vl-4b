"""Record bounded manifest-first CPU package transfer or collect saved bytes."""
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
PKG=BASE/'candidates/M391-silu-real-input-component-01'

def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
        prefix='upload_'+name.replace('.','_');folder=ROOT/'tmp/m391';p=folder/(prefix+'_final.log')
        text=p.read_text(encoding='utf-8-sig');size=(PKG/name).stat().st_size
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise RuntimeError('Full file receipt missing')
        count=(size+899)//900;paths=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(paths)!=count:raise RuntimeError('Chunk count missing')
        for i,piece in enumerate(paths,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',piece.read_text(encoding='utf-8-sig')):raise RuntimeError('Sequence/size receipt missing')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count,receipt_sha256=sha(p)))
    syntax=ROOT/'tmp/m391/runner_syntax_uart.log'
    assert '__M391_SYNTAX_RC_0__' in syntax.read_text(encoding='utf-8-sig')
    value=dict(status='PASS_M391_BOUNDED_CPU_PACKAGE_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,syntax_sha256=sha(syntax),board_gate_started=False)
    p=BASE/'runs/M391-cpu-transfer-01/RESULT.json';atomic(p,encoded(value),immutable=True);d=sha(p)
    sync('latest_m391_silu_transfer',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=p.relative_to(ROOT).as_posix(),sha256=d),
         f'## M391 CPU组件传输核对（2026-10-04）\n\nmanifest-first/900B各文件完整SHA与逐块/root bash-n核对，SHA {d}。尚未运行算子，下一步一次CPU-only真实数组组件，不加载Overlay；已有result/runlog只能Collect。')
    print('M391_TRANSFER_SYNCHRONIZED',d)

if __name__=='__main__':
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':
        from m391_collect import collect
        collect(ROOT/sys.argv[2])
    else:raise SystemExit('transfer | collect logpath')
