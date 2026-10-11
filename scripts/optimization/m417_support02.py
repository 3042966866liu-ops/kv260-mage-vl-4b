"""Actual exporter/collector/artifact/receipt checks with explicit synthetic records."""
import contextlib,copy,hashlib,importlib.util,io,json,re,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m417_workflow02 as workflow

def main():
    pkg=workflow.PKG;m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json')
    for row in m['files']:assert sha(pkg/row['path'])==row['sha256']
    sys.path.insert(0,str(pkg))
    spec=importlib.util.spec_from_file_location('m409_actual_producer_test',pkg/'m417_gate.py')
    producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
    temp_root=ROOT/'tmp/m41702/support';temp_root.mkdir(parents=True,exist_ok=True)
    rejects=0
    with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
        folder=Path(temporary);producer.OUTPUT=folder/'results/RESULT.json';producer.OUTPUT.parent.mkdir()
        producer.os=SimpleNamespace(geteuid=lambda:0,fsync=__import__('os').fsync,replace=__import__('os').replace)
        producer.time=SimpleNamespace(sleep=lambda _:None)
        old=sys.argv;sys.argv=['m417_gate.py']
        try:
            try:producer.main()
            except RuntimeError as e:assert 'Default-off' in str(e)
            else:raise AssertionError('Default-off bypass')
        finally:sys.argv=old
        # Actual saved-capture loader with self-owned finite files; corruption rejected.
        producer.CAPTURE=folder/'capture';producer.CAPTURE.mkdir();rows=[]
        for k,s in producer.SHAPES.items():
            p=producer.CAPTURE/(k+'.npy');np.save(p,np.ones(s,np.float32),allow_pickle=False)
            rows.append(dict(path=p.name,file_bytes=p.stat().st_size,file_sha256=sha(p),tensor=producer.tensor(np.load(p,allow_pickle=False))))
        atomic(producer.CAPTURE/'CAPTURE_MANIFEST.json',encoded(dict(files=rows)))
        custom=dict(capture_manifest=dict(sha256=sha(producer.CAPTURE/'CAPTURE_MANIFEST.json'),files=rows))
        assert set(producer.load_capture(custom,np))==set(producer.SHAPES)
        p=producer.CAPTURE/rows[0]['path'];saved=p.read_bytes();p.write_bytes(saved[:-1]+bytes([saved[-1]^1]))
        try:producer.load_capture(custom,np)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Corrupt capture accepted')
        p.write_bytes(saved)
        # Actual artifact saver and size/whitelist limits.
        artifacts=[];buf=io.BytesIO();arr=np.ones((392,4096),np.float32);np.save(buf,arr,allow_pickle=False)
        producer.save_blob('fixture.npy',buf.getvalue(),artifacts)
        assert np.array_equal(np.load(producer.OUTPUT.parent/'fixture.npy',allow_pickle=False),arr) and artifacts[0]['sha256']==sha(producer.OUTPUT.parent/'fixture.npy')
        for name,blob in [('../escape.raw',b'x'),('too-large.raw',b'0'*((8<<20)+1))]:
            try:producer.save_blob(name,blob,artifacts)
            except RuntimeError:rejects+=1
            else:raise AssertionError('Artifact boundary accepted')
        expected=json.loads((pkg/'M416_CAPTURE_EXPECTED.json').read_bytes())
        bad=dict(status='FAIL_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',gate_return_code=1,errors=[dict(message='EXPLICIT SYNTHETIC failure')],
            manifest_sha256=digest,gate_level='PS-only-saved-input-exact-MLP-FTZ-reference',selected_layer=13,
            overlay_loaded=False,dma_allocations=0,fpga_transactions=0,visual_forward_calls=0,language_forward_calls=0,
            semantic_quality_proven=False,PL_hardware_proven=False,performance_pass=False,formal_promotion_allowed=False)
        quality={k:dict(shape=[392,4096 if k in ('fc1','gelu') else 1024],cosine=1.,relative_l2=0.,min_token_cosine=1.,RMSE=0.,max_abs=0.) for k in ('fc1','gelu','fc2','output','residual_sum')}
        chains=json.loads((pkg/'MLP_CHAINS.json').read_bytes())['chains'];batches={};arts=[]
        for part in ('fc1','fc2'):
            c=next(x for x in chains if x['module']==f'model.visual.encoder.layers.13.mlp.{part}');batches[part]=[]
            for start in range(0,392,32):
                dig={};
                for suffix,n in (('packet',c['input_bytes']),('raw',c['output_bytes'])):
                    blob=b'0'*n;d=hashlib.sha256(blob).hexdigest();dig[suffix]=d;arts.append(dict(path=f'{part}_{start:03d}_shift6.{suffix}',bytes=n,sha256=d))
                batches[part].append(dict(start=start,rows=min(32,392-start),initial_shift=6,selected_shift=6,attempted_shifts=[6],physical_reference_attempts=1,logical_calls=1,input_bytes=c['input_bytes'],output_bytes=c['output_bytes'],packet_sha256=dig['packet'],raw_sha256=dig['raw']))
        for k in ('input','fc1','gelu','fc2','output'):arts.append(dict(path=k+'.npy',bytes=1,sha256='0'*64))
        good=dict(bad,component_isolation=dict(separate_process=True,parent_state_unchanged=True,return_code=0),status='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',gate_return_code=0,errors=[],local_mlp_forward_calls=2,logical_reference_calls=26,
            original_replay_bit_exact=True,local_exact_arithmetic_screen_pass=True,bindings_restored=True,visual_owner_closed=True,no_pynq_import=True,
            capture_manifest_sha256=expected['capture_manifest']['sha256'],capture_source_raw_sha256=expected['raw_sha256'],capture_tensors=expected['capture'],target_matrices=expected['target_matrices'],target_resolution=expected['target_resolution'],
            component=dict(real_Torch_CPU=True,actual_M207_class=True,actual_SiglipMLP_GELU=True,native_single_batch_preserved=True,independent_int32_full_output_equal=True,nonzero_bias_PS_add=True,bindings_restored=True,invalid_native_inputs_rejected=4,T32_partial_rows=[32,8]),
            source_identities_verified=49,quality_metrics=quality,boundary_residual_bf16=quality['residual_sum'],reference_batches=batches,physical_reference_attempts=26,artifacts=arts,backend_before={},backend_after={},elapsed_s_diagnostic_not_performance=1)
        def export(value):
            producer.OUTPUT.write_bytes(encoded(value));stream=io.StringIO()
            with contextlib.redirect_stdout(stream):producer.export()
            return stream.getvalue()+f'M417_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        complete=export(good);assert workflow.decode(complete)[2]==good and workflow.decode(export(bad))[2]==bad
        mutations=[]
        for k,v in [('manifest_sha256','0'*64),('selected_layer',11),('bindings_restored',False),('visual_owner_closed',False),('original_replay_bit_exact',False),('local_exact_arithmetic_screen_pass',False),('fpga_transactions',1),('visual_forward_calls',1),('performance_pass',True),('PL_hardware_proven',True),('logical_reference_calls',25),('source_identities_verified',48),('physical_reference_attempts',27),('elapsed_s_diagnostic_not_performance',901),('capture_manifest_sha256','0'*64)]:
            obj=copy.deepcopy(good);obj[k]=v;mutations.append(export(obj))
        for change in range(6):
            obj=copy.deepcopy(good)
            if change==0:obj['quality_metrics']['fc2']['relative_l2']=.03
            if change==1:obj['reference_batches']['fc1'][-1]['rows']=32
            if change==2:obj['reference_batches']['fc2'][0]['attempted_shifts']=[6,4]
            if change==3:obj['artifacts'][0]['sha256']='f'*64
            if change==4:obj['artifacts'].pop()
            if change==5:obj['component']['invalid_native_inputs_rejected']=3
            mutations.append(export(obj))
        for k,v in [('separate_process',False),('parent_state_unchanged',False),('return_code',1)]:
            obj=copy.deepcopy(good);obj['component_isolation'][k]=v;mutations.append(export(obj))
        mutations += [complete+complete,complete.replace('M417_RESULT_CHUNK=1/','M417_RESULT_CHUNK=0/'),complete.replace('gate_rc=0 export_rc=0','gate_rc=1 export_rc=0'),complete[:complete.index('M417_RESULT_CHUNK=1/')]]
        for txt in mutations:
            try:workflow.decode(txt)
            except (ValueError,KeyError,StopIteration):rejects+=1
            else:raise AssertionError('Invalid result accepted')
        log=folder/'saved.log';log.write_text(complete,encoding='utf-8');called=[]
        destination=folder/'collected/BOARD_RESULT.json'
        r=workflow.collect(log,destination,sync_function=lambda *args:called.append(args))
        assert destination.read_bytes()==encoded(good) and called[0][0]=='latest_m417_reference_board02'
        try:atomic(destination,b'changed',immutable=True)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Immutable evidence overwritten')
        receipts=folder/'receipts';receipts.mkdir()
        for name in ['PACKAGE_MANIFEST.json']+json.loads((pkg/'TRANSFER_FILES.json').read_bytes())['files']:
            prefix='upload_'+name.replace('.','_');size=(pkg/name).stat().st_size;count=(size+899)//900
            (receipts/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):(receipts/(prefix+f'_chunk_{i:04d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} '+name,encoding='utf-8')
        # Execute the actual assembler, adapting only its two filesystem roots.
        import shutil
        from unittest.mock import patch
        old_packet=BASE/'candidates/M417-layer13-saved-reference-01'
        asmold=folder/'asmold';asmnew=folder/'asmnew'
        shutil.copytree(old_packet,asmold);asmnew.mkdir()
        names=['PACKAGE_MANIFEST.json']+json.loads((pkg/'TRANSFER_FILES.json').read_bytes())['files']
        for name in names:shutil.copyfile(pkg/name,asmnew/name)
        assembler=(pkg/'assemble_m417.py').read_text(encoding='utf-8')
        assert assembler.count('HERE=Path(__file__).resolve().parent')==1 and assembler.count("OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')")==1
        fixture_code=assembler.replace('HERE=Path(__file__).resolve().parent','HERE=Path('+repr(str(asmnew))+')').replace("OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')",'OLD=Path('+repr(str(asmold))+')')
        def execute_assembler():
            old_argv=sys.argv;sys.argv=['assemble_m417.py',digest];output=io.StringIO()
            try:
                with patch('os.geteuid',return_value=0,create=True),contextlib.redirect_stdout(output):exec(compile(fixture_code,str(pkg/'assemble_m417.py'),'exec'),dict(__name__='explicit_self_owned_assembler_fixture'))
            finally:sys.argv=old_argv
            return output.getvalue()
        assembly_text=execute_assembler()
        assert all(sha(asmnew/r['path'])==r['sha256'] for r in m['files'])
        (receipts/'assembly.log').write_text(assembly_text,encoding='utf-8')
        witness=asmold/'EXPECTED.json';saved=witness.read_bytes();witness.write_bytes(saved+b'corruption')
        try:execute_assembler()
        except RuntimeError:rejects+=1
        else:raise AssertionError('Corrupt old source accepted')
        witness.write_bytes(saved)
        extra=asmnew/'unexpected';extra.write_bytes(b'extra')
        try:execute_assembler()
        except RuntimeError:rejects+=1
        else:raise AssertionError('Unexpected staging file accepted')
        extra.unlink()
        (receipts/'syntax.log').write_text('__M417_SYNTAX_RC_0__',encoding='utf-8')
        assert len(workflow.transfer(receipts,False)['files'])==len(names)
        missing=next(receipts.glob('upload_*_chunk_*.log'));missing.unlink()
        try:workflow.transfer(receipts,False)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Missing receipt accepted')
    psh=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    test=subprocess.run([str(psh),'-NoProfile','-File',str(HERE/'m417_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert test.returncode==0 and b'M417_CONTROL_SELF_TEST_PASS' in test.stdout
    PKG=workflow.PKG
    component_path=ROOT/'tmp/m41702/component/RESULT.json'
    checked=json.loads(component_path.read_bytes())
    assert checked['isolation']['parent_state_unchanged'] and checked['isolation']['return_code']==0
    assert checked['new_actual_packaged_entry'] and checked['isolated_parent'] and checked['old_missing_dependency_reproduced'] and checked['no_developer_directory_on_child_path'] and checked['component']['independent_int32_full_output_equal']
    import ast
    for p in PKG.glob('*.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02/run_m417_reference.sh'],capture_output=True)
    assert syntax.returncode==0
    v=dict(status='PASS_M417_ACTUAL_REFERENCE_CONTROL_AND_RECOVERY',manifest_sha256=digest,
        actual_isolated_component=checked,actual_isolated_component_sha256=sha(component_path),python310_syntax=True,bash_n=True,actual_delta_assembler_with_filesystem_root_substitution_only=True,actual_default_off_export_save_capture_load=True,complete_PASS_and_early_FAIL_export=True,
        negative_checks=rejects,actual_atomic_destination_and_BOARD_key=True,immutable=True,
        all_manifest_first_chunk_receipts=True,missing_receipt_rejected=True,control_failure_collect_SelfTest=True,
        fixtures_explicit_synthetic=True,target_model_quality_or_PL=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m417_support02.py','m417_control02.ps1','m417_workflow02.py')})
    out=BASE/'runs/M417-layer13-reference-support-02/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m417_reference_support02',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),
        f'## M417 实际软件参考控制与回收（2026-10-06）\n\nSHA {sha(out)}；实际保留NPY加载/损坏拒绝、有界artifact保存、PASS/早期FAIL原字节导出、{rejects}负例、实际原子目标/BOARD键/immutable、全部manifest-first/900B回执与缺失拒绝、控制失败仍收集自测通过。明确合成fixture，不证明目标质量。下一步同COM3一次原已保存输入精确参考，无Overlay/DMA/新视觉或语言前向。')
    print('M417_SUPPORT_SYNC',sha(out),rejects)
if __name__=='__main__':main()
