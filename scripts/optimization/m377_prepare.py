"""Freeze one family pair; unchanged loader, memory policy and hardware."""
import ast,json,shutil,subprocess,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,encoded,atomic,sync
OLD=BASE/'candidates/M365-staged-layer-03'
PKG=BASE/'candidates/M377-gate-up-pair-01'
PRIOR='e02968c97a786efcc489f78e8856bab3f0165edff620a0e583e466774c33b521'
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('Ambiguous source anchor: '+a)
    return s.replace(a,b)
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    recovery={}
    for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        t=(ROOT/n).read_text(encoding='utf-8-sig');recovery[n]=dict(sha256=sha(ROOT/n),chars=len(t))
    priors={}
    for k in ('latest_m365_stage_support','latest_m365_staged_layer_closure','latest_m376_gate_up_worker_board'):
        r=board[k];assert sha(ROOT/r['result'])==r['sha256']
        assert all(r['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));priors[k]=r['sha256']
    assert priors['latest_m376_gate_up_worker_board']==PRIOR
    cap=json.loads((ROOT/board['latest_m376_gate_up_worker_board']['result']).read_text(encoding='utf-8'))
    assert cap['status']=='PASS_GATE_UP_TWO_WORKER_CPU_COMPONENT_ONLY' and cap['gate_return_code']==0
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')==board['latest_m365_stage_support']['manifest_sha256']
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    excluded={'m365_assemble.py','m365_staged_layer_gate.py','m365_export_result.py','run_m365_staged_layer.sh','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in excluded:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    for n in ('m376_gate_up_workers.py','m377_gate_up_pair.py'):shutil.copyfile(HERE/n,PKG/n)
    assert sha(PKG/'m376_gate_up_workers.py')==sha(BASE/'candidates/M376-gate-up-worker-component-01/m376_gate_up_workers.py')
    shutil.copyfile(ROOT/board['latest_m376_gate_up_worker_board']['result'],PKG/'M376_CAPABILITY_RESULT.json')
    assembly=(BASE/'candidates/M374-layer-future-wait-01/m374_assemble.py').read_text(encoding='utf-8').replace('M374','M377')
    atomic(PKG/'m377_assemble.py',assembly.encode('utf-8'))
    s=(OLD/'m365_staged_layer_gate.py').read_text(encoding='utf-8').replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m377_gate_up_pair_01').replace('M365','M377').replace('from m365_export_result import emit_saved','from m377_export_result import emit_saved')
    s=s.replace('--enable-staged-layer','--enable-gate-up-pair').replace('args.enable_staged_layer','args.enable_gate_up_pair').replace('independent-single-layer-capacity-diagnostic','independent-gate-up-family-pair')
    s=once(s,"        result['prior_board_sha256'] = PRIOR_SHA", "        result['prior_board_sha256'] = PRIOR_SHA\n        cap_path=HERE/'M376_CAPABILITY_RESULT.json'\n        cap=json.loads(cap_path.read_text(encoding='utf-8'))\n        if sha256(cap_path)!='"+PRIOR+"' or cap['status']!='PASS_GATE_UP_TWO_WORKER_CPU_COMPONENT_ONLY' or cap['gate_return_code']!=0:raise RuntimeError('M376 CPU capability differs')\n        result['parser_capability_sha256']=sha256(cap_path)")
    start=s.index('        one_layer=bind(');end=s.index("        result['boot_unchanged']",start)
    s=s[:start]+'''        from m377_gate_up_pair import run_pair
        result['family_pair']=run_pair(runtime,policy,hidden)
        result['fpga_transactions']=1+len(result['transactions'])
        if runtime.logical_calls!=10 or runtime.host_calls!=len(result['transactions']):raise RuntimeError('Family pair transaction accounting differs')
        if any(t['layer']!=0 or t['family']!='gate_up' for t in result['transactions']):raise RuntimeError('Family scope escaped')
        result['model_forward_calls']=0
        result['worker_started']=True
        result['ps_prefetch_enabled']=False
        result['diagnostic_scope']='Layer0 gate_up pair on159 repeated frozen text embeddings; no model/vision/LMhead/video/performance'
        result['numerical_pass']=True
        result['gate_up_family_pair_pass']=True
        result['status']='PASS_M377_GATE_UP_PAIR_NUMERICAL'
        result['memory_capacity_proven']=False
'''+s[end:]
    s=s.replace('PASS_M377_SINGLE_LAYER_DIAGNOSTIC','PASS_M377_GATE_UP_PAIR_NUMERICAL')
    s=s.replace('Original complete runtime objects retained; independent one-layer diagnostic, no extra CMA/PS slot or vision/LMhead/multi-layer; production policy unchanged','Original complete runtime retained; layer0 gate_up original1 versus candidate2 parse workers; no extra CMA/PS slot/model forward; production policy unchanged')
    s=s.replace('Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically','Adjudicate pair and synchronize; then separately prepare single-layer numerical gate. No automatic full-model or performance run.')
    atomic(PKG/'m377_gate_up_pair_gate.py',s.encode('utf-8'))
    exporter=(BASE/'candidates/M374-layer-future-wait-01/m374_export_result.py').read_text(encoding='utf-8').replace('M374','M377').replace('/home/ubuntu/m374_layer_future_wait_01','/home/ubuntu/m377_gate_up_pair_01').replace('independent-single-layer-capacity-diagnostic','independent-gate-up-family-pair')
    atomic(PKG/'m377_export_result.py',exporter.encode('utf-8'))
    runner=(OLD/'run_m365_staged_layer.sh').read_text(encoding='utf-8').replace('M365','M377').replace('m365_export_result','m377_export_result').replace('m365_staged_layer_gate','m377_gate_up_pair_gate').replace('/home/ubuntu/m365_staged_layer_02','/home/ubuntu/m377_gate_up_pair_01').replace('--enable-staged-layer','--enable-gate-up-pair').replace('ENABLE_STAGED_LAYER','ENABLE_GATE_UP_PAIR')
    runner=once(runner,'task_python=/usr/local/share/pynq-venv/bin/python','task_python=/usr/local/share/pynq-venv/bin/python\nexport PYTHONDONTWRITEBYTECODE=1')
    atomic(PKG/'run_m377_gate_up_pair.sh',runner.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for name,tree in trees.items():
        for n in ast.walk(tree):
            names=[r.name.split('.')[0] for r in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((name,v) for v in names if v and v not in trees and v not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    hw=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'));assert hw['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for r in hw['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    frozen=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for r in closure['files']:assert sha(frozen/r['path'])==r['sha256']
    for n in ('m365_stage_policy.py','owned_buffer_release.py','LAYER_EXPECTED.json'):assert sha(PKG/n)==sha(OLD/n)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m377-gate-up-family-pair-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_GATE_UP_PAIR_PREPARATION',recovery_reads=recovery,prior_sha256=priors,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),recursive_import_missing=missing,python310_syntax=True,allocator_shapes_global=True,hardware_same_sha=True,original_policy_and_loader_preserved=True,extra_cma_bytes=0,numerical_pass=False,performance_pass=False,board_run=False)
    path=BASE/'runs/M377-gate-up-pair-preparation-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path)
    sync('latest_m377_gate_up_pair_preparation',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M377 gate_up 单/双解析 worker 数值包准备（2026-10-03）\n\n原完整loader/七DMA/内存停止/安全回收和同SHA硬件保持；只layer0 gate_up 159重复文本embedding，同输入原1与候选2解析线程完整输出/重试/计数比较。前级M376板端CPU通过。missing=0、3.10、SHAPES和硬件证据通过。准备SHA {digest}；manifest {r["manifest_sha256"]}。尚未上板，下一步控制/回收支持检查。')
    print('M377_PREPARED',digest,r['manifest_sha256'],len(rows))
if __name__=='__main__':main()
