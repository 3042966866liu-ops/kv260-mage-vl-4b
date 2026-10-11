"""Validate only new one-request dispatch and saved-byte protocol; no hardware."""
import ast,base64,copy,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import verify_package
import m441_video_collect09 as c

def fixture():
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m432_integrated_board']
    assert w.sha(w.ROOT/e['result'])==e['sha256']
    r=json.loads((w.ROOT/e['result']).read_bytes());s=r['samples'][1];skip=r['samples'][0]['counts']['host_calls']
    r.update(status='PASS_M441V_INTEGRATED_VIDEO_NUMERICAL',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),build_id='0x4D343431',samples=[s],model_forward_calls=1,vision_forward_calls=1,fpga_transactions=1068,host_calls=781,logical_calls=778,transactions=r['transactions'][skip:],integrated_visual=[r['integrated_visual'][1]],integrated_exact_comparisons=[r['integrated_exact_comparisons'][1]],logit_files=[r['logit_files'][1]],saved_reference_variant='late13_23_candidate',prior_fixed_text_raw_sha256='0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7',source_compatibility_checked_before_overlay=True,prior_board_sha256='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d')
    r['original_exact_comparison']=dict(r['integrated_exact_comparisons'][0],decision=True)
    for x in [r['final_snapshot'],r['same_overlay_minimal_proof']['snapshot'],s['final_snapshot']]+[t['completed_snapshot'] for t in r['visual_transactions']]:x['ap_return']=0x4d343431
    r.pop('logit_comparison',None)
    return r,e['sha256']

def emit(r):
    raw=w.encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M441V_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM441V_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M441V_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M441V_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'

