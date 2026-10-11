"""Prepare three isolated last31 chains after recovered original-reference closure."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
OLD=BASE/'candidates/M398-tail-reference-01'
PKG=BASE/'candidates/M399-tail-chain-01'
DRAFT=ROOT/'tmp/m399/chain-draft'

def change(s):
    return s.replace('M398','M399').replace('m398','m399').replace('tail_reference','tail_chain').replace('tail-reference','tail-chain').replace('TAIL_REFERENCE','TAIL_CHAIN')

def generate():
    if DRAFT.exists() or PKG.exists():raise RuntimeError('Fresh immutable draft/package required')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;s=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),lines=len(s.splitlines()))
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m398_tail_reference_closure']
    assert sha(ROOT/prior['result'])==prior['sha256']=='3a5d93c8e7f302c448511f9e8f40bfa1466a77606096f4fe6396accfe406653d'
    assert prior['status']=='PASS_ORIGINAL_TAIL_REFERENCE_ONLY' and all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    raw=ROOT/b['latest_m398_tail_reference_board']['result'];r=json.loads(raw.read_text(encoding='utf-8'))
    assert sha(raw)==prior['raw_sha256']=='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'
    assert r['status']=='PASS_M398_ORIGINAL_TAIL_REFERENCE' and r['reference_capture_pass'] and not r['tail_candidate_executed']
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='ef29003df90eacafdaea216fc4549165fddb57f0b4e03654e0a8be8c09150757'
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));assert all(sha(OLD/x['path'])==x['sha256'] for x in m['files'])
    g=change((OLD/'m398_tail_reference_gate.py').read_text(encoding='utf-8'))
    g=g.replace('from m399_reference_capture import LastLayerReferenceCapture,RetainedReferenceOwnerError','from m399_tail_chain_scope import TailChainScope,RetainedChainOwnerError')
    g=g.replace('capture_scope','chain_scope').replace('RetainedReferenceOwnerError','RetainedChainOwnerError')
    g=g.replace('sealed-DMA-original-fixed159-tail-chain','sealed-DMA-isolated-last31-three-chains')
    g=g.replace('Original complete runtime objects retained; independent fixed159-token diagnostic including36 layers/head, original math, missing-only layer35 fixtures bounded16MiB disk, no PS prefetch or extra CMA; original visual plus language and head; production policy unchanged',
                'Original full runtime/seven DMA retained; three independent original layer35 last31 chains from exact captured inputs; no vision/model forward/head, no PS prefetch/extra DMA; production policy unchanged')
    a=g.index("        capture_prior=HERE/");z=g.index('        if os.geteuid()',a)
    g=g[:a]+"        reference_pin=json.loads((HERE/'TAIL_CHAIN_PREREQUISITE.json').read_text(encoding='utf-8'))\n        result['original_reference_sha256']=reference_pin['raw_sha256']\n"+g[z:]
    a=g.index('        from m368_head_observer import bind as bind_head');z=g.index('    except RetainedChainOwnerError',a)
    g=g[:a]+'''        model=engine.language
        patch(model,'prefill',forbid('language.prefill',blocked))
        patch(engine,'stream',forbid('engine.stream',blocked))
        before=runtime.evidence()
        policy.capture('before-three-last31-chains',True);policy.begin_sampling()
        reference_path=Path('/home/ubuntu/m398_tail_reference_01/B1/load-memory.json')
        if reference_pin['raw_sha256']!='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef':raise RuntimeError('Original reference pin differs')
        chain_scope=TailChainScope(model,policy,resident,reference_path,reference_pin['raw_sha256'],enabled=True)
        scope_ref=weakref.ref(chain_scope)
        result['last31_chains']=chain_scope.run()
        chain_scope.close()
        result['chain_scope']=chain_scope.report()
        chain_scope=None
        if scope_ref() is not None:raise RetainedChainOwnerError('Closed last31 chain owner retained')
        result['scope_weakref_dead']=True
        policy.capture('after-three-last31-chains',True);policy.stop_sampling()
        after=runtime.evidence()
        result['chain_runtime_evidence']=after
        result['chain_call_delta']={key:after[key]-before[key] for key in ('logical_calls','host_calls','stage_bytes','scale_retry_count','pipeline_retry_launches','logical_expected_macros','expected_macros')}
        if result['chain_call_delta']['logical_calls']!=3 or result['chain_call_delta']['host_calls']!=len(result['transactions']):raise RuntimeError('Actual three-chain launch accounting differs')
        if result['chain_call_delta']['host_calls']!=3 or result['chain_call_delta']['scale_retry_count'] or result['chain_call_delta']['pipeline_retry_launches']:raise RuntimeError('Original retained last31 retry behavior differs')
        if result['chain_call_delta']['stage_bytes']!=45268992:raise RuntimeError('Original three family staging bytes differ')
        if result['model_forward_calls'] or result.get('vision_forward_calls',0) or blocked:raise RuntimeError('Independent chain escaped to model/vision forward')
        result['ps_prefetch_enabled']=False;result['worker_started']=False;result['silu_workspace_enabled']=False
        result['original_parser_workers']=1;result['extra_pynq_allocations']=len(allocations)-7
        result['candidate_full_model_executed']=False;result['chain_numerical_pass']=True
        result['numerical_pass']=True;result['status']='PASS_M399_LAST31_CHAIN_NUMERICAL'
        result['memory_capacity_proven']=False
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
''' + g[z:]
    g=g.replace("result['status']=='PASS_M399_ORIGINAL_TAIL_CHAIN'","result['status']=='PASS_M399_LAST31_CHAIN_NUMERICAL'")
    g=g.replace('Original tail fixture identity/lifecycle closure only; then isolated tail chain gate, no performance or candidate full video yet','Three independent last31 chains closure only; then isolated layer35 full Attention/KV plus last31 projections; no full candidate/video/performance yet')
    assert 'LastLayerReferenceCapture' not in g and 'chain_scope' in g
    assert "result['gate_return_code']=0 if result['status']=='PASS_M399_LAST31_CHAIN_NUMERICAL'" in g
    DRAFT.mkdir(parents=True)
    skip={'m398_tail_reference_gate.py','m398_export_result.py','run_m398_tail_reference.sh','m398_assemble.py','TAIL_REFERENCE_PREREQUISITE.json','SHA256SUMS'}
    for f in m['files']:
        if f['path'] not in skip:shutil.copyfile(OLD/f['path'],DRAFT/f['path'])
    atomic(DRAFT/'m399_tail_chain_gate.py',g.encode('utf-8'));shutil.copyfile(HERE/'m399_tail_chain_scope.py',DRAFT/'m399_tail_chain_scope.py')
    atomic(DRAFT/'TAIL_CHAIN_PREREQUISITE.json',encoded(dict(closure=prior,raw_sha256=sha(raw),reference_manifest=r['reference_capture'],original_package_sha256=sha(OLD/'PACKAGE_MANIFEST.json'))))
    for src,dst in [('m398_export_result.py','m399_export_result.py'),('run_m398_tail_reference.sh','run_m399_tail_chain.sh'),('m398_assemble.py','m399_assemble.py')]:
        s=change((OLD/src).read_text(encoding='utf-8')).replace('sealed-DMA-original-fixed159-tail-chain','sealed-DMA-isolated-last31-three-chains')
        if src=='m398_assemble.py':
            s=s.replace("OLD=Path('/home/ubuntu/m387_ps_video_candidate_01')","OLD=Path('/home/ubuntu/m398_tail_reference_candidate_01')").replace('2613ed813ca8d873076b0a6443309242f9c0594e655e57dcfe4d1859839f4fbb',sha(OLD/'PACKAGE_MANIFEST.json'))
        atomic(DRAFT/dst,s.encode('utf-8'))
    assert "$remote='/home/ubuntu/m398_tail_reference_candidate_01'" in (HERE/'m398_control.ps1').read_text(encoding='utf-8-sig')
    assert "OLD=Path('/home/ubuntu/m398_tail_reference_candidate_01')" in (DRAFT/'m399_assemble.py').read_text(encoding='utf-8')
    for src,dst in [('m398_control.ps1','m399_control.ps1'),('m398_workflow.py','m399_workflow.py')]:
        s=change((HERE/src).read_text(encoding='utf-8-sig')).replace('M387-ps-video-01','M398-tail-reference-01')
        s=s.replace('原固定159视频末层参考捕获','三个独立末31 chain').replace('末层参考捕获包传输核对','末批chain包传输核对').replace('精确M387','精确M398')
        atomic(HERE/dst,s.encode('utf-8'))
    atomic(ROOT/'tmp/m399/recovery_read.json',encoded(recovery))
    print('M399_DRAFT_CREATED',len(list(DRAFT.iterdir())))

def freeze():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in DRAFT.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads((DRAFT/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            imports=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,x) for x in imports if x and x not in trees and x not in allowed)
    assert not missing,missing
    s=(DRAFT/'m399_tail_chain_gate.py').read_text(encoding='utf-8');main=next(n for n in symtable.symtable(s,'gate','exec').get_children() if n.get_name()=='main')
    assert next(t for t in main.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert 'engine.stream(request)' not in s and 'chain_scope.run()' in s and 'chain_scope.close()' in s
    assert 'unsafe=unsafe or chain_scope is not None' in s
    for f in json.loads((DRAFT/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/f['path'])==f['sha256']
    assert sha(DRAFT/'m399_tail_chain_scope.py')==sha(HERE/'m399_tail_chain_scope.py')
    PKG.mkdir(parents=True)
    for p in DRAFT.iterdir():shutil.copyfile(p,PKG/p.name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(f['sha256']+'  '+f['path']+'\n' for f in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M399-last31-three-chains-v1',files=rows,file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows))))
    value=dict(status='PASS_OFFLINE_LAST31_CHAIN_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),build_id='0x4D333537',recursive_missing=missing,python310_syntax=True,
               file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows),isolated_chain_count=3,tokens_per_chain=31,reference_files=7,
               expected_logical_calls=3,expected_physical_chain_calls=3,expected_minimal_plus_chain_calls=4,original_stage_bytes=45268992,
               extra_DMA=0,model_forward_calls=0,PS_prefetch=False,parser_workers=1,production_policy_unchanged=True,
               board_run=False,numerical_pass=False,performance_pass=False,test_support_pending=True)
    out=BASE/'runs/M399-tail-chain-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m399_tail_chain_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M399 三个末31 chain准备（2026-10-04）\n\nSHA `{h}`，manifest `{value["manifest_sha256"]}`；参考为已闭合M398原159末层12NPY，只使用三输入/四输出七文件，使用前后完整file/tensor SHA与身份核对。原完整runtime/seven DMA，三个独立原M238 family各31行，预期3逻辑/3物理加minimal4，原stage45268992B，不执行视觉/Prefill/head。默认关闭，无新增DMA，parser1、PS/SiLU workspace关闭，生产64MiB保持；missing0/3.10/同SHA硬件闭合复用。尚需实际封装/回收/控制支持，通过后上板一次三chain；任何失败停本级，无单层/完整候选数值或性能。')
    print(json.dumps(value|{'result_sha256':h}))

if __name__=='__main__':
    if sys.argv[1:]==['generate']:generate()
    elif sys.argv[1:]==['freeze']:freeze()
    else:raise SystemExit('generate | freeze')
