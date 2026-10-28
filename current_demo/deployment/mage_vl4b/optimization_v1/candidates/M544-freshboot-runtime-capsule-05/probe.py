"""A53 import-only check for the new complete-request entry; no constructor."""
import base64,hashlib,importlib.util,json,os,sys,time,traceback,zlib
from pathlib import Path
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def main():
    assert len(sys.argv)==4 and sys.flags.isolated and os.geteuid()==0
    control=Path(__file__).resolve().parent;pkg=Path('/dev/shm/m523_PS3072_ttft_package01')
    lower=Path('/dev/shm/m523_M455_twentytwo_local_package322');assets=Path('/dev/shm/m523_M455_full22_request_package335/assets')
    out=Path('/dev/shm/m523_PS3072_ttft_import01/Import');assert not out.exists();out.mkdir(parents=True)
    v=dict(status='FAIL_A53_NEW_NATIVE_PAIR_ENTRY_IMPORT',primary_rc=1,errors=[],model_constructors=0,model_forwards=0,Overlay=0,DMA=0)
    try:
        assert sha(control/'PACKAGE_MANIFEST.json')==sys.argv[1] and sha(__file__)==sys.argv[3]
        for root,expected in ((control,sys.argv[1]),(pkg,sys.argv[2])):
            assert sha(root/'PACKAGE_MANIFEST.json')==expected;m=read(root/'PACKAGE_MANIFEST.json')
            assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
            for r in m['files']:
                f=root/r['path'];assert not f.is_symlink() and f.stat().st_nlink==1 and f.stat().st_size==r['bytes'] and sha(f)==r['sha256']
                if f.suffix=='.py':compile(f.read_text(encoding='utf-8'),str(f),'exec')
        denied=[]
        def guard(event,args):
            bad=event in ('subprocess.Popen','os.system','os.kill','os.fork','os.posix_spawn') or event.startswith('socket.')
            if event=='open' and args and isinstance(args[0],(str,bytes)):bad=bad or os.fsdecode(args[0]).startswith(('/dev/mem','/dev/dri/','/dev/uio','/sys/class/fpga'))
            if bad:denied.append(event);raise RuntimeError('A53 entry import denied side effect: '+event)
        sys.addaudithook(guard)
        sys.path[:0]=[str(pkg),str(lower),str(lower/'runtime'),str(assets/'reference')]+[r['directory'] for r in read(assets/'PLAN.json')['visual_reused_packages']]
        import PS3072_trial as adapter
        import m455_configuration_retry02,b0_configuration_retry02,retry_component
        assert Path(m455_configuration_retry02.__file__).resolve()==pkg/'m455_configuration_retry02.py'
        assert Path(b0_configuration_retry02.__file__).resolve()==pkg/'b0_configuration_retry02.py'
        v['CMA_retry_components']=retry_component.tests(pkg)
        spec=importlib.util.spec_from_file_location('_new_native_pair_main_only',pkg/'native.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
        assert Path(adapter.__file__).resolve()==pkg/'PS3072_trial.py' and callable(entry.main) and not denied
        expected_tokenizers=read(pkg/'PRIOR_IMPORT_AUDIT.json')['imports']['tokenizers']
        expected_init=Path(expected_tokenizers['path'])
        assert sha(expected_init)==expected_tokenizers['init_sha256']
        sys.path.insert(0,str(expected_init.parent.parent))
        import tokenizers
        assert Path(tokenizers.__file__).resolve()==expected_init.resolve()
        assert tokenizers.__version__==expected_tokenizers['version'] and sha(tokenizers.__file__)==expected_tokenizers['init_sha256']
        from M455_four_block_request523366 import render
        from M455_request_guard52354 import physical_bound
        task=read(pkg/'TASK_CONTRACT.json');plan=read(pkg/'REQUEST_PLAN.json')
        tokenizer=Path('/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json')
        assert sha(tokenizer)==task['tokenizer_sha256'] and sha(pkg/'TASK_CONTRACT.json')==plan['task_contract_sha256']
        actual_ids=tokenizers.Tokenizer.from_file(str(tokenizer)).encode(render(),add_special_tokens=False).ids
        assert actual_ids==task['token_ids']==plan['token_ids'] and len(actual_ids)==128 and actual_ids.count(151655)==98
        assert physical_bound(128,32,visual=True)==41524
        assert os.uname().machine=='aarch64' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='f425c270-dc5e-4a1d-98de-025c85938620'
        assert len(plan['language'])==19 and set(plan['visual'])=={'14','15','21'}
        import completion_boundary,PS_A53_component
        v['completion_components']=completion_boundary.tests()
        assert plan['new_full_model_forwards_budget']==6 and len(plan['PS3072_ttft']['schedule'])==6
        v['PS_component']=PS_A53_component.check(pkg)
        v.update(status='PASS_A53_PS3072_TTFT_IMPORT_AND_LOCAL_MLP_ZERO_MODEL',primary_rc=0,package_manifest_sha256=sys.argv[2],
            native_A53=os.uname().machine=='aarch64',source_sha256=sha(__file__),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),denied_events=denied)
    except BaseException:v['errors'].append(traceback.format_exc())
    raw=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (out/'BOARD_RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    packed=zlib.compress(raw,9);print('M523_SHAPE_RAW_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True);print('M523_SHAPE_Z_SHA256='+hashlib.sha256(packed).hexdigest(),flush=True)
    chunks=[packed[i:i+480] for i in range(0,len(packed),480)]
    for i,b in enumerate(chunks):print('M523_SHAPE_Z_PART='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)
    return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
