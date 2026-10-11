"""Actual new producer/default-off/export/collector/transfer routes, synthetic data."""
import contextlib,copy,importlib.util,io,json,subprocess,sys,tempfile
from types import SimpleNamespace
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m414_workflow as w
from m414_policy import POLICY,MemoryBudget,MAIN_SIZES,MINIMAL_SIZES
from m414_quality import save_features,THRESHOLDS,visual_quality
import numpy as np

def main():
    pkg=w.PKG;manifest=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');plan=json.loads((pkg/'PLAN.json').read_bytes())
    reference=json.loads((ROOT/plan['reference_result']).read_bytes());visual=json.loads((pkg/'EXPECTED_VISUAL.json').read_bytes())
    def load(name):
        spec=importlib.util.spec_from_file_location('actual_'+name,pkg/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    gate=load('m414_gate');exporter=load('m414_export');rejects=0
    root=ROOT/'tmp/m41401/support';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        folder=Path(temp);gate.OUTPUT=folder/'early/BOARD_RESULT.json';exporter.OUTPUT=gate.OUTPUT
        gate.proc=lambda:dict(CmaFree=0,MemAvailable=2<<30,Cached=0,VmRSS=10<<20,read_bytes=0,rchar=0)
        gate.os.geteuid=lambda:0;exporter.os.geteuid=lambda:0;exporter.time=SimpleNamespace(sleep=lambda _:None)
        previous=sys.argv
        try:
            sys.argv=['actual',digest]
            try:gate.main()
            except RuntimeError as e:assert 'Default-off' in str(e);rejects+=1
            else:raise AssertionError('Default-off bypass')
            assert not gate.OUTPUT.parent.exists()
            gate.verify_package=lambda *unused:(_ for _ in ()).throw(RuntimeError('EXPLICIT source-before-resource fixture rejection'))
            sys.argv=['actual',digest,'--enable-layer12-visual-quality'];assert gate.main()==1
        finally:sys.argv=previous
        failure=json.loads(gate.OUTPUT.read_bytes());assert failure['physical_transactions_started']==0 and failure['visual_forward_calls']==0
        def exported(value):
            exporter.OUTPUT.write_bytes(encoded(value));out=io.StringIO()
            with contextlib.redirect_stdout(out):exporter.emit_saved()
            return out.getvalue()+f'M414_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        assert w.decode(exported(failure))[2]==failure
        old=json.loads((BASE/'runs/M412-complete-MLP-board-01/BOARD_RESULT.json').read_bytes())
        good=dict(old,status='PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY',gate_return_code=0,errors=[],manifest_sha256=digest,gate_level='layer12-full-visual-feature-quality',
                  visual_forward_calls=2,selected_layers=[12],semantic_quality_proven=False,performance_pass=False,feature_quality_pass=True,original_reference_pass=True,
                  local_mlp_calls=0,samples=[],warmups=[],prior_complete_MLP_sha256=plan['previous_local_raw_sha256'],
                  original_visual=visual['visual'],candidate_visual=dict(visual['visual'],sha256='a'*64),preprocessed=visual['preprocessed'],
                  original_layer12_capture=reference['capture_tensors'],candidate_layer12_capture=dict(reference['candidate_tensors'],residual=reference['capture_tensors']['residual']),
                  original_visual_elapsed_ns_diagnostic=100,candidate_visual_elapsed_ns_diagnostic=100,
                  component=json.loads((BASE/'runs/M414-component-02/RESULT.json').read_bytes()),admission_policy=POLICY,elapsed_s_diagnostic_not_performance=1.)
        good.pop('comparison',None);good.pop('boundary_residual_bf16',None)
        state=dict(rng_sha256='0'*64,intraop=4,interop=4,dtype='torch.float32',inference=False)
        good['original_reference_before_overlay']=True
        good['component_process']=dict(separate_process=True,parent_state_unchanged=True,return_code=0,before=state,after=state,timeout_seconds=90,stdout_sha256='0'*64,stderr_sha256='0'*64)
        identities=json.loads((BASE/'candidates/M409-saved-MLP-reference-01/M348_SOURCE_IDENTITIES.json').read_bytes())['files']
        good['resolved_modules']={name:dict(path=row['path'],sha256=row['sha256']) for name in plan['resolved_module_names'] for row in identities if Path(row['path']).name==name+'.py'}
        good['CPU_store_after']=dict(good['CPU_store_after'],uncached_decode_calls=good['CPU_store_before']['uncached_decode_calls']+142,cache_entries=26,cache_bytes=66699264,cache_within_budget=True)
        good['staging']=good['staging'][:2];good['physical_transactions_started']=28
        snapshot=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098)
        good['PL_rows']=[dict(part=part,start=b['start'],shift=b['selected_shift'],input_bytes=b['input_bytes'],output_bytes=b['output_bytes'],packet_sha256=b['packet_sha256'],raw_sha256=b['raw_sha256'],completed_snapshot=snapshot,wait_ns=1)
                         for part in ('fc1','fc2') for b in reference['reference_batches'][part]]
        baseline=dict(VmRSS=10<<20,MemAvailable=2<<30,CmaFree=0);budget=MemoryBudget(baseline,lambda:dict(baseline))
        good['memory_after_constructor']=baseline
        labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*26+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
        good['memory']=[budget.check(label,recovery=i>=29) for i,label in enumerate(labels)]
        labels=['after-constructor']
        for phase in ('original-full-visual','layer12-PL-full-visual'):
            labels.append('before-'+phase);labels.extend(phase+':layer'+str(i)+':'+edge for i in range(24) for edge in ('before','after'));labels.append('after-'+phase)
        good['PS_checkpoints']=[budget.check(label) for label in labels]
        feature=np.random.default_rng(413).normal(size=(98,2560)).astype(np.float32)
        good['full_visual_quality']=visual_quality(feature,feature)
        good['retained_visual_features']=[dict(path=prefix+'_visual.npy',file_bytes=1003648,file_sha256='b'*64,tensor=good[key]) for prefix,key in [('original','original_visual'),('candidate','candidate_visual')]]
        complete=exported(good);assert w.decode(complete)[2]==good
        # Exercise new bounded file producer and immutable native-array round trip.
        actual=save_features(folder,dict(original=feature,candidate=feature))
        assert all(np.array_equal(np.load(folder/x['path'],allow_pickle=False),feature) for x in actual)
        try:save_features(folder,dict(original=feature,candidate=feature))
        except RuntimeError:rejects+=1
        else:raise AssertionError('Visual features overwritten')
        mutations=[]
        x=copy.deepcopy(good);x['original_reference_before_overlay']=False;mutations.append(exported(x))
        x=copy.deepcopy(good);x['component_process']['separate_process']=False;mutations.append(exported(x))
        for key,value in [('numerical_pass',False),('feature_quality_pass',False),('semantic_quality_proven',True),('performance_pass',True),('selected_layers',[12,13]),('visual_forward_calls',3),('language_forward_calls',1),('bindings_restored',False),('PS_owner_closed',False),('stable_restored',False),('DMA_allocator_restored',False),('DMA_sealed_after_main',False),('unexpected_DMA_requests',['forbidden']),('unsafe_dma_buffers_retained',True),('PS_checkpoints',good['PS_checkpoints'][:-1]),('source_identities_verified',48),('physical_transactions_started',27),('releases',good['releases'][:-1]),('elapsed_s_diagnostic_not_performance',841)]:
            x=copy.deepcopy(good);x[key]=value;mutations.append(exported(x))
        for i in range(14):
            x=copy.deepcopy(good)
            if i==0:x['full_visual_quality']['metrics']['relative_l2']=.021
            if i==1:x['full_visual_quality']['thresholds']['maximum_relative_l2']=.1
            if i==2:x['original_visual']['sha256']='0'*64
            if i==3:x['candidate_layer12_capture']['input']['sha256']='0'*64
            if i==4:x['PL_rows'][-1]['raw_sha256']='0'*64
            if i==5:x['PL_rows'][-1]['completed_snapshot']['mm2s_dmasr']=0
            if i==6:x['memory'][0]['required_cma_free_bytes']=64<<20
            if i==7:x['memory'][0]['VmRSS']=baseline['VmRSS']+(769<<20)
            if i==8:x['retained_visual_features'][0]['file_bytes']=1
            if i==9:x['resolved_modules']['m273_latest_vision_runtime']['sha256']='0'*64
            if i==10:x['component']['negative_checks']=8
            if i==11:x['CPU_store_after']['uncached_decode_calls']-=2
            if i==12:x['numerical_batches']['fc1'][-1]['rows']=32
            if i==13:x['PL_rows']=x['PL_rows'][::-1]
            mutations.append(exported(x))
        mutations.extend([complete+complete,complete.replace('M414_RESULT_CHUNK=1/','M414_RESULT_CHUNK=0/'),complete.replace('gate_rc=0 export_rc=0','gate_rc=0 export_rc=1'),complete[:complete.index('M414_RESULT_CHUNK=1/')]])
        for value in mutations:
            try:w.decode(value)
            except (ValueError,KeyError):rejects+=1
            else:raise AssertionError('Invalid full visual decision accepted')
        log=folder/'collected.log';log.write_text(complete,encoding='utf-8');called=[];out=folder/'destination/BOARD_RESULT.json'
        assert w.collect(log,out,sync_function=lambda *args:called.append(args))==good and out.read_bytes()==encoded(good) and called[0][0]=='latest_m414_layer12_visual_board'
        receipts=folder/'receipts';receipts.mkdir()
        for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in manifest['files']]:
            prefix='upload_'+name.replace('.','_');size=(pkg/name).stat().st_size;count=(size+899)//900
            (receipts/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):(receipts/(prefix+f'_chunk_{i:04d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} '+name,encoding='utf-8')
        (receipts/'syntax.log').write_text('__M414_SYNTAX_RC_0__',encoding='utf-8');assert len(w.transfer(receipts,False)['files'])==manifest['file_count']+1
        next(receipts.glob('upload_*_chunk_*.log')).unlink()
        try:w.transfer(receipts,False)
        except ValueError:rejects+=1
        else:raise AssertionError('Missing upload receipt accepted')
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    test=subprocess.run([psh,'-NoProfile','-File',str(HERE/'m414_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert test.returncode==0 and b'M414_CONTROL_SELF_TEST_PASS' in test.stdout
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M414-layer12-full-visual-01/run_m414_mlp.sh'],capture_output=True);assert syntax.returncode==0,syntax.stdout+syntax.stderr
    value=dict(status='PASS_M414_ACTUAL_PRODUCER_EXPORT_CONTROL_RECOVERY',manifest_sha256=digest,negative_checks=rejects,actual_default_off_and_source_before_resource_failure=True,
               actual_failure_saved_exported=True,complete_visual_PASS_collected_with_explicit_synthetic_data=True,actual_feature_save_and_immutable_roundtrip=True,
               actual_atomic_destination_and_BOARD_key=True,manifest_first_all900B_receipts=True,missing_receipt_rejected=True,control_failure_collection_SelfTest=True,bash_n=True,
               board_quality_or_performance_proven=False,source_sha256={n:sha(HERE/n) for n in ('m414_support.py','m414_workflow.py','m414_control.ps1')})
    path=BASE/'runs/M414-layer12-visual-support-01/RESULT.json';atomic(path,encoded(value),immutable=True)
    sync('latest_m414_layer12_visual_support',dict(status=value['status'],result=path.relative_to(ROOT).as_posix(),sha256=sha(path),manifest_sha256=digest),
         f'## M414 完整视觉质量实际配套检查（2026-10-06）\n\nSHA {sha(path)}；真实新producer默认关闭/资源前FAIL保存与导出、完整PASS合成记录和{rejects}项拒绝、两个feature文件原子保存及immutable、实际collect目的地/BOARD键、全部manifest-first900B回执/缺失拒绝、控制故意失败收集与bash-n通过。明确合成数据，不证明目标质量。下一步同COM3原版一次完整视觉SHA→仅第12层PL一次完整视觉特征筛选，无语言/性能/扩层；失败只收集原字节。')
    print('M414_SUPPORT_SYNC',sha(path),rejects)
if __name__=='__main__':main()
