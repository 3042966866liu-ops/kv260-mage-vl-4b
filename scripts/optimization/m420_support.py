"""Actual entry/export/strict collector checks using explicit synthetic records."""
import ast,copy,contextlib,importlib.util,io,json,subprocess,sys,tempfile
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m420_workflow02 as w
from m414_policy import MemoryBudget

def main():
    pkg=w.PKG;plan=json.loads((pkg/'PLAN.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');rejects=0
    def load(name):
        spec=importlib.util.spec_from_file_location('m420_actual_'+name,pkg/(name+'.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    producer=load('m420_gate');exporter=load('m420_export')
    local=copy.deepcopy(plan)
    for row in local['board_prerequisites']:row['path']=str(ROOT/row['local_path'])
    producer.verify_prerequisites(local)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
        folder=Path(temp);p=folder/'prior.json'
        for key,bad in [('status','PASS_M410_CHAIN'),('gate_return_code',1),('gate_return_code',False),('stable_restored',False),('safe_buffers_released',False),('numerical_pass',False),('performance_pass',False),('errors',['synthetic'])]:
            badplan=copy.deepcopy(local);value=json.loads(Path(badplan['board_prerequisites'][0]['path']).read_bytes());value[key]=bad;p.write_bytes(encoded(value));badplan['board_prerequisites'][0].update(path=str(p),sha256=sha(p))
            try:producer.verify_prerequisites(badplan)
            except RuntimeError:rejects+=1
            else:raise AssertionError('Bad actual prerequisite accepted')
        badplan=copy.deepcopy(local);badplan['board_prerequisites'][0]['sha256']='0'*64
        try:producer.verify_prerequisites(badplan)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Prerequisite SHA ignored')
        producer.OUTPUT=folder/'failure/BOARD_RESULT.json';exporter.OUTPUT=producer.OUTPUT
        producer.os.geteuid=lambda:0;exporter.os.geteuid=lambda:0;exporter.time=SimpleNamespace(sleep=lambda _:None);producer.proc=lambda:dict(CmaFree=0,MemAvailable=2<<30,Cached=0,VmRSS=10<<20,read_bytes=0,rchar=0)
        old=sys.argv
        try:
            sys.argv=['actual',digest]
            try:producer.main()
            except RuntimeError:rejects+=1
            else:raise AssertionError('Default off bypass')
            assert not producer.OUTPUT.parent.exists()
            producer.verify_package=lambda *unused:(_ for _ in ()).throw(RuntimeError('EXPLICIT source-before-resource rejection'))
            sys.argv=['actual',digest,'--enable-combination-quality'];assert producer.main()==1
        finally:sys.argv=old
        failure=json.loads(producer.OUTPUT.read_bytes());assert not failure['allocations'] and not failure['overlay_loads'] and failure['visual_forward_calls']==0
        def export(value):
            exporter.OUTPUT.write_bytes(encoded(value));out=io.StringIO()
            with contextlib.redirect_stdout(out):exporter.emit_saved()
            return out.getvalue()+f'M420_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        assert w.decode(export(failure))[2]==failure
        b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());good=json.loads((ROOT/b['latest_m414_layer12_visual_board']['result']).read_bytes())
        ref12=json.loads((ROOT/plan['reference_results']['12']).read_bytes());ref13=json.loads((ROOT/plan['reference_results']['13']).read_bytes());refs={'12':ref12,'13':ref13}
        cp=json.loads((ROOT/'tmp/m42002/component/RESULT.json').read_bytes())
        good.update(status='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY',gate_level='layers12-13-full-visual-feature-quality',manifest_sha256=digest,selected_layers=[12,13],visual_forward_calls=3,
            component=cp['component'],prerequisites_verified=plan['board_prerequisites'],original_captures={i:r['capture_tensors'] for i,r in refs.items()},target_matrices={i:r['target_matrices'] for i,r in refs.items()},target_resolution={i:r['target_resolution'] for i,r in refs.items()},
            software_captures={i:dict(r['candidate_tensors'],residual=r['capture_tensors']['residual']) for i,r in refs.items()},software_visual=good['candidate_visual'],layer13_input_changed=False,software_PL_complete_features_exact=True,full_wire_reference_batches_exact=52,
            software_batches={i:r['reference_batches'] for i,r in refs.items()},software_wire_identities={},PL_batches={},PL_rows=[],physical_transactions_started=54,
            local_quality={i:dict(r['quality_metrics'],actual_residual_sum=r['quality_metrics']['residual_sum']) for i,r in refs.items()})
        good['candidate_captures']=copy.deepcopy(good['software_captures'])
        for index,ref in refs.items():
            good['software_wire_identities'][index]=[];good['PL_batches'][index]={}
            for part in ('fc1','fc2'):
                batches=ref['reference_batches'][part]
                good['PL_batches'][index][part]=[{k:x[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|dict(physical_calls=1) for x in batches]
                for x in batches:
                    row=dict(part=part,start=x['start'],shift=x['selected_shift'],input_bytes=x['input_bytes'],output_bytes=x['output_bytes'],packet_sha256=x['packet_sha256'],raw_sha256=x['raw_sha256'])
                    good['software_wire_identities'][index].append(row);good['PL_rows'].append(dict(row,layer=int(index),completed_snapshot=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098)))
        good['staging']=[dict(layer=i,part=part,bytes=2228224,elapsed_ns=1) for i in (12,13) for part in ('fc1','fc2')]
        good['CPU_store_after']['uncached_decode_calls']=good['CPU_store_before']['uncached_decode_calls']+208
        baseline=good['memory_after_constructor'];budget=MemoryBudget(baseline,lambda:dict(baseline,MemAvailable=3<<30))
        labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*52+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
        good['memory']=[budget.check(label,recovery=i>=55) for i,label in enumerate(labels)]
        labels=['after-constructor']
        for phase in ('original-full-visual','software-full-visual','PL-full-visual'):labels+=['before-'+phase]+[phase+':layer'+str(i)+':'+edge for i in range(24) for edge in ('before','after')]+['after-'+phase]
        good['PS_checkpoints']=[budget.check(label) for label in labels]
        full=export(good);assert w.decode(full)[2]==good
        mutations=[]
        for key,bad in [('manifest_sha256','0'*64),('selected_layers',[12,13,14]),('visual_forward_calls',2),('language_forward_calls',1),('performance_pass',True),('semantic_quality_proven',True),('stable_restored',False),('bindings_restored',False),('PS_owner_closed',False),('DMA_allocator_restored',False),('unexpected_DMA_requests',['new']),('physical_transactions_started',53),('full_wire_reference_batches_exact',51),('software_PL_complete_features_exact',False),('layer13_input_changed',True),('source_identities_verified',48),('releases',good['releases'][:-1]),('elapsed_s_diagnostic_not_performance',841)]:
            value=copy.deepcopy(good);value[key]=bad;mutations.append(export(value))
        for kind in range(10):
            value=copy.deepcopy(good)
            if kind==0:value['candidate_captures']['13']['input']['sha256']='0'*64
            if kind==1:value['PL_rows'][-1]['raw_sha256']='0'*64
            if kind==2:value['software_batches']['13']['fc2'][-1]['rows']=32
            if kind==3:value['staging'][-1]['layer']=12
            if kind==4:value['memory'][-1]['recovery']=False
            if kind==5:value['PS_checkpoints'].pop()
            if kind==6:value['local_quality']['13']['actual_residual_sum']['relative_l2']=.03
            if kind==7:value['component_process']['parent_state_unchanged']=False
            if kind==8:value['full_visual_quality']['metrics']['relative_l2']=.03
            if kind==9:value['final_snapshot']['mm2s_dmasr']=0
            mutations.append(export(value))
        mutations += [full+full,full.replace('M420_RESULT_CHUNK=1/','M420_RESULT_CHUNK=0/'),full[:full.index('M420_RESULT_CHUNK=1/')],full.replace('gate_rc=0 export_rc=0','gate_rc=0 export_rc=1')]
        for t in mutations:
            try:w.decode(t)
            except (ValueError,KeyError):rejects+=1
            else:raise AssertionError('Bad combination evidence accepted')
        log=folder/'export.log';log.write_text(full,encoding='utf-8');called=[];out=folder/'collected/BOARD_RESULT.json'
        assert w.collect(log,out,sync_function=lambda *args:called.append(args))==good and called[0][0]=='latest_m420_combination_board' and out.read_bytes()==encoded(good)
        try:atomic(out,b'changed',immutable=True)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Saved evidence overwritten')
        receipts=folder/'receipts';receipts.mkdir();m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())
        for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
            prefix='upload_'+name.replace('.','_');size=(pkg/name).stat().st_size;count=(size+899)//900
            (receipts/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):(receipts/(prefix+f'_chunk_{i:04d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)}',encoding='utf-8')
        (receipts/'syntax.log').write_text('__M420_SYNTAX_RC_0__',encoding='utf-8');w.transfer(receipts,False)
        next(receipts.glob('upload_*_chunk_*.log')).unlink()
        try:w.transfer(receipts,False)
        except ValueError:rejects+=1
        else:raise AssertionError('Missing upload receipt accepted')
    tree=ast.parse((pkg/'m420_gate.py').read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');calls=[n for n in ast.walk(main) if isinstance(n,ast.Call)]
    source=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='verify_prerequisites');constructor=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='M273LatestPSVisionRuntime');owner=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='WorkOwner');assert source.lineno<constructor.lineno<owner.lineno
    def output(name):
        tree=ast.parse((pkg/name).read_bytes());n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUTPUT' for t in n.targets));return n.value.args[0].value
    assert output('m420_gate.py')==output('m420_export.py')=='/home/ubuntu/m420_combination_visual_02/BOARD_RESULT.json'
    assert '[[ ! -e '+PurePosixPath(output('m420_gate.py')).parent.as_posix()+' ]]' in (pkg/'run_m420_mlp.sh').read_text(encoding='utf-8')
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    result=subprocess.run([psh,'-NoProfile','-File',str(HERE/'m420_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert result.returncode==0 and b'M420_CONTROL_SELF_TEST_PASS' in result.stdout
    result=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M420-layers12-13-full-visual-02/run_m420_mlp.sh'],capture_output=True);assert result.returncode==0
    for p in pkg.glob('*.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    v=dict(status='PASS_M420_ACTUAL_ENTRY_COLLECTION_CONTROL',manifest_sha256=digest,actual_prerequisite_positive_and_negative=True,actual_source_before_resources=True,actual_default_off_and_early_FAIL_export=True,full_synthetic_PASS_collected=True,negative_checks=rejects,
        immutable_saved_only=True,manifest_first_all900B_receipts=True,source_guard_before_constructor=True,result_paths_equal=True,control_failure_collect_SelfTest=True,bash_n=True,Python310_syntax=True,
        clean_dynamic_component_sha256=sha(ROOT/'tmp/m42002/component/RESULT.json'),synthetic_not_board=True,performance_evidence=False,
        source_sha256={n:sha(HERE/n) for n in ('m420_support.py','m420_workflow02.py','m420_control.ps1')})
    out=BASE/'runs/M420-combination-support-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m420_combination_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),f'## M420 双层视觉实际入口与回收检查（2026-10-06）\n\nSHA {sha(out)}；真实冻结前级正例及错误状态/rc/释放/净收益/SHA拒绝，默认关闭/资源前FAIL原导出、完整合成PASS和{rejects}负例、原子目的地/BOARD键、manifest-first900B回执/缺失拒绝、故意失败仍收集、三结果路径及Python3.10/bash-n通过。明确离线合成，不证明板端质量。下一步同COM3一次原版/动态软件/PL三视觉质量，0语言/性能/24层。')
    print('M420_SUPPORT_SYNC',sha(out),rejects)
if __name__=='__main__':main()
