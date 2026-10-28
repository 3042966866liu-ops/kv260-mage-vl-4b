"""Actual native closed import/compile, no constructor or device API call."""
import base64,hashlib,importlib,json,os,sys,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    root=Path('/dev/shm/m523_M455_twentytwo_local_package322');digest=sys.argv[1]
    out=Path('/dev/shm/m523_M455_full22_import327');assert not out.exists();out.mkdir()
    v=dict(status='FAIL_M455_P1_NATIVE_IMPORT_ONLY',primary_rc=1,models=0,Overlay=0,DMA=0,errors=[],modules={},manifest_sha256=digest)
    try:
        assert sha(root/'PACKAGE_MANIFEST.json')==digest
        m=json.loads((root/'PACKAGE_MANIFEST.json').read_bytes());rows=m['files']
        assert len(rows)==m['file_count'] and sum(r['bytes'] for r in rows)==m['total_bytes']
        assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
        for r in rows:
            p=root/r['path'];assert not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
            if p.suffix=='.py':compile(p.read_bytes(),str(p),'exec')
        sys.path[:0]=[str(root),str(root/'runtime')]
        for name in ('M455_full22_local_gate523319','M455_twentytwo_local_PS523317','board_runtime','m341_build_id_gate','m455_configuration01',
            'm455_board_clocks03','m455_completion_observer','b0_owners523','owned_buffer_release',
            'b0_transaction_guard523','board_safety','memory_lifecycle','b0_configuration523'):
            mod=importlib.import_module(name);p=Path(mod.__file__).resolve();p.relative_to(root)
            v['modules'][name]=dict(path=str(p),sha256=sha(p))
        assert sys.version_info[:2]==(3,10)
        v.update(status='PASS_M455_P1_NATIVE_IMPORT_ONLY',primary_rc=0)
    except BaseException:v['errors'].append(traceback.format_exc())
    raw=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (out/'BOARD_RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    print('M523_B0_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    parts=[raw[i:i+480] for i in range(0,len(raw),480)]
    for i,b in enumerate(parts):print('M523_B0_RESULT_PART='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)
    return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
