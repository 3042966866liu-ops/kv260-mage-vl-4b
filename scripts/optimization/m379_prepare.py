"""Fixed30 text gate, exact existing model/head and memory policy, gate_up width2."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M366-staged-text-03'
PKG=BASE/'candidates/M379-gate-up-text-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m378_gate_up_layer_board']
    assert prior['status']=='PASS_M378_SINGLE_LAYER_DIAGNOSTIC' and sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    # Pin the previously verified fixed-text package from authoritative result.
    oldraw=json.loads((BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'));assert oldraw['manifest_sha256']==sha(OLD/'PACKAGE_MANIFEST.json') and oldraw['status']=='PASS_M366_FIXED_TEXT_DIAGNOSTIC'
    PKG.mkdir(parents=True)
    skip={'m366_assemble.py','m366_staged_text_gate.py','m366_export_result.py','run_m366_staged_text.sh','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    shutil.copyfile(BASE/'candidates/M376-gate-up-worker-component-01/m376_gate_up_workers.py',PKG/'m376_gate_up_workers.py')
    assembly=(BASE/'candidates/M378-gate-up-layer-01/m378_assemble.py').read_text(encoding='utf-8').replace('M378','M379').replace('/home/ubuntu/m377_gate_up_pair_candidate_01','/home/ubuntu/m366_staged_text_candidate_03').replace('c211d99d3b279555a9e93d5f26a7a5aa6179062a1ab1aad801fae3862fd61c9f',sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m379_assemble.py',assembly.encode('utf-8'))
    s=(OLD/'m366_staged_text_gate.py').read_text(encoding='utf-8').replace('M366','M379').replace('/home/ubuntu/m366_staged_text_02','/home/ubuntu/m379_gate_up_text_01').replace('from m366_export_result import emit_saved','from m379_export_result import emit_saved')
    s=once(s,"        result['prior_board_sha256'] = PRIOR_SHA","        result['prior_board_sha256'] = PRIOR_SHA\n        layer_path=Path('/home/ubuntu/m378_gate_up_layer_01/B1/load-memory.json')\n        layer=json.loads(layer_path.read_text(encoding='utf-8'))\n        if sha256(layer_path)!='"+prior['sha256']+"' or layer['status']!='PASS_M378_SINGLE_LAYER_DIAGNOSTIC' or layer['gate_return_code']!=0 or not layer['safe_buffers_released']:raise RuntimeError('Changed parser layer prerequisite differs')\n        result['two_parser_layer_sha256']=sha256(layer_path)")
    s=once(s,'        token,logits,kv=model.prefill(hidden.copy())',"        from m376_gate_up_workers import GateUpWorkers\n        parser_scope=GateUpWorkers(runtime,workers=2,enabled=True)\n        with parser_scope:\n            token,logits,kv=model.prefill(hidden.copy())\n        result['parser_scope']=parser_scope.report()\n        result['ps_prefetch_enabled']=False")
    atomic(PKG/'m379_staged_text_gate.py',s.encode('utf-8'))
    export=(OLD/'m366_export_result.py').read_text(encoding='utf-8').replace('M366','M379').replace('/home/ubuntu/m366_staged_text_02','/home/ubuntu/m379_gate_up_text_01')
    if 'import time' not in export:export=once(export,'import sys','import sys\nimport time')
    oldline="    for i,p in enumerate(chunks):print(f'M379_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)"
    if oldline in export:export=once(export,oldline,"    for i,p in enumerate(chunks):\n        print(f'M379_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)\n        time.sleep(.04)")
    atomic(PKG/'m379_export_result.py',export.encode('utf-8'))
    runner=(OLD/'run_m366_staged_text.sh').read_text(encoding='utf-8').replace('M366','M379').replace('m366_export_result','m379_export_result').replace('m366_staged_text_gate','m379_staged_text_gate').replace('/home/ubuntu/m366_staged_text_02','/home/ubuntu/m379_gate_up_text_01')
    if 'export PYTHONDONTWRITEBYTECODE=1' not in runner:runner=once(runner,'task_python=/usr/local/share/pynq-venv/bin/python','task_python=/usr/local/share/pynq-venv/bin/python\nexport PYTHONDONTWRITEBYTECODE=1')
    atomic(PKG/'run_m379_staged_text.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[r.name.split('.')[0] for r in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for n in ('m366_stage_policy.py','m366_head_observer.py','LAYER_EXPECTED.json','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json','owned_buffer_release.py'):assert sha(PKG/n)==sha(OLD/n)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m379-two-parser-fixed-text-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_TWO_PARSER_FIXED_TEXT_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),two_parser_layer_sha256=prior['sha256'],original_text_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),recursive_import_missing=missing,python310_syntax=True,allocator_shapes_global=True,original30token_math_head_reference_policy_same_sha=True,extra_cma_bytes=0,board_run=False,numerical_pass=False,performance_pass=False)
    path=BASE/'runs/M379-gate-up-text-preparation-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path);sync('latest_m379_gate_up_text_preparation',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M379 gate_up 双解析线程固定文本准备（2026-10-03）\n\n前级新单层 SHA {prior["sha256"]}已同步；原30Token/36层/完整LMhead/151936logits与72KV参考、内存policy/物理head观察保持同SHA，仅36次gate_up使用2解析worker。依赖missing=0/3.10/作用域通过，0新增DMA。准备 SHA {digest}；尚未上板。')
    print('M379_PREPARED',digest,len(rows))
if __name__=='__main__':main()
