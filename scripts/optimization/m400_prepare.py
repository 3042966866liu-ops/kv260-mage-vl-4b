"""Prepare one isolated last-layer numerical gate after M399 closure."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_tail_layer_scope import derive
OLD=BASE/'candidates/M399-tail-chain-01'
PKG=BASE/'candidates/M400-tail-layer-01'
DRAFT=ROOT/'tmp/m400/layer-draft'
RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
SOURCE=RELEASE/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'


def change(s):
    return s.replace('M399','M400').replace('m399','m400').replace('tail_chain','tail_layer').replace('tail-chain','tail-layer').replace('TAIL_CHAIN','TAIL_LAYER')


def generate():
    if DRAFT.exists() or PKG.exists():raise RuntimeError('Fresh draft/package required')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;s=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),lines=len(s.splitlines()))
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m399_tail_chain_closure']
    assert sha(ROOT/prior['result'])==prior['sha256']=='90303bfb7f0709843c49cfef16af20d599376a4824107d907ff9fbcd6f50d6c4'
    assert prior['status']=='PASS_LAST31_THREE_CHAINS_ONLY'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    original=BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json';r=json.loads(original.read_text(encoding='utf-8'))
    assert sha(original)=='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'
    chain_raw=ROOT/b['latest_m399_tail_chain_board']['result']
    assert sha(chain_raw)==prior['raw_sha256']=='924ae716e4e399b6f94f522d279b5f6472328bbb6049ebfb6d16004d5f95c992'
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='e762fa83ff45ad2b50266370e42de43ab27b30517efaa306ef1c0f04cae8c5df'
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert all(sha(OLD/f['path'])==f['sha256'] for f in m['files'])
    contract_path=RELEASE/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    contract=json.loads(contract_path.read_text(encoding='utf-8'));chains=[c for c in contract['chains'] if c.get('layer')==35]
    assert [c['family'] for c in chains]==['qkv','attention_out','gate_up','mlp_down']
    expected_stage=sum(c['staged_bytes_all_shards'] for c in chains)
    expected_macros=sum(c['expected_macros']*(5 if c['family']=='qkv' else 1) for c in chains)
    assert expected_stage==53624832 and expected_macros==81920000
    families=[r['video_result']['families'][i] for i in range(len(r['video_result']['families'])) if r['video_result']['families'][i]['layer']==35]
    qkv=families[0];assert qkv['family']=='qkv'
    f=r['reference_capture']['fixtures'];prefix='model.language_model.layers.35.'
    from m399_tail_chain_scope import PLAN
    for family,source,goldens in PLAN:
        families[[x['family'] for x in families].index(family)]=dict(layer=35,family=family,input=f[source]['tensor'],output={prefix+k:f[n]['tensor'] for k,n in goldens.items()})
    transactions=[x for x in r['transactions'] if x['layer']==35 and x['family']=='qkv']
    assert len(transactions)==5
    for family,_,_ in PLAN:transactions.append([x for x in r['transactions'] if x['layer']==35 and x['family']==family][-1])
    assert len(transactions)==8 and all(x['method']=='_launch_prepacked' for x in transactions)
    # M238 accepts the two final original buffers in order tail128 then block96.
    scales=[x for x in r['video_result']['scale_attempts'] if x['layer']==35 and x['family']=='qkv']
    for family,_,_ in PLAN:
        candidates=[x for x in r['video_result']['scale_attempts'] if x['layer']==35 and x['family']==family]
        assert len(candidates)==5;scales.append(candidates[3])
    assert len(scales)==8 and all(len(x['attempted_shifts'])==1 for x in scales)
    pin=dict(closure=prior,chain_raw_sha256=sha(chain_raw),raw_sha256=sha(original),reference_manifest=r['reference_capture'],
             expected_families=families,expected_key=r['video_result']['keys'][35],expected_value=r['video_result']['values'][35],
             expected_transactions=transactions,expected_scale_attempts=scales,
             original_contract_sha256=sha(contract_path),chains=chains,expected_stage_bytes=expected_stage,expected_macros=expected_macros)
    g=change((OLD/'m399_tail_chain_gate.py').read_text(encoding='utf-8'))
    g=g.replace('TailChainScope','TailLayerScope').replace('chain_scope','layer_scope')
    g=g.replace('sealed-DMA-isolated-last31-three-chains','sealed-DMA-isolated-layer35-fullAttention-last31')
    g=g.replace('three independent original layer35 last31 chains from exact captured inputs; no vision/model forward/head','isolated layer35 original full159 QKV/Attention/KV plus last31 post-attention projections; no vision/full-model forward/head')
    start=g.index('        model=engine.language');end=g.index('    except RetainedChainOwnerError',start)
    g=g[:start]+'''        model=engine.language
        patch(model,'prefill',forbid('language.prefill',blocked))
        patch(engine,'stream',forbid('engine.stream',blocked))
        before=runtime.evidence()
        policy.capture('before-layer35-tail',True);policy.begin_sampling()
        reference_path=Path('/home/ubuntu/m398_tail_reference_01/B1/load-memory.json')
        if reference_pin['raw_sha256']!='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef':raise RuntimeError('Original reference pin differs')
        layer_scope=TailLayerScope(model,policy,resident,reference_path,reference_pin['raw_sha256'],enabled=True)
        scope_ref=weakref.ref(layer_scope)
        result['layer_result']=layer_scope.run(sys.modules['m241_video_language_runtime'],(HERE/'frozen_last_layer.py').read_text(encoding='utf-8'))
        layer_scope.close()
        result['layer_scope']=layer_scope.report()
        layer_scope=None
        if scope_ref() is not None:raise RetainedChainOwnerError('Closed layer owner retained')
        result['scope_weakref_dead']=True
        policy.capture('after-layer35-tail',True);policy.stop_sampling()
        after=runtime.evidence()
        result['layer_runtime_evidence']=after
        result['layer_call_delta']={key:after[key]-before[key] for key in ('logical_calls','host_calls','stage_bytes','scale_retry_count','pipeline_retry_launches','logical_expected_macros','expected_macros')}
        if result['layer_call_delta']['logical_calls']!=8 or result['layer_call_delta']['host_calls']!=len(result['transactions']):raise RuntimeError('Actual layer launch accounting differs')
        if result['layer_call_delta']['host_calls']!=8 or result['layer_call_delta']['scale_retry_count'] or result['layer_call_delta']['pipeline_retry_launches']:raise RuntimeError('Matched original layer retained retry behavior differs')
        if result['layer_call_delta']['stage_bytes']!=reference_pin['expected_stage_bytes'] or result['layer_call_delta']['expected_macros']!=reference_pin['expected_macros'] or result['layer_call_delta']['logical_expected_macros']!=reference_pin['expected_macros']:raise RuntimeError('Original layer staging/macros differ')
        if after['scale_attempts']!=reference_pin['expected_scale_attempts']:raise RuntimeError('Original retained scale choices differ')
        if model.grouped_attention_calls!=1 or result['model_forward_calls'] or result.get('vision_forward_calls',0) or blocked:raise RuntimeError('Layer escaped to full-model/vision/head')
        result['isolated_layer_calls']=1
        result['ps_prefetch_enabled']=False;result['worker_started']=False;result['silu_workspace_enabled']=False
        result['original_parser_workers']=1;result['extra_pynq_allocations']=len(allocations)-7
        result['candidate_full_model_executed']=False;result['layer_numerical_pass']=True
        result['numerical_pass']=True;result['status']='PASS_M400_TAIL_LAYER_NUMERICAL'
        result['memory_capacity_proven']=False
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
''' +g[end:]
    g=g.replace('PASS_M400_LAST31_CHAIN_NUMERICAL','PASS_M400_TAIL_LAYER_NUMERICAL')
    g=g.replace('Three independent last31 chains closure only; then isolated layer35 full Attention/KV plus last31 projections; no full candidate/video/performance yet','Isolated layer35 numeric/lifetime closure only; then fixed30 text. No full video/performance yet')
    marker="        result['original_reference_sha256']=reference_pin['raw_sha256']\n"
    g=g.replace(marker,marker+"        chain_path=Path('/home/ubuntu/m399_tail_chain_01/B1/load-memory.json')\n        chain_prior=json.loads(chain_path.read_text(encoding='utf-8'))\n        if sha256(chain_path)!=reference_pin['chain_raw_sha256'] or chain_prior['status']!='PASS_M399_LAST31_CHAIN_NUMERICAL' or chain_prior['gate_return_code']:raise RuntimeError('Actual prior chain result differs')\n        result['chain_prerequisite_sha256']=sha256(chain_path)\n")
    DRAFT.mkdir(parents=True)
    skip={'m399_tail_chain_gate.py','m399_export_result.py','run_m399_tail_chain.sh','m399_assemble.py','TAIL_CHAIN_PREREQUISITE.json','SHA256SUMS'}
    for f in m['files']:
        if f['path'] not in skip:shutil.copyfile(OLD/f['path'],DRAFT/f['path'])
    atomic(DRAFT/'m400_tail_layer_gate.py',g.encode('utf-8'))
    for n in ('m400_tail_layer_scope.py','m397_last_layer_tail_scope.py','m343_layer_scope.py'):shutil.copyfile(HERE/n,DRAFT/n)
    atomic(DRAFT/'frozen_last_layer.py',derive(SOURCE.read_bytes()).encode('utf-8'))
    atomic(DRAFT/'TAIL_LAYER_PREREQUISITE.json',encoded(pin))
    for src,dst in [('m399_export_result.py','m400_export_result.py'),('run_m399_tail_chain.sh','run_m400_tail_layer.sh'),('m399_assemble.py','m400_assemble.py')]:
        s=change((OLD/src).read_text(encoding='utf-8')).replace('sealed-DMA-isolated-last31-three-chains','sealed-DMA-isolated-layer35-fullAttention-last31')
        if src=='m399_assemble.py':s=s.replace('/home/ubuntu/m398_tail_reference_candidate_01','/home/ubuntu/m399_tail_chain_candidate_01').replace('ef29003df90eacafdaea216fc4549165fddb57f0b4e03654e0a8be8c09150757',sha(OLD/'PACKAGE_MANIFEST.json'))
        atomic(DRAFT/dst,s.encode('utf-8'))
    assert "$remote='/home/ubuntu/m399_tail_chain_candidate_01'" in (HERE/'m399_control.ps1').read_text(encoding='utf-8-sig')
    for src,dst in [('m399_control.ps1','m400_control.ps1'),('m399_workflow.py','m400_workflow.py')]:
        s=change((HERE/src).read_text(encoding='utf-8-sig')).replace('M398-tail-reference-01','M399-tail-chain-01')
        s=s.replace('latest_m400_tail_layer','latest_m400_tail_layer')
        s=s.replace('三个独立末31 chain','独立layer35组合').replace('末批chain包传输核对','末层单层包传输核对').replace('精确M398','精确M399')
        atomic(HERE/dst,s.encode('utf-8'))
    atomic(ROOT/'tmp/m400/recovery_read.json',encoded(recovery))
    print('M400_DRAFT_CREATED',len(list(DRAFT.iterdir())),expected_stage,expected_macros)


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
    s=(DRAFT/'m400_tail_layer_gate.py').read_text(encoding='utf-8');main=next(n for n in symtable.symtable(s,'gate','exec').get_children() if n.get_name()=='main')
    assert next(t for t in main.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert 'unsafe=unsafe or layer_scope is not None' in s and 'layer_scope.run(' in s and 'layer_scope.close()' in s
    for f in json.loads((DRAFT/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/f['path'])==f['sha256']
    PKG.mkdir(parents=True)
    for p in DRAFT.iterdir():shutil.copyfile(p,PKG/p.name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(f['sha256']+'  '+f['path']+'\n' for f in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M400-isolated-last-layer-tail-v1',files=rows,file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows))))
    value=dict(status='PASS_OFFLINE_LAST_LAYER_TAIL_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),build_id='0x4D333537',recursive_missing=missing,python310_syntax=True,
               file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows),isolated_layer=35,full_tokens=159,tail_tokens=31,reference_files=11,
               expected_logical_calls=8,expected_physical_layer_calls=8,expected_minimal_plus_layer_calls=9,original_stage_bytes=53624832,expected_macros=81920000,
               extra_DMA=0,PS_prefetch=False,SiLU_workspace=False,parser_workers=1,production_policy_unchanged=True,
               board_run=False,numerical_pass=False,performance_pass=False,test_support_pending=True)
    out=BASE/'runs/M400-tail-layer-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m400_tail_layer_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M400 末层组合准备（2026-10-04）\n\nSHA `{h}`，manifest `{value["manifest_sha256"]}`；原M398真实末层输入重算layer35，全159QKV/RoPE/Attention/KV保持，后三投影31行。8逻辑/8层物理加minimal9，原stage53624832B/宏81920000，11项NPY前后身份与完整SHA核对、完整QKV/KV SHA、Attention/末批/hidden/norm逐位核对。原seven DMA封锁，默认关闭、parser1，PS/SiLU workspace关闭，生产64MiB保持；missing0/3.10/同SHA硬件47项复用。尚需实际入口/回收/控制支持，未上传或上板，无新性能。')
    print(json.dumps(value|{'result_sha256':h}))


if __name__=='__main__':
    if sys.argv[1:]==['generate']:generate()
    elif sys.argv[1:]==['freeze']:freeze()
    else:raise SystemExit('generate | freeze')
