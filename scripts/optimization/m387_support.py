"""New video PS scope, two-source assembly and strict recovery checks only."""
import ast,base64,copy,hashlib,json,os,subprocess,sys,tempfile,textwrap,weakref,shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m387_prepare import PKG,OLD,VIDEO,once

def main():
    prep=json.loads((BASE/'runs/M387-ps-video-preparation-01/RESULT.json').read_text(encoding='utf-8'))
    text_raw=prep['PS_text_prerequisite_sha256']
    s=(HERE/'m386_control.ps1').read_text(encoding='utf-8').replace('M386','M387').replace('m386','m387').replace('ps-text','ps-video').replace('ps_text','ps_video').replace('PS_TEXT','PS_VIDEO').replace('candidates/M385-ps-layer-02','candidates/M386-ps-text-01')
    s=once(s,'    $oldEntries=@{}',"    $secondary=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/optimization_v1/candidates/M380-gate-up-video-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json\n    $oldEntries=@{}")
    s=once(s,'    foreach ($entry in $oldManifest.files) { $oldEntries[$entry.path]=$entry.sha256 }',"    foreach ($entry in $secondary.files) { $oldEntries[$entry.path]=$entry.sha256+':'+$entry.bytes }\n    foreach ($entry in $oldManifest.files) { $oldEntries[$entry.path]=$entry.sha256+':'+$entry.bytes }")
    s=once(s,"$oldEntries[$_.path] -ne $_.sha256","$oldEntries[$_.path] -ne ($_.sha256+':'+$_.bytes)")
    atomic(HERE/'m387_control.ps1',s.encode('utf-8'))
    s=(HERE/'m386_workflow.py').read_text(encoding='utf-8').replace('M386','M387').replace('m386','m387').replace('ps-text','ps-video').replace('ps_text','ps_video').replace('candidates/M385-ps-layer-02','candidates/M386-ps-text-01').replace('30载荷','37载荷').replace('精确M385','精确M386与M380').replace('固定文本162窗口','固定159视频162窗口').replace('固定文本完整数值','固定159视频完整数值')
    s=once(s,"    names=['PACKAGE_MANIFEST.json']", "    secondary=json.loads((BASE/'candidates/M380-gate-up-video-01/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))\n    second={r['path']:r for r in secondary['files']}\n    old.update({k:v for k,v in second.items() if k not in old or old[k]!=next((r for r in manifest['files'] if r['path']==k),None)})\n    names=['PACKAGE_MANIFEST.json']")
    s=once(s,"old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json')", "old_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),secondary_manifest_sha256=sha(BASE/'candidates/M380-gate-up-video-01/PACKAGE_MANIFEST.json')")
    atomic(HERE/'m387_workflow.py',s.encode('utf-8'))
    s=(HERE/'m386_collect.py').read_text(encoding='utf-8').replace('M386','M387').replace('ps-text','ps-video').replace('ps_text','ps_video').replace('m366_stage_policy','m368_stage_policy').replace('PASS_M387_PS_TEXT_NUMERICAL','PASS_M387_PS_VIDEO_NUMERICAL').replace('sealed-DMA-PS-fixed-text-numerical','sealed-DMA-PS-fixed159-video-numerical').replace('layer_result','video_result').replace('LAYER_EXPECTED.json','VIDEO_EXPECTED.json').replace('PS_layer_prerequisite_sha256','PS_text_prerequisite_sha256').replace('07a1ee4ab46b8b730a70ddd13f711bb4f99e6179f9f1e58666ae769be4cd4ce8',text_raw).replace("p['budget_growth_bytes']!=256<<20","p['budget_growth_bytes']!=1024<<20")
    s=once(s,"        expected=json.loads((PKG/'VIDEO_EXPECTED.json')", "        visual=json.loads((PKG/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))\n        if r['vision_forward_calls']!=1 or not all(r['visual_exact_comparison'].values()) or r['visual_features']!=visual['visual_features'] or r['preprocessed']!=visual['preprocessed'] or r['prompt_token_ids']!=visual['prompt_token_ids']:raise ValueError('Original visual identity/output differs')\n        if r['same_loading_path_video_sha256']!='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf':raise ValueError('Frozen original video loader differs')\n        expected=json.loads((PKG/'VIDEO_EXPECTED.json')")
    s=s.replace('原30Token/36层/完整head与162窗口PS预读，原单parser，非视频','原159Token视频/视觉/36层/head与162窗口PS预读，原单parser').replace('之后独立论证159视频预算','之后才准备同核单parser原暂存/PS预读轻量交错请求性能').replace('M387 PS固定文本数值门禁','M387 PS固定159视频数值门禁')
    atomic(HERE/'m387_collect.py',s.encode('utf-8'))
    ctl=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m387_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert ctl.returncode==0 and 'M387_CONTROL_SELF_TEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    sys.path.insert(0,str(PKG))
    import ps_read_ahead as component
    from ps_read_ahead import RetainedPSResourcesError
    from test_ps_read_ahead import Buffer,SAFE
    from test_m382_ps_slot import memory
    from m368_stage_policy import FAMILIES,SHAPES,assess
    namespace={};exec(compile((PKG/'m387_video_ps_read.py').read_text(encoding='utf-8'),'actual-frozen-video-adapter','exec'),namespace)
    VideoPSReadSession=namespace['VideoPSReadSession']
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);layouts=[]
        for kind in ('language','head'):
            folder=root/kind;folder.mkdir()
            for port in range(4):(folder/f'weights{port}.bin').write_bytes(bytes(range(256))*32)
            layouts.append(SimpleNamespace(root=folder,manifest=dict(files=[dict(path=f'weights{i}.bin',bytes=8192) for i in range(4)])))
        chains={(layer,name):dict(offset=i*16,size=32,descriptors=[i]) for i,(layer,name) in enumerate(FAMILIES)}
        head=[dict(offset=i*16,size=32,descriptors=[200+i]) for i in range(8)]
        runtime=SimpleNamespace(weight_mode='staged-low-cma',maximum_weight_window_bytes=128,staged_buffers=[Buffer(128) for _ in range(4)],kernel=None,dma=None,language_layout=layouts[0],head_layout=layouts[1],head_contract=SimpleNamespace(chains=head),stage_bytes=0,stage_ms=0,_stage=lambda *a:'original',_language_chain=lambda layer,name:chains[(layer,name)])
        before=runtime._stage;current=memory(rss=100<<20);current['system_bytes']['MemAvailable']=2<<30;counts={'success':7}
        policy=SimpleNamespace(sealed=True,baseline_rss=100<<20,initial_counts=counts,buffer_bytes=SHAPES,stop_reason=None,snapshot=lambda:copy.deepcopy(current),counters=lambda:dict(counts))
        def capture(label,check):
            if check:assess(current,policy.baseline_rss,counts,counts,sealed=True,buffer_bytes=SHAPES)
            return copy.deepcopy(current)
        policy.capture=capture;base=SimpleNamespace(chain_window=lambda layout,c:(c['offset']//16,c['size']),transaction_snapshot=lambda *a:dict(SAFE))
        observed=[]
        def original_prefill(hidden):
            for layout,chain in [(runtime.language_layout,chains[x]) for x in FAMILIES]+[(runtime.head_layout,c) for c in head]:
                runtime._stage(layout,chain)
                expected=bytes((i%256) for i in range(chain['offset'],chain['offset']+32))
                assert all(bytes(b.array[:32])==expected for b in runtime.staged_buffers)
                observed.append((layout,chain))
            return 17,None,None
        source=(PKG/'m387_ps_video_gate.py').read_text(encoding='utf-8');a=source.index('            plan=[(');b=source.index("            policy.capture('after-language-prefill-and-head'",a)
        result={};ns=dict(runtime=runtime,base=base,policy=policy,resident=lambda:True,VideoPSReadSession=VideoPSReadSession,FAMILIES=FAMILIES,weakref=weakref,RetainedPSResourcesError=RetainedPSResourcesError,result=result,original_prefill=original_prefill,hidden=None,allocations=[None]*7)
        strict=component.file_identity
        if os.name=='nt':
            with patch.object(component,'file_identity',lambda stat:strict(stat)[:4]+strict(stat)[5:]):exec(compile(textwrap.dedent(source[a:b]),'actual-frozen-video-PS-scope','exec'),ns)
        else:exec(compile(textwrap.dedent(source[a:b]),'actual-frozen-video-PS-scope','exec'),ns)
        assert len(observed)==162 and sum(x[0] is runtime.head_layout for x in observed)==8
        assert runtime._stage is before and result['session_weakref_dead'] and not hasattr(runtime,'_m351_ps_owner')
        assert result['ps_session']['component']['stages']==result['ps_session']['component']['submissions']==162
        assert result['ps_session']['component']['total_weight_bytes']==20736
        assert result['ps_session']['slot_release']['all_owner_weakrefs_dead'] and result['ps_session']['budget_growth_bytes']==1024<<20
    # Run the exact assembly with path-only relocation over actual immutable files.
    assembly_checks=0
    for fault in ('none','secondary_manifest','secondary_payload','missing_new','extra','count','bytes','traversal'):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);dest=root/'candidate';primary=root/'primary';secondary=root/'secondary';dest.mkdir();shutil.copytree(OLD,primary);shutil.copytree(VIDEO,secondary)
            new=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']};second={r['path']:r for r in json.loads((VIDEO/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
            for r in new['files']:
                if old.get(r['path'])!=r and second.get(r['path'])!=r:shutil.copyfile(PKG/r['path'],dest/r['path'])
            if fault=='secondary_manifest':(secondary/'PACKAGE_MANIFEST.json').write_bytes(b'{}')
            elif fault=='secondary_payload':(secondary/'VIDEO_EXPECTED.json').write_bytes(b'corrupt')
            elif fault=='missing_new':(dest/'m387_ps_video_gate.py').unlink()
            elif fault=='extra':(dest/'unexpected').write_bytes(b'')
            elif fault=='count':new['file_count']+=1
            elif fault=='bytes':new['total_bytes']+=1
            elif fault=='traversal':new['files'][0]['path']='../escape'
            (dest/'PACKAGE_MANIFEST.json').write_bytes(encoded(new))
            source=(PKG/'m387_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m386_ps_text_candidate_01',primary.as_posix()).replace('/home/ubuntu/m380_gate_up_video_candidate_01',secondary.as_posix())
            ns={'__file__':str(dest/'m387_assemble.py'),'__name__':'assembly-fixture'};exec(compile(source,'actual-frozen-assembly','exec'),ns)
            try:ns['main'](sha(dest/'PACKAGE_MANIFEST.json'))
            except (RuntimeError,FileNotFoundError):
                if fault=='none':raise
            else:
                assert fault=='none',fault
                assert all(sha(dest/r['path'])==r['sha256'] for r in new['files'])
            assembly_checks+=1
    from m387_collect import decode
    row=json.loads((BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'))
    row.update(status='PASS_M387_PS_VIDEO_NUMERICAL',gate_level='sealed-DMA-PS-fixed159-video-numerical',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),PS_text_prerequisite_sha256=text_raw,ps_prefetch_enabled=True,session_weakref_dead=True,patch_registry_cleared=True,worker_started=True,extra_pynq_allocations=0,original_parser_workers=1,same_loading_path_video_sha256='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf')
    first=next(x for x in row['stage_memory'] if x['label']=='diagnostic-admission-after-seven-real-buffers')
    checks=[dict(before_payload=False,memory=x['memory'],decision=x['admission'],cma_counts=x['cma_counts']) for x in row['stage_memory'] if x['admission']]
    row['ps_session']=dict(component=dict(status='COMPLETE_COMPONENT_ONLY',stages=162,submissions=162,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=row['video_result']['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False),budget_growth_bytes=1024<<20,available_margin_bytes=64<<20,budget_baseline_rss=first['memory']['process_bytes']['VmRSS'],independent_memory_checks=checks,slot_release=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False),production_policy_changed=False,additional_dma_allocations=0,source_component_unchanged=True)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M387_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM387_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M387_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M387_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('PS_text_prerequisite_sha256','0'*64),('ps_prefetch_enabled',False),('session_weakref_dead',False),('original_parser_workers',2),('extra_pynq_allocations',1),('video_result',{}),('visual_features',{}),('preprocessed',{}),('prompt_token_ids',[]),('vision_forward_calls',0),('same_loading_path_video_sha256','0'*64),('performance_pass',True),('manifest_sha256','0'*64),('fpga_transactions',0),('safe_buffers_released',False)]:bad.append(dict(row,**{k:v}))
    for k,v in [('budget_growth_bytes',256<<20),('budget_baseline_rss',0),('slot_release',{}),('independent_memory_checks',[])]:
        x=copy.deepcopy(row);x['ps_session'][k]=v;bad.append(x)
    for k,v in [('stages',161),('submissions',163),('total_weight_bytes',0),('open_files',1),('live_views',1)]:
        x=copy.deepcopy(row);x['ps_session']['component'][k]=v;bad.append(x)
    for k,v in [('inserted_observation_calls',1),('every_retry_physical_boundary',False),('removed_observation_calls_ast_equals_original',False),('exact_frozen_head_chains',7)]:
        x=copy.deepcopy(row);x['head_observer_proof'][k]=v;bad.append(x)
    for x in bad:
        try:decode(export(x))
        except (ValueError,RuntimeError,KeyError,MemoryError):pass
        else:raise AssertionError('Invalid video result accepted')
    for log in [export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')]:
        try:decode(log)
        except ValueError:pass
        else:raise AssertionError('Invalid raw accepted')
    names=('m387_control.ps1','m387_workflow.py','m387_collect.py','m387_support.py','m387_prepare.py')
    for n in names:
        if n.endswith('.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_PS_VIDEO_PLAN_CONTROL_TWO_SOURCE_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_frozen162_window_orchestration=True,real_fixture_read_copy_and_weakrefs=True,language_windows=154,head_windows=8,explicit_fake_DMA_model_math_memory=True,Windows_test_only_ctime_adapter=os.name=='nt',strict_Linux_source_identity_unchanged=True,collector_old_video_reference_fixture_only=True,collector_negative_checks=len(bad)+3,two_source_assembly_checks=assembly_checks,controller_failure_collects=True,original_head_executor_observation_reused_same_sha=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    p=BASE/'runs/M387-ps-video-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m387_ps_video_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M387 固定159视频PS控制/回收闭合（2026-10-03）\n\n实际冻结154语言＋8head编排、真实自有fixture读/复制/slot/session弱引用；模型数学/DMA/内存替身明确。两精确旧包依赖复制{assembly_checks}项故障检查、{len(bad)+3}回收负例、控制故意失败仍收集通过。支持SHA {d}；非新视频数值或性能。下一步同COM3确认后一次本级，容量/生命周期失败停止扩大。')
    print('M387_SUPPORT_PASS',d,len(bad)+3,assembly_checks)
if __name__=='__main__':main()
