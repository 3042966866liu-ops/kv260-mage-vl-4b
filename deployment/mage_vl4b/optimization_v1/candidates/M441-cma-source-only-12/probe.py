"""Read installed source and metadata only; never import PYNQ or program FPGA."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

def read(path,limit=262144):
    path=Path(path)
    try:
        size=path.stat().st_size
        with path.open('rb') as f:raw=f.read(limit+1)
        if len(raw)>limit:raise RuntimeError('Read bound exceeded')
        return dict(path=str(path),bytes=size,sha256=hashlib.sha256(raw).hexdigest(),text=raw.decode('utf-8'))
    except (OSError,UnicodeError,RuntimeError) as e:
        return dict(path=str(path),unavailable=repr(e))

def main():
    assert os.geteuid()==0
    assert len(sys.argv)==2 and hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==sys.argv[1]
    candidates=[Path(p)/'pynq' for p in sys.path if p and (Path(p)/'pynq/overlay.py').is_file()]
    assert len(candidates)==1,repr(candidates)
    root=candidates[0]
    specs={'overlay.py':{'__init__','download'},'bitstream.py':{'download'},
           'pl_server/embedded_device.py':{'download','_preload_binfile'},
           'pl_server/xrt_device.py':{'_xrt_download','allocate_bo'},
           'pl_server/device.py':{'post_download'}}
    sources=[]
    for rel,names in specs.items():
        item=read(root/rel)
        if 'text' in item:
            text=item.pop('text');lines=text.splitlines();tree=ast.parse(text)
            item['functions']=[dict(name=n.name,line=n.lineno,source='\n'.join(lines[n.lineno-1:n.end_lineno])) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
        sources.append(item)
    r=dict(status='M441_CMA_INSTALLED_SOURCE_READ_ONLY',source_sha256=sys.argv[1],kernel=platform.uname()._asdict(),page_size=os.sysconf('SC_PAGE_SIZE'),sources=sources,
           metadata=[read(p) for p in ['/proc/version','/proc/cmdline','/sys/class/fpga_manager/fpga0/name','/sys/class/fpga_manager/fpga0/state','/sys/kernel/tracing/available_events']],
           counters=[read(p) for p in sorted(Path('/sys/kernel/mm/cma').glob('*/*')) if p.name in ('alloc_pages_success','alloc_pages_fail','release_pages')],
           resource_imports=False,overlay_calls=0,allocations=0,fpga_transactions=0,temperature_read=False)
    raw=(json.dumps(r,ensure_ascii=True,separators=(',',':'))+'\n').encode()
    assert len(raw)<=128*1024
    out=Path('/home/ubuntu/m441_cma_source_evidence_12')
    out.mkdir(exist_ok=False)
    f=out/'RESULT.json';f.write_bytes(raw)
    print('M441C_SOURCE_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,part in enumerate(parts):
        print('M441C_SOURCE_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode(),flush=True)
        time.sleep(.02)
    print('M441C_SOURCE_DONE',flush=True)

if __name__=='__main__':main()
