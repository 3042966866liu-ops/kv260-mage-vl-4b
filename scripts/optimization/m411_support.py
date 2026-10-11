"""Actual producer early failure/export/collection/receipt routes, synthetic PASS."""
import ast,contextlib,copy,importlib.util,io,json,subprocess,sys,tempfile
from types import SimpleNamespace
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m411_workflow as w
def main():
    pkg=w.PKG;m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');plan=json.loads((pkg/'PLAN.json').read_bytes())
    ref=json.loads((ROOT/plan['reference_result']).read_bytes())
    def load(name):
        spec=importlib.util.spec_from_file_location('m411_actual_'+name,pkg/(name+'.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    producer=load('m411_gate');exporter=load('m411_export');rejects=0
    root=ROOT/'tmp/m41101/support';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        folder=Path(temp);producer.OUTPUT=folder/'early/BOARD_RESULT.json';exporter.OUTPUT=producer.OUTPUT
        producer.proc=lambda:dict(CmaFree=256<<20,MemAvailable=2<<30,Cached=0,VmRSS=10<<20,read_bytes=0,rchar=0)
        producer.os.geteuid=lambda:0;exporter.os.geteuid=lambda:0;exporter.time=SimpleNamespace(sleep=lambda _:None)
        old=sys.argv
        try:
            sys.argv=['actual',digest]
            try:producer.main()
            except RuntimeError as e:assert 'Default-off' in str(e);rejects+=1
            else:raise AssertionError('Default-off bypass')
            assert not producer.OUTPUT.parent.exists()
            producer.verify_package=lambda *unused:(_ for _ in ()).throw(RuntimeError('EXPLICIT resource-before-source fixture rejection'))
            sys.argv=['actual',digest,'--enable-complete-MLP-gate'];assert producer.main()==1
        finally:sys.argv=old
        failure=json.loads(producer.OUTPUT.read_bytes());assert not failure['numerical_pass'] and failure['physical_transactions_started']==0 and failure['local_mlp_calls']==0
        def export(value):
            exporter.OUTPUT.parent.mkdir(parents=True,exist_ok=True);exporter.OUTPUT.write_bytes(encoded(value));out=io.StringIO()
            with contextlib.redirect_stdout(out):exporter.emit_saved()
            return out.getvalue()+f'M411_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        assert w.decode(export(failure))[2]==failure
        samples=[]
        for variant in 'ABBABAAB':samples.append(dict(variant=variant,elapsed_ns=1000000 if variant=='A' else 800000,read_bytes=0,rchar=1,output_exact_outside_timer=True,logical_PL_calls=26 if variant=='B' else 0,physical_PL_calls=26 if variant=='B' else 0,staging_bytes=4456448 if variant=='B' else 0))
        allocations=[]
        for group,sizes in enumerate(([144]*4+[2576,4096],[557056]*4+[163856,524288,524288],[144]*4+[2576,4096])):
            for i,size in enumerate(sizes):allocations.append(dict(label=str(group),bytes=size,address=0x10000000+group*0x1000000+i*0x100000))
        releases=[];start=0
        for count in (6,7,6):releases.extend(reversed(allocations[start:start+count]));start+=count
        snapshot=dict(ap_ctrl=4,ap_return=0x4d395832,mm2s_dmasr=4098,s2mm_dmasr=4098)
        good=dict(failure,status='PASS_M411_COMPLETE_MLP_NET_GAIN',gate_return_code=0,errors=[],package_verified=True,numerical_pass=True,bindings_restored=True,PS_owner_closed=True,safe_buffers_released=True,stable_restored=True,boot_unchanged=True,cmdline_unchanged=True,unsafe_dma_buffers_retained=False,
            prior_chain_sha256=plan['chain_raw_sha256'],source_identities_verified=49,full_wire_reference_batches_exact=26,local_mlp_calls=12,target_resolution=ref['target_resolution'],target_matrices=ref['target_matrices'],quality_metrics=ref['quality_metrics'],boundary_residual_bf16=ref['boundary_residual_bf16'],
            backend_before={},backend_after={},release_preflight=dict(status='READY_FOR_BOARD_PREFLIGHT'),warmups=[samples[0],samples[1]],samples=samples,comparison=w.decision(samples),performance_pass=True,
            CPU_store_before=dict(uncached_decode_calls=0),CPU_store_after=dict(uncached_decode_calls=12),PL_rows=[{}]*156,physical_transactions_started=158,transactions=[{}]*2,staging=[{}]*12,
            numerical_batches={part:[{k:b[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|dict(physical_calls=b['physical_reference_attempts']) for b in ref['reference_batches'][part]] for part in ('fc1','fc2')},
            allocations=allocations,releases=releases,memory=[dict(CmaFree=256<<20,MemAvailable=2<<30,required_cma_free_bytes=64<<20) for _ in range(161)],final_snapshot=snapshot,elapsed_s_diagnostic_not_performance=1.)
        complete=export(good);assert w.decode(complete)[2]==good
        no_gain=copy.deepcopy(good)
        for x in no_gain['samples']:x['elapsed_ns']=1000000 if x['variant']=='A' else 990000
        no_gain['comparison']=w.decision(no_gain['samples']);no_gain['performance_pass']=False;no_gain['status']='CLOSED_M411_COMPLETE_MLP_NO_RELIABLE_NET_GAIN';assert w.decode(export(no_gain))[2]==no_gain
        mutations=[]
        for k,v in [('manifest_sha256','0'*64),('numerical_pass',False),('bindings_restored',False),('PS_owner_closed',False),('stable_restored',False),('unsafe_dma_buffers_retained',True),('full_visual',True),('expanded_24_layers',True),('full_wire_reference_batches_exact',25),('local_mlp_calls',11),('physical_transactions_started',157),('releases',releases[:-1]),('source_identities_verified',48),('backend_after',dict(changed=True)),('performance_pass',False),('elapsed_s_diagnostic_not_performance',841)]:
            if k=='full_visual':continue
            x=copy.deepcopy(good);x[k]=v;mutations.append(export(x))
        for k in range(8):
            x=copy.deepcopy(good)
            if k==0:x['samples'][1]['staging_bytes']=0
            if k==1:x['samples'][1]['physical_PL_calls']=25
            if k==2:x['samples'][0]['variant']='B'
            if k==3:x['numerical_batches']['fc1'][-1]['rows']=32
            if k==4:x['memory'][0]['CmaFree']=32<<20
            if k==5:x['target_matrices']['fc1']['bias_sha256']='0'*64
            if k==6:x['comparison']['mean_gain']=.9
            if k==7:x['final_snapshot']['mm2s_dmasr']=0
            mutations.append(export(x))
        mutations += [complete+complete,complete.replace('M411_RESULT_CHUNK=1/','M411_RESULT_CHUNK=0/'),complete.replace('gate_rc=0 export_rc=0','gate_rc=1 export_rc=0'),complete[:complete.index('M411_RESULT_CHUNK=1/')]]
        for txt in mutations:
            try:w.decode(txt)
            except (ValueError,KeyError):rejects+=1
            else:raise AssertionError('Invalid complete segment accepted')
        log=folder/'collected.log';log.write_text(complete,encoding='utf-8');called=[];out=folder/'destination/BOARD_RESULT.json'
        assert w.collect(log,out,sync_function=lambda *args:called.append(args))==good and out.read_bytes()==encoded(good) and called[0][0]=='latest_m411_complete_mlp_board'
        try:atomic(out,b'changed',immutable=True)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Immutable evidence overwritten')
        receipts=folder/'receipts';receipts.mkdir()
        for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
            prefix='upload_'+name.replace('.','_');size=(pkg/name).stat().st_size;count=(size+899)//900
            (receipts/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):(receipts/(prefix+f'_chunk_{i:04d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} '+name,encoding='utf-8')
        (receipts/'syntax.log').write_text('__M411_SYNTAX_RC_0__',encoding='utf-8');assert len(w.transfer(receipts,False)['files'])==m['file_count']+1
        next(receipts.glob('upload_*_chunk_*.log')).unlink()
        try:w.transfer(receipts,False)
        except ValueError:rejects+=1
        else:raise AssertionError('Missing upload receipt accepted')
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    test=subprocess.run([psh,'-NoProfile','-File',str(HERE/'m411_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert test.returncode==0 and b'M411_CONTROL_SELF_TEST_PASS' in test.stdout
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M411-complete-visual-MLP-01/run_m411_mlp.sh'],capture_output=True);assert syntax.returncode==0,syntax.stderr
    v=dict(status='PASS_M411_ACTUAL_PRODUCER_EXPORT_CONTROL_RECOVERY',manifest_sha256=digest,actual_default_off_and_resource_before_source_failure=True,actual_early_FAIL_saved_and_exported=True,complete_PASS_and_rejected_net_gain_collected=True,negative_checks=rejects,
        actual_atomic_destination_and_BOARD_key=True,immutable=True,manifest_first_all900B_receipts=True,missing_receipt_rejected=True,control_failure_collect_SelfTest=True,bash_n=True,synthetic_PASS_not_hardware=True,performance_evidence=False,
        source_sha256={n:sha(HERE/n) for n in ('m411_support.py','m411_workflow.py','m411_control.ps1')})
    p=BASE/'runs/M411-complete-MLP-support-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m411_complete_mlp_support',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=digest),
        f'## M411 完整MLP实际控制回收检查（2026-10-06）\n\nSHA {sha(p)}；实际default-off/源码前拒绝保存及原FAIL导出、完整PASS和净收益拒绝合成记录、{rejects}负例、原子目的地/BOARD键/immutable、manifest-first全部900B回执及缺失拒绝、控制故意失败仍收集和bash-n通过。仅离线配套证据，不证明目标PL/质量或性能。下一步同COM3一次有界完整MLP数值后预定AB预热+ABBABAAB8完整段，容量不足/生命周期/精度失败停本级，不扩24层。')
    print('M411_SUPPORT_SYNC',sha(p),rejects)
if __name__=='__main__':main()
