"""Freeze fixed30 full model gate after M400 closure; no board access."""
import ast
import copy
import hashlib
import json
import shutil
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m401_prefill_source import derive,validate
from m400_prepare_layer02 import replace_once as rep
OLD=BASE/'candidates/M400-tail-layer-02'
PKG=BASE/'candidates/M401-tail-text-01'
TEXT=BASE/'candidates/M366-staged-text-03'
SOURCE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'

def version(t):return t.replace('M400','M401').replace('m400','m401').replace('tail_layer','tail_text').replace('tail-layer','tail-text').replace('TAIL_LAYER','TAIL_TEXT')

def main():
    if PKG.exists():raise RuntimeError('Immutable new package required')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;s=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),lines=len(s.splitlines()),bytes=p.stat().st_size)
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    closure=BASE/'runs/M400-tail-layer-closure-02/RESULT.json'
    assert sha(closure)=='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043'
    prior=json.loads(closure.read_text(encoding='utf-8'));assert prior['layer_numerical_pass'] and prior['stable_restored']
    assert all(sha(closure) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='79ad703a9e23761f922084243f15de1e582058e83db552b10a3bae7d36ca5fc7'
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert all(sha(OLD/r['path'])==r['sha256'] for r in m['files'])
    for key in ('latest_m366_staged_layer_board',):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']=='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb'
    expected=json.loads((TEXT/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))
    baseline=expected['baseline'];assert baseline['logical_calls']==162 and baseline['host_calls']==165 and baseline['token']==17
    frozen=derive(SOURCE.read_bytes()).encode('utf-8');frozen_sha=hashlib.sha256(frozen).hexdigest();proof=validate(SOURCE.read_bytes(),frozen,frozen_sha)
    payload={r['path']:(OLD/r['path']).read_bytes() for r in m['files'] if r['path'] not in ('SHA256SUMS','m400_tail_layer_scope.py','m400_tail_source_02.py','m400_layer_entry_02.py','frozen_last_layer.py')}
    for old,new in [('m400_tail_layer_gate.py','m401_tail_text_gate.py'),('m400_export_result.py','m401_export_result.py'),('run_m400_tail_layer.sh','run_m401_tail_text.sh'),('m400_assemble.py','m401_assemble.py')]:payload[new]=version(payload.pop(old).decode('utf-8')).encode('utf-8')
    payload['m401_prefill_source.py']=(HERE/'m401_prefill_source.py').read_bytes()
    payload['frozen_prefill.py']=frozen
    payload['M400_LAYER_CLOSURE.json']=closure.read_bytes()
    payload['LAYER_EXPECTED.json']=(TEXT/'LAYER_EXPECTED.json').read_bytes()
    payload['m366_head_observer.py']=(TEXT/'m366_head_observer.py').read_bytes()
    # Reuse all original scope ownership/invocation checks, substitute only binding.
    scope=(HERE/'m397_last_layer_tail_scope.py').read_text(encoding='utf-8')
    a=scope.index('        original=ast.parse(raw.decode(');z=scope.index('        self.bindings.append(namespace)',a)
    scope=scope[:a]+'''        from m401_prefill_source import derive
        namespace=dict(vars(module));namespace['_m397_select']=self.select
        generated=derive(raw)
        exec(compile('from __future__ import annotations\\n'+generated,'<m401-frozen-original-prefill-tail>','exec'),namespace)
'''+scope[z:]
    payload['m401_prefill_tail_scope.py']=scope.encode('utf-8')
    entry=(HERE/'m400_layer_entry_02.py').read_text(encoding='utf-8').replace('from m400_tail_source_02 import validate','from m401_prefill_source import validate').replace('fc5543e48aecc49dad0c08eb5efefa82a12ed607088b30cbba1a9b792d06f40b',frozen_sha).replace('frozen_last_layer.py','frozen_prefill.py').replace('m400_tail_layer_gate_02','m401_tail_text_gate_01').replace('m400_tail_layer_gate.py','m401_tail_text_gate.py').replace('--enable-tail-layer','--enable-tail-text').replace('M400','M401')
    payload['m401_text_entry.py']=entry.encode('utf-8')
    gate=payload['m401_tail_text_gate.py'].decode('utf-8')
    gate=rep(gate,'from m401_tail_text_scope import TailLayerScope,RetainedChainOwnerError','from m401_prefill_tail_scope import LastLayerTailScope,RetainedTailOwnerError')
    gate=gate.replace('RetainedChainOwnerError','RetainedTailOwnerError').replace('--enable-tail-layer','--enable-tail-text').replace('args.enable_tail_layer','args.enable_tail_text').replace('/home/ubuntu/m401_tail_text_02','/home/ubuntu/m401_tail_text_01')
    gate=gate.replace("gate_level='sealed-DMA-isolated-layer35-fullAttention-last31'","gate_level='sealed-DMA-fixed30-full36-layer-tail-prefill'")
    gate=gate.replace("isolated layer35 original full159 QKV/Attention/KV plus last31 post-attention projections; no vision/full-model forward/head", "fixed30 complete36-layer Prefill and full LM head; final batch selector only; no vision/video")
    marker="        result['chain_prerequisite_sha256']=sha256(chain_path)\n"
    gate=rep(gate,marker,marker+"        layer_prior_path=Path('/home/ubuntu/m400_tail_layer_02/B1/load-memory.json')\n        if sha256(layer_prior_path)!='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c':raise RuntimeError('Actual single-layer result SHA differs')\n        layer_prior=json.loads(layer_prior_path.read_text(encoding='utf-8'))\n        if layer_prior['status']!='PASS_M400_TAIL_LAYER_NUMERICAL' or layer_prior['gate_return_code']:raise RuntimeError('Single-layer prerequisite rejected')\n        result['layer_prerequisite_sha256']=sha256(layer_prior_path)\n        result['layer_closure_sha256']=sha256(HERE/'M400_LAYER_CLOSURE.json')\n        if result['layer_closure_sha256']!='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043':raise RuntimeError('Layer closure differs')\n")
    a=gate.index('        model=engine.language');z=gate.index('    except RetainedTailOwnerError',a)
    text_gate=(TEXT/'m366_staged_text_gate.py').read_text(encoding='utf-8')
    region=text_gate[text_gate.index('        from m366_head_observer import bind as bind_head'):text_gate.index('    except CapacityRejected as exc:')].replace('M366','M401')
    region=rep(region,"        token,logits,kv=model.prefill(hidden.copy())",'''        layer_scope=LastLayerTailScope(model,policy,resident,tokens=30,enabled=True)
        scope_ref=weakref.ref(layer_scope)
        candidate=layer_scope.bind(sys.modules['m241_video_language_runtime'])
        token,logits,kv=candidate(model,hidden.copy())
        del candidate
        layer_scope.close()
        result['tail_scope']=layer_scope.report()
        layer_scope=None
        if scope_ref() is not None:raise RetainedTailOwnerError('Closed Prefill owner retained')
        result['scope_weakref_dead']=True''')
    region=region.replace("result['status']='PASS_M401_FIXED_TEXT_DIAGNOSTIC'","result['status']='PASS_M401_TAIL_TEXT_NUMERICAL'")
    region=rep(region,"        result['memory_capacity_proven']=False", "        result['memory_capacity_proven']=False\n        result['candidate_full_model_executed']=True\n        result['original_parser_workers']=1;result['ps_prefetch_enabled']=False;result['silu_workspace_enabled']=False\n        result['extra_pynq_allocations']=len(allocations)-7\n        del hidden,selected_rows,token,logits,kv,output\n") if 'del hidden' in region else region
    # `output` exists only inside family callback. Dispose only original retained locals.
    region=rep(region,"        result['memory_capacity_proven']=False", "        result['memory_capacity_proven']=False\n        result['candidate_full_model_executed']=True\n        result['original_parser_workers']=1;result['ps_prefetch_enabled']=False;result['silu_workspace_enabled']=False\n        result['extra_pynq_allocations']=len(allocations)-7\n        del hidden,selected_rows,token,logits,kv\n")
    gate=gate[:a]+region+gate[z:]
    gate=gate.replace('PASS_M401_TAIL_LAYER_NUMERICAL','PASS_M401_TAIL_TEXT_NUMERICAL').replace('Isolated layer35 numeric/lifetime closure only; then fixed30 text. No full video/performance yet','Fixed30 complete36-layer/head numerical closure only; next separately prepare fixed159 video. No performance unlocked.')
    payload['m401_tail_text_gate.py']=gate.encode('utf-8')
    payload['m401_export_result.py']=payload['m401_export_result.py'].replace(b'/home/ubuntu/m401_tail_text_02',b'/home/ubuntu/m401_tail_text_01')
    payload['run_m401_tail_text.sh']=payload['run_m401_tail_text.sh'].replace(b'/home/ubuntu/m401_tail_text_02',b'/home/ubuntu/m401_tail_text_01').replace(b'm401_layer_entry_02.py',b'm401_text_entry.py').replace(b'--enable-tail-layer',b'--enable-tail-text')
    assembly=payload['m401_assemble.py'].decode('utf-8').replace('/home/ubuntu/m401_tail_text_candidate_01','/home/ubuntu/m400_tail_layer_candidate_02').replace('2a04363254f7d0fe49e49551e41d50609270fa67328650f701b44b001d0de2fa',sha(OLD/'PACKAGE_MANIFEST.json'))
    payload['m401_assemble.py']=assembly.encode('utf-8')
    trees={n[:-3]:ast.parse(v.decode('utf-8'),feature_version=(3,10)) for n,v in payload.items() if n.endswith('.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads(payload['SOURCE_CLOSURE.json'])['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for mod,tree in trees.items():
        for n in ast.walk(tree):
            imports=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((mod,x) for x in imports if x and x not in trees and x not in allowed)
    assert not missing,missing
    PKG.mkdir(parents=True)
    for n,v in payload.items():atomic(PKG/n,v)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M401-fixed30-full-prefill-tail-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    # New host controller retains bounded copy/failure collection from verified02.
    controller=version((HERE/'m400_control02.ps1').read_text(encoding='utf-8-sig')).replace('M401-tail-text-02','M401-tail-text-01').replace('m401_tail_text_candidate_02','m401_tail_text_candidate_01').replace('M401-tail-text-01/PACKAGE_MANIFEST.json','M400-tail-layer-02/PACKAGE_MANIFEST.json')
    controller=controller.replace("$local='deployment/mage_vl4b/optimization_v1/candidates/M400-tail-layer-02'","$local='deployment/mage_vl4b/optimization_v1/candidates/M401-tail-text-01'")
    controller=controller.replace('tmp/m40102/','tmp/m401/').replace('m401_workflow02.py','m401_workflow.py').replace('M401-tail-text-board-02','M401-tail-text-board-01')
    for key in ('preparation','support','transfer'):controller=controller.replace('latest_m401_tail_text_'+key+'02','latest_m401_tail_text_'+key)
    atomic(HERE/'m401_control.ps1',controller.encode('utf-8'))
    workflow=version((HERE/'m400_workflow02.py').read_text(encoding='utf-8')).replace("PKG=BASE/'candidates/M401-tail-text-02'","PKG=BASE/'candidates/M401-tail-text-01'").replace("OLD=BASE/'candidates/M401-tail-text-01'","OLD=BASE/'candidates/M400-tail-layer-02'").replace('tmp/m40102','tmp/m401').replace('M401-tail-text-transfer-02','M401-tail-text-transfer-01').replace('latest_m401_tail_text_transfer02','latest_m401_tail_text_transfer').replace('from m401_collect02 import','from m401_collect import').replace('精确M401-01','精确M400-02')
    atomic(HERE/'m401_workflow.py',workflow.encode('utf-8'))
    value=dict(status='DRAFT_M401_FIXED_TEXT_PENDING_SUPPORT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),prior_closure_sha256=sha(closure),source_precheck=proof,source_recovery_reads=recovery,
               recursive_missing=missing,python310_syntax=True,expected_logical_calls=162,expected_physical_model_calls=165,total_physical_with_minimal=166,
               fixed_tokens=30,full_layers=36,logits=151936,KV_tensors=72,extra_DMA=0,parser_workers=1,PS_prefetch=False,SiLU_workspace=False,
               same_SHA_hardware_reused=True,production_policy_unchanged=True,PS_growth_limit_bytes=1024<<20,PS_available_margin_bytes=64<<20,
               known_KV_bytes=36*2*30*1024*4,gate_up_two_arrays_bytes=2*30*9728*4,full_logits_bytes=151936*4,exact_peak_proven=False,
               file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),board_run=False,numerical_pass=False,performance_pass=False)
    atomic(BASE/'runs/M401-tail-text-draft-01/RESULT.json',encoded(value),immutable=True)
    print(json.dumps(value))

if __name__=='__main__':main()
