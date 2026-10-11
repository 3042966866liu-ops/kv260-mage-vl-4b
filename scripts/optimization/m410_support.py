"""Actual saved exporter/collector/receipts, explicit synthetic lower-gate records."""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile
from types import SimpleNamespace
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m410_workflow as w
def main():
    pkg=w.PKG;manifest=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');case=json.loads((pkg/'BOARD_CASES.json').read_bytes())
    for row in manifest['files']:assert sha(pkg/row['path'])==row['sha256']
    header=json.loads((BASE/'runs/M357-activation-bank-preparation-01/RESULT.json').read_bytes());assert header['missing']==[]
    spec=importlib.util.spec_from_file_location('m410_actual_exporter',pkg/'m410_export.py');producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
    temp_root=ROOT/'tmp/m41001/support';temp_root.mkdir(parents=True,exist_ok=True);rejects=0
    with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
        folder=__import__('pathlib').Path(temporary);producer.EVIDENCE=folder/'board';producer.os=SimpleNamespace(geteuid=lambda:0);producer.time=SimpleNamespace(sleep=lambda _:None)
        def export(value):
            p=producer.EVIDENCE/value['gate_level']/'BOARD_RESULT.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encoded(value));output=io.StringIO()
            with contextlib.redirect_stdout(output):producer.emit_saved(value['gate_level'])
            return output.getvalue()+f'M410_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        snap=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
        for mode in w.MODES:
            fail=dict(status='FAIL_M410_'+mode.upper(),gate_return_code=1,gate_level=mode,build_id='0x4D333537',manifest_sha256=digest,errors=['EXPLICIT early synthetic failure'],performance_pass=False,full_model=False,video=False,promoted=False)
            prior='1'*64 if mode=='Chain' else None
            if prior:fail['prior_raw_sha256']=prior
            assert w.decode(export(fail),mode,prior)[2]==fail
            selected=case['cases'][mode];rows=[];alloc=[]
            for i,label in enumerate(('candidate-legal-build-id','visual-'+mode.lower(),'stable-restored-build-id')):
                saved=selected['saved_batch'] if i==1 else case['build_bytes'];build=0x4d395832 if i==2 else 0x4d333537
                rows.append(dict(label=label,build_id=hex(build),config=selected['chain']['config'] if i==1 else case['build_config'],**saved,expected_sha256=saved['raw_sha256'],output_sha256=saved['raw_sha256'],full_output_exact=True,completed_snapshot=dict(snap,ap_return=build),wait_ns=1000))
                for k in range(6):alloc.append(dict(label=label,bytes=16,address=0x10000000+i*1024+k*16))
            releases=[]
            for i in range(0,18,6):releases.extend(reversed(alloc[i:i+6]))
            good=dict(fail,status='PASS_M410_'+mode.upper(),gate_return_code=0,errors=[],package_verified=True,numerical_pass=True,safe_buffers_released=True,stable_restored=True,boot_unchanged=True,cmdline_unchanged=True,unsafe_dma_buffers_retained=False,
                stable_sources_verified=len(case['stable_sources']),hardware_closure_sha256=sha(pkg/'HARDWARE_CLOSURE.json'),transactions=rows,physical_transactions_started=3,
                saved_reference=dict(reference_raw_sha256=case['reference_raw_sha256'],part=selected['part'],selected_shift=selected['shift'],packet_sha256=selected['saved_batch']['packet_sha256'],raw_sha256=selected['saved_batch']['raw_sha256']),
                allocations=alloc,releases=releases,memory=[dict(CmaFree=256<<20,MemAvailable=1<<30,required_cma_free_bytes=64<<20) for _ in range(6)],
                overlay_loads=[dict(build_id='0x4d333537'),dict(build_id='0x4d395832')],final_snapshot=dict(snap,ap_return=0x4d395832))
            complete=export(good);assert w.decode(complete,mode,prior)[2]==good
            mutations=[]
            for k,v in [('manifest_sha256','0'*64),('gate_level','bad'),('numerical_pass',False),('performance_pass',True),('safe_buffers_released',False),('stable_restored',False),('unsafe_dma_buffers_retained',True),('physical_transactions_started',2),('releases',releases[:-1]),('memory',good['memory'][:-1]),('stable_sources_verified',0),('hardware_closure_sha256','0'*64)]:
                x=copy.deepcopy(good);x[k]=v
                if k=='gate_level':mutations.append(complete.replace('"notused"','"unused"')) if False else None;continue
                mutations.append(export(x))
            for k in range(7):
                x=copy.deepcopy(good)
                if k==0:x['transactions'][1]['output_sha256']='0'*64
                if k==1:x['transactions'][0]['completed_snapshot']['mm2s_dmasr']=0
                if k==2:x['transactions'][1]['packet_sha256']='0'*64
                if k==3:x['memory'][3]['CmaFree']=32<<20
                if k==4:x['memory'][3]['MemAvailable']=64<<20
                if k==5:x['saved_reference']['raw_sha256']='0'*64
                if k==6:x['overlay_loads'].append(dict(build_id='0x4d333537'))
                mutations.append(export(x))
            mutations += [complete+complete,complete.replace('M410_RESULT_CHUNK=1/','M410_RESULT_CHUNK=0/'),complete.replace('gate_rc=0 export_rc=0','gate_rc=1 export_rc=0'),complete[:complete.index('M410_RESULT_CHUNK=1/')]]
            if prior:mutations.append(export(dict(good,prior_raw_sha256='0'*64)))
            for txt in mutations:
                try:w.decode(txt,mode,prior)
                except (ValueError,KeyError,StopIteration):rejects+=1
                else:raise AssertionError('Invalid lower gate accepted')
            log=folder/(mode+'.log');log.write_text(complete,encoding='utf-8');called=[];destination=folder/mode/'BOARD_RESULT.json'
            assert w.collect(log,mode,prior,destination,sync_function=lambda *args:called.append(args))==good
            assert destination.read_bytes()==encoded(good) and called[0][0]=='latest_m410_visual_'+mode.lower()
            try:atomic(destination,b'changed',immutable=True)
            except RuntimeError:rejects+=1
            else:raise AssertionError('Immutable evidence overwritten')
        receipts=folder/'receipts';receipts.mkdir()
        for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
            prefix='upload_'+name.replace('.','_');size=(pkg/name).stat().st_size;count=(size+899)//900
            (receipts/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):(receipts/(prefix+f'_chunk_{i:04d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} '+name,encoding='utf-8')
        (receipts/'syntax.log').write_text('__M410_SYNTAX_RC_0__',encoding='utf-8');assert len(w.transfer(receipts,False)['files'])==manifest['file_count']+1
        next(receipts.glob('upload_*_chunk_*.log')).unlink()
        try:w.transfer(receipts,False)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Missing upload receipt accepted')
    psh=ROOT.__class__(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    test=subprocess.run([str(psh),'-NoProfile','-File',str(HERE/'m410_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert test.returncode==0 and b'M410_CONTROL_SELF_TEST_PASS' in test.stdout
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M410-visual-linear-01/run_m410_visual.sh'],capture_output=True)
    assert syntax.returncode==0,syntax.stderr
    value=dict(status='PASS_M410_ACTUAL_EXPORT_CONTROL_AND_RECOVERY',manifest_sha256=digest,negative_checks=rejects,actual_saved_export_PASS_early_FAIL=True,actual_atomic_destination_and_BOARD_keys=True,all_manifest_first_900B_receipts=True,missing_receipt_rejected=True,
        control_failure_collection_SelfTest=True,bash_n=True,original_recursive_header_missing=header['missing'],unchanged_hardware_evidence=True,fixtures_explicit_synthetic=True,board_or_performance_evidence=False,
        source_sha256={n:sha(HERE/n) for n in ('m410_support.py','m410_control.ps1','m410_workflow.py')})
    out=BASE/'runs/M410-visual-linear-support-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m410_visual_linear_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),
        f'## M410 视觉最小用例实际控制回收检查（2026-10-06）\n\nSHA {sha(out)}；原header missing=0、同SHA电路证据保持；实际已保存PASS/早期FAIL导出、两个目的地和BOARD键、{rejects}回收负例、manifest-first全部900B回执/缺失拒绝、控制故意失败仍收集及bash-n通过，明确合成fixture。下一步同COM3授权后只单descriptor，闭合同步后才双descriptor链；无新硬件/性能或24层结论。')
    print('M410_SUPPORT_SYNC',sha(out),rejects)
if __name__=='__main__':main()
