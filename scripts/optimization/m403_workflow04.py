"""Versioned transfer receipt / saved-result dispatch only."""
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
PKG=BASE/'candidates/M403-tail-performance-01'
OLD=BASE/'candidates/M395-silu-performance-01'


def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files'] if old.get(r['path'])!=r]
    verified=[]
    for name in names:
        prefix='upload_'+name.replace('.','_')
        final=ROOT/'tmp/m403'/(prefix+'_final.log')
        text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise RuntimeError('Missing exact file receipt')
        count=((PKG/name).stat().st_size+899)//900
        paths=sorted((ROOT/'tmp/m403').glob(prefix+'_chunk_*.log'))
        if len(paths)!=count:raise RuntimeError('Chunk receipt count differs')
        for i,p in enumerate(paths,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,(PKG/name).stat().st_size))+r'\s',p.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk sequence/byte receipt differs')
        verified.append(dict(path=name,sha256=sha(PKG/name),chunks=count,receipt_sha256=sha(final)))
    assembly=ROOT/'tmp/m403/assembly02_uart.log';syntax=ROOT/'tmp/m403/root_syntax02_uart.log'
    assert 'M403_ASSEMBLY_SHA_PASS '+sha(PKG/'PACKAGE_MANIFEST.json') in assembly.read_text(encoding='utf-8-sig') and '__M403_ASSEMBLY_RC_0__' in assembly.read_text(encoding='utf-8-sig')
    assert '__M403_SYNTAX_RC_0__' in syntax.read_text(encoding='utf-8-sig')
    value=dict(status='PASS_M403_MANIFEST_FIRST_BOUNDED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),new_files=verified,old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),assembly_sha256=sha(assembly),syntax_sha256=sha(syntax),board_gate_started=False)
    p=BASE/'runs/M403-tail-performance-transfer-01/RESULT.json';atomic(p,encoded(value),immutable=True);d=sha(p)
    sync('latest_m403_tail_performance_transfer',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),f'## M403 末层性能包传输核对（2026-10-04）\n\nmanifest-first/900B新载荷全部逐块与完整SHA，未变依赖只从精确M395复制，完整白名单/大小/root bash-n通过，SHA {d}。尚未Overlay/模型/FPGA；下一步一次同核完整末层/末T32裁剪ABBABAAB轻量请求对照，已有原run日志或结果只能收集。')
    print('M403_TRANSFER_SYNCHRONIZED',d)


if __name__=='__main__':
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':
        from m403_collect import collect
        collect(ROOT/sys.argv[2])
    else:raise SystemExit('transfer | collect logpath')
