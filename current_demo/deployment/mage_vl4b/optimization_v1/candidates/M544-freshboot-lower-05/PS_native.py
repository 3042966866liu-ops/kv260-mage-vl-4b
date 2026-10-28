"""Native A53 packet boundary over saved CSim goldens; zero hardware/model."""
import ast,base64,hashlib,importlib.util,json,os,sys,time,traceback,zlib
from pathlib import Path
sys.dont_write_bytecode=True

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def persist(p,value):
    p=Path(p);raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    tmp=p.with_suffix('.partial')
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    assert not p.exists();os.rename(tmp,p)
def emit(raw):
    packed=zlib.compress(raw,9);assert len(raw)<=4<<20 and len(packed)<=4<<20
    print('M523_SHAPE_RAW_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M523_SHAPE_Z_SHA256='+hashlib.sha256(packed).hexdigest(),flush=True)
    chunks=[packed[i:i+480] for i in range(0,len(packed),480)]
    for i,b in enumerate(chunks):
        print('M523_SHAPE_Z_PART='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)

def main():
    here=Path(__file__).resolve().parent;expected=sys.argv[1];assert len(sys.argv)==2
    out=Path('/dev/shm/m544_freshboot_lower05_PS_evidence');assert not out.exists();out.mkdir(mode=0o700)
    result=dict(status='FAIL_M455_ADAPTIVE_NATIVE_PS_BOUNDARY',primary_rc=1,errors=[],cases=[],
        models=0,Overlay=0,DMA=0,privileged_actions=0,source_sha256=sha(__file__),manifest_sha256=expected)
    try:
        assert sha(here/'PACKAGE_MANIFEST.json')==expected;m=read(here/'PACKAGE_MANIFEST.json')
        names={r['path'] for r in m['files']};assert len(names)==m['file_count']
        assert {p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file()}==names|{'PACKAGE_MANIFEST.json'}
        assert sum(r['bytes'] for r in m['files'])==m['total_bytes']
        for r in m['files']:
            rel=Path(r['path']);assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in r['path']
            p=here/rel;assert not p.is_symlink() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        plan=read(here/'PLAN.json');csim=read(here/'P1_CSIM_RESULT.json')
        assert sha(here/'P1_CSIM_RESULT.json')==plan['CSim_sha256'] and csim['status']=='PASS_M455_ADAPTIVE_FOUR_VECTOR_CSIM_ONLY' and csim['original_rc']==0
        import numpy as np
        spec=importlib.util.spec_from_file_location('_m523_adaptive_native_loader',here/'m455_private_runtime_loader01.py')
        loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
        factory=loader.load_private(here/'private_runtime',plan['private_manifest_sha256'],namespace='_m455_adaptive_PS_native52301')
        cls=factory['runtime_class'];base=factory['base'];contract=factory['contract']
        src=here/'SiLU_source.py';assert sha(src)==plan['SiLU_source_sha256']
        nodes=[n for n in ast.parse(src.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='silu'];assert len(nodes)==1
        namespace={'np':np};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(src),'exec'),namespace)
        x=np.frombuffer((here/'input_FP32.bin').read_bytes(),np.float32).reshape(32,2560);assert np.isfinite(x).all()
        for entry in plan['variants']:
            name=entry['name'];gu,down=entry['gate_up'],entry['down']
            gu_shift=base.M120BoardRuntime._initial_scale_shift(x)
            packet=cls._prepare_block(gu,x,0,0,gu_shift).packet
            gu_equal=hashlib.sha256(packet).hexdigest()==entry['gate_up_packet_sha256']
            outputs=contract.parse_chain_output(gu,(here/name/'gate_up_golden.bin').read_bytes(),output_scale_shift=6)
            middle=namespace['silu'](outputs['gate'])*outputs['up'];assert middle.dtype==np.float32 and np.isfinite(middle).all()
            down_shift=base.M120BoardRuntime._initial_scale_shift(middle)
            actual=cls._prepare_block(down,middle,0,0,down_shift).packet
            saved=(here/name/'down_packet.bin').read_bytes();equal=actual==saved
            path=out/(name+'_Down_packet.bin')
            with path.open('xb') as f:f.write(actual);f.flush();os.fsync(f.fileno())
            values=out/(name+'_middle_FP32.bin')
            with values.open('xb') as f:f.write(middle.tobytes());f.flush();os.fsync(f.fileno())
            result['cases'].append(dict(variant=name,GateUp_shift=gu_shift,GateUp_packet_equal=gu_equal,
                Down_shift=down_shift,Down_packet_equal=equal,changed_bytes=sum(a!=b for a,b in zip(actual,saved)),
                actual_Down_packet_sha256=sha(path),expected_Down_packet_sha256=entry['down_packet_sha256'],
                actual_middle_sha256=sha(values),packet_bytes=len(actual),middle_bytes=values.stat().st_size,
                saved_packet=path.name,saved_middle=values.name))
        passed=all(c['GateUp_shift']==c['Down_shift']==6 and c['GateUp_packet_equal'] and c['Down_packet_equal'] for c in result['cases'])
        result.update(status='PASS_M455_ADAPTIVE_NATIVE_PS_BOUNDARY_ONLY' if passed else 'FAIL_M455_ADAPTIVE_NATIVE_PS_PACKET_MISMATCH',primary_rc=0 if passed else 1)
    except BaseException:result['errors'].append(traceback.format_exc())
    persist(out/'BOARD_RESULT.json',result);emit((out/'BOARD_RESULT.json').read_bytes());return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