def support():
    verify_package(c.PKG);r,source=fixture();c.check(r)
    assert c.decode(emit(r))[2]==r
    failed=dict(r,status='FAIL',gate_return_code=1,errors=['explicit fixture'])
    assert c.decode(emit(failed))[2]==failed
    mutations=[('manifest_sha256','0'*64),('build_id','0x4D333537'),('model_forward_calls',2),('vision_forward_calls',2),('fpga_transactions',1067),('logical_calls',1556),('transactions',r['transactions'][:-1]),('integrated_boundaries',r['integrated_boundaries'][:-1]),('visual_transactions',r['visual_transactions'][:-1]),('visual_staging',r['visual_staging'][:-1]),('saved_reference_variant','original'),('borrowed_extra_DMA',1),('peak_live_visual_layer_scopes',2),('visual_static_cache_invalidated',False),('safe_buffers_released',False),('unsafe_buffers_retained',True),('source_compatibility_checked_before_overlay',False),('prior_fixed_text_raw_sha256','0'*64),('prior_board_sha256','0'*64),('temperature_measurement_enabled',True),('performance_pass',True),('gate_return_code',False)]
    bads=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')]
    for k,v in mutations:bads.append(emit(dict(r,**{k:v})))
    for field in ('keys','values','families','logits','decision','counts'):
        b=copy.deepcopy(r)
        if isinstance(b['samples'][0][field],list):b['samples'][0][field].pop()
        elif field=='logits':b['samples'][0][field]['sha256']='0'*64
        elif field=='decision':b['samples'][0][field]['knife_score']=0.1
        else:b['samples'][0][field]['stage_bytes']-=1
        bads.append(emit(b))
    b=copy.deepcopy(r);b['visual_transactions'][0]['completed_snapshot']['ap_return']=0;bads.append(emit(b))
    for bad in bads:
        try:c.decode(bad)
        except (ValueError,KeyError,RuntimeError):pass
        else:raise AssertionError('Broken full result accepted')
    # Execute the actual new exporter; root and filesystem ownership are explicit Windows fakes.
    spec=importlib.util.spec_from_file_location('actual_m441_video_export',c.PKG/'m441_video_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    folder=w.ROOT/'tmp/m441_video09/export_fixture';folder.mkdir(parents=True,exist_ok=False);saved=folder/'BOARD_RESULT.json';atomic(saved,w.encoded(r),immutable=True)
    buf=io.StringIO()
    with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda unused:None),patch('sys.stdout',buf):ex.emit_saved()
    assert c.decode(buf.getvalue())[2]==r
    try:
        with patch.object(ex.os,'geteuid',lambda:1000,create=True):ex.emit_saved()
    except RuntimeError:pass
    else:raise AssertionError('Exporter accepted non-root')
    control=w.HERE/'m441_video_control09.ps1';pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp=subprocess.run([pwsh,'-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert cp.returncode==0 and 'M441V_CONTROL_SELFTEST_PASS' in cp.stdout,cp.stdout+cp.stderr
    # Only the candidate request is scheduled; actual scalar guard rejects A and a second request before imports.
    src=(c.PKG/'m432_trials.py').read_text(encoding='utf-8');tr=ast.parse(src)
    loop=next(n for n in ast.walk(tr) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [x.id for x in n.target.elts]==['i','visual'])
    assert eval(compile(ast.Expression(loop.iter),'<actual-dispatch>','eval'),{'features':['A','B']})==((1,'B'),)
    psrc=(c.PKG/'m432_request_visual.py').read_text(encoding='utf-8');pt=ast.parse(psrc)
    cls=next(n for n in pt.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__call__')
    guard=next(n for n in fn.body if isinstance(n,ast.If));test=compile(ast.Expression(guard.test),'<actual-provider-guard>','eval')
    from types import SimpleNamespace
    for index,count,rejected in ((1,0,False),(0,0,True),(1,1,True),(2,0,True)):
        obj=SimpleNamespace(result={'integrated_visual':[None]*count},disposed=False)
        assert eval(test,{'index':index,'self':obj}) is rejected
    # External recursive modules must resolve to the pinned runtime or six exact reused visual manifests.
    plan=json.loads((c.PKG/'PLAN.json').read_bytes());packages=[]
    for row in plan['visual_reused_packages']:
        matches=[p.parent for p in (w.BASE/'candidates').glob('*/PACKAGE_MANIFEST.json') if w.sha(p)==row['manifest_sha256']];assert len(matches)==1
        verify_package(matches[0]);packages.append(matches[0])
    reuse=w.BASE/'candidates/M368-staged-video-03';verify_package(reuse);packages.append(reuse)
    closure=json.loads((c.PKG/'SOURCE_CLOSURE.json').read_bytes());names={p.stem for p in c.PKG.glob('*.py')}|set(closure['modules'])|set(sys.stdlib_module_names)|{'numpy','torch','pynq','tokenizers'}
    for root in packages:names|={p.stem for p in root.glob('*.py')}
    for p in c.PKG.glob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
        for n in ast.walk(tree):
            refs=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            assert all(not ref or ref in names for ref in refs),(p.name,refs)
    rejected=w.ROOT/'tmp/m441_video09/package_staging'
    out=w.BASE/'runs/M441-fixed-video-support-09';paths=[c.PKG/x for x in ('m441_video_gate.py','m441_video_entry.py','m441_video_export.py','m441_video_assemble.py','m432_trials.py','m432_request_visual.py','run_m441_video.sh')]+[control,w.HERE/'m441_video_collect09.py',Path(__file__)]
    v=dict(status='PASS_M441_FIXED_VIDEO_SUPPORT09',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),collector_fixture_explicitly_not_board=True,reference_raw_sha256=source,collector_negative_checks=len(bads),actual_exporter_full_decoder_pass=True,actual_one_B_dispatch_and_preimport_provider_guard=True,controller_failure_collection_verified=True,recursive_import_missing=0,unchanged_original_borrowed_lifecycle=True,old_remote_path_rejected_before_package_and_board=True,rejected_preparation_files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(rejected.iterdir())],files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in paths],board_executed=False,performance_pass=False)
    atomic(out/'CONTROL_SELFTEST.txt',(cp.stdout+cp.stderr).encode('utf-8'),immutable=True);atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_video_support',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=v['manifest_sha256']),f'## M441 固定159视频支持09（2026-10-09）\n\nSHA {d}；实际单B调度/资源前provider拒绝、完整原M432派生明确fixture、{len(bads)}回收破坏负例及实际exporter→decoder/非root拒绝、控制故意失败收集和精确复用闭包通过。最初离线远程目录推断被原控制证据拒绝，暂存文件保留，正确目录由实际M432控制器绑定；0板端/性能。')
    print(v['status'],d)

def receipt():
    logs=w.ROOT/'tmp/m441_video09';a=logs/'assembly.log';s=logs/'upload_syntax.log'
    assert 'M441V_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig') and '__M441V_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig') and '__M441V_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    out=w.BASE/'runs/M441-fixed-video-transfer-09';v=dict(status='PASS_M441_FIXED_VIDEO_TRANSFER_ONLY09',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),logs=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))],assembly_full_whitelist_verified=True,bash_n_pass=True,board_executed=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_video_transfer',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=v['manifest_sha256']),f'## M441 固定159视频传输09（2026-10-09）\n\nSHA {d}；manifest-first900B/逐文件SHA/精确旧目录与保存原text字节组装/root bash-n通过，0执行；下一步一次固定159视频，已有attempt只Collect。')
    print(v['status'],d)

if __name__=='__main__':
    if sys.argv[1:]==['receipt']:receipt()
    else:support()
