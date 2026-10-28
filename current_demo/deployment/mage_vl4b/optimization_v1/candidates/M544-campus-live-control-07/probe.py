"""A53 software-delta import and scheduling fixtures, zero model/Overlay/DMA."""
import base64,hashlib,json,os,sys,time,traceback,zlib
from pathlib import Path
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def main():
    assert len(sys.argv)==4 and sys.flags.isolated and os.geteuid()==0
    control=Path(__file__).resolve().parent;pkg=Path('/dev/shm/m544_live_worker_package07')
    lower=Path('/dev/shm/m523_M455_twentytwo_local_package322');original=Path('/dev/shm/m523_PS3072_ttft_package01')
    assets=Path('/dev/shm/m523_M455_full22_request_package335/assets');release=Path('/home/ubuntu/tellme_release_install_20260926')
    out=Path('/dev/shm/m544_live_worker_import07/Import');assert not out.exists();out.mkdir(parents=True)
    value=dict(status='FAIL_A53_FIXED_DEMO_SUBSET_IMPORT_COMPONENT',primary_rc=1,errors=[],model_constructors=0,model_forwards=0,Overlay=0,DMA=0)
    try:
        assert sha(control/'PACKAGE_MANIFEST.json')==sys.argv[1] and sha(__file__)==sys.argv[3]
        for folder,expected in ((control,sys.argv[1]),(pkg,sys.argv[2])):
            assert sha(folder/'PACKAGE_MANIFEST.json')==expected;m=read(folder/'PACKAGE_MANIFEST.json')
            assert {f.relative_to(folder).as_posix() for f in folder.rglob('*') if f.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
            for row in m['files']:
                f=folder/row['path'];assert not f.is_symlink() and f.stat().st_nlink==1 and f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
                if f.suffix=='.py':compile(f.read_text(encoding='utf-8'),str(f),'exec')
        plan=read(pkg/'DEMO_BOARD_PLAN.json');assert sha(original/'PACKAGE_MANIFEST.json')==plan['original_component_manifest_sha256']
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==plan['expected_boot'] and os.uname().machine=='aarch64'
        denied=[]
        def guard(event,args):
            bad=event in ('subprocess.Popen','os.system','os.kill','os.fork','os.posix_spawn') or event.startswith('socket.')
            if event=='open' and args and isinstance(args[0],(str,bytes)):bad=bad or os.fsdecode(args[0]).startswith(('/dev/mem','/dev/dri/','/dev/uio','/sys/class/fpga'))
            if bad:denied.append(event);raise RuntimeError('CPU import/component denied device/process effect: '+event)
        sys.addaudithook(guard)
        sys.path[:0]=[str(pkg),str(original),str(lower),str(lower/'runtime'),str(assets/'reference')]+[r['directory'] for r in read(assets/'PLAN.json')['visual_reused_packages']]
        import board_demo_trial,board_subset,board_visual_subset,board_component
        assert Path(board_demo_trial.__file__).resolve()==pkg/'board_demo_trial.py'
        spec=__import__('importlib.util',fromlist=['']).spec_from_file_location('_fixed_demo_delta_native_import',pkg/'native.py');entry=__import__('importlib.util',fromlist=['']).module_from_spec(spec);spec.loader.exec_module(entry)
        assert callable(entry.main)
        expected=read(original/'PRIOR_IMPORT_AUDIT.json')['imports']['tokenizers'];init=Path(expected['path']);assert sha(init)==expected['init_sha256'];sys.path.insert(0,str(init.parent.parent))
        import tokenizers
        assert tokenizers.__version__==expected['version'] and Path(tokenizers.__file__).resolve()==init.resolve()
        from M455_four_block_request523366 import render
        tokenizer=release/'deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json';task=read(original/'TASK_CONTRACT.json');assert sha(tokenizer)==task['tokenizer_sha256']
        actual=tokenizers.Tokenizer.from_file(str(tokenizer)).encode(render(),add_special_tokens=False).ids
        assert actual==plan['token_ids']==task['token_ids'] and len(actual)==128 and actual.count(151655)==98
        value['CPU_components']=board_component.check(pkg,original,release)
        value['PS_component_vision_constructors']=1
        value['complete_model_constructors']=0
        import completion_boundary
        value['unchanged_completion_rejection_components']=completion_boundary.tests()
        assert not denied
        value.update(status='PASS_A53_M543_REPAIRED_DEMO_COMPONENT_ZERO_FPGA',primary_rc=0,package_manifest_sha256=sys.argv[2],source_sha256=sha(__file__),boot_id=plan['expected_boot'],denied_events=denied)
    except BaseException:value['errors'].append(traceback.format_exc())
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    with (out/'BOARD_RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    packed=zlib.compress(raw,9);print('M523_SHAPE_RAW_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True);print('M523_SHAPE_Z_SHA256='+hashlib.sha256(packed).hexdigest(),flush=True)
    pieces=[packed[i:i+480] for i in range(0,len(packed),480)]
    for i,b in enumerate(pieces):print('M523_SHAPE_Z_PART='+str(i)+'/'+str(len(pieces))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)
    return value['primary_rc']
if __name__=='__main__':raise SystemExit(main())
