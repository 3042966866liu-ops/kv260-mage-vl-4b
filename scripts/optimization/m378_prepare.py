"""Freeze changed PS schedule layer only after actual family PASS is synchronized."""
import ast,base64,copy,hashlib,json,shutil,subprocess,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,encoded,atomic,sync
from m377_prepare import once
PKG=BASE/'candidates/M378-gate-up-layer-01'
OLD=BASE/'candidates/M377-gate-up-pair-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));r=board['latest_m377_gate_up_pair_board']
    assert r['status']=='PASS_M377_GATE_UP_PAIR_NUMERICAL' and sha(ROOT/r['result'])==r['sha256']
    assert all(r['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    prior=r['sha256'];oldmanifest=sha(OLD/'PACKAGE_MANIFEST.json')
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    PKG.mkdir(parents=True)
    excluded={'m377_assemble.py','m377_gate_up_pair.py','m377_gate_up_pair_gate.py','m377_export_result.py','run_m377_gate_up_pair.sh','SHA256SUMS'}
    for row in manifest['files']:
        if row['path'] not in excluded:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    assembly=(OLD/'m377_assemble.py').read_text(encoding='utf-8').replace('M377','M378').replace('/home/ubuntu/m365_staged_layer_candidate_02','/home/ubuntu/m377_gate_up_pair_candidate_01').replace('d74b5aa1efce14ae66e61632c583418e8485eb055e6c26631e8fd4f3cdda22db',oldmanifest)
    atomic(PKG/'m378_assemble.py',assembly.encode('utf-8'))
    source=(BASE/'candidates/M365-staged-layer-03/m365_staged_layer_gate.py').read_text(encoding='utf-8').replace('M365','M378').replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m378_gate_up_layer_01').replace('from m365_export_result import emit_saved','from m378_export_result import emit_saved')
    source=once(source,"        result['prior_board_sha256'] = PRIOR_SHA","        result['prior_board_sha256'] = PRIOR_SHA\n        family_path=Path('/home/ubuntu/m377_gate_up_pair_01/B1/load-memory.json')\n        family=json.loads(family_path.read_text(encoding='utf-8'))\n        if sha256(family_path)!='"+prior+"' or family['status']!='PASS_M377_GATE_UP_PAIR_NUMERICAL' or family['gate_return_code']!=0 or not family['safe_buffers_released']:raise RuntimeError('Actual family prerequisite differs')\n        result['family_pair_prerequisite_sha256']=sha256(family_path)")
    source=once(source,'        output,kv=one_layer(model,hidden.copy())',"        from m376_gate_up_workers import GateUpWorkers\n        parser_scope=GateUpWorkers(runtime,workers=2,enabled=True)\n        with parser_scope:\n            output,kv=one_layer(model,hidden.copy())\n        result['parser_scope']=parser_scope.report()\n        result['ps_prefetch_enabled']=False")
    source=source.replace('Original complete runtime objects retained; independent one-layer diagnostic, no extra CMA/PS slot or vision/LMhead/multi-layer; production policy unchanged','Original complete runtime and one layer retained; gate_up two parser workers only; no extra CMA/PS slot; production policy unchanged')
    atomic(PKG/'m378_staged_layer_gate.py',source.encode('utf-8'))
    exporter=(OLD/'m377_export_result.py').read_text(encoding='utf-8').replace('M377','M378').replace('/home/ubuntu/m377_gate_up_pair_01','/home/ubuntu/m378_gate_up_layer_01').replace('independent-gate-up-family-pair','independent-single-layer-capacity-diagnostic')
    atomic(PKG/'m378_export_result.py',exporter.encode('utf-8'))
    runner=(BASE/'candidates/M374-layer-future-wait-01/run_m374_staged_layer.sh').read_text(encoding='utf-8').replace('M374','M378').replace('m374','m378').replace('/home/ubuntu/m378_layer_future_wait_01','/home/ubuntu/m378_gate_up_layer_01')
    atomic(PKG/'run_m378_staged_layer.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((module,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m378-two-parser-single-layer-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    p=BASE/'runs/M378-gate-up-layer-preparation-01/RESULT.json';r=dict(status='PASS_OFFLINE_TWO_PARSER_LAYER_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),family_pair_prerequisite_sha256=prior,old_manifest_sha256=oldmanifest,recursive_import_missing=missing,python310_syntax=True,original_policy_reference_math_preserved=True,board_run=False,performance_pass=False)
    atomic(p,encoded(r),immutable=True);digest=sha(p);sync('latest_m378_gate_up_layer_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M378 双解析 worker 单层包准备（2026-10-03）\n\nM377真实family SHA {prior}已同步；只原layer0 gate_up启用2解析worker，五family/hidden/KV/重试完整原参考，原内存停止和释放保持。missing=0/3.10/作用域核对通过。准备 SHA {digest}；尚未上板，须控制及回收自测后执行。')
    print('M378_PREPARED',digest)
if __name__=='__main__':main()
