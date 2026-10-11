"""Prepare immutable same-level retry after authentic owner recovery; no board access."""
import ast
import json
import shutil
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_tail_source_02 import validate

OLD=BASE/'candidates/M400-tail-layer-01'
PKG=BASE/'candidates/M400-tail-layer-02'
OLD_SHA='2a04363254f7d0fe49e49551e41d50609270fa67328650f701b44b001d0de2fa'
FROZEN_SHA='fc5543e48aecc49dad0c08eb5efefa82a12ed607088b30cbba1a9b792d06f40b'


def replace_once(text,old,new):
    if text.count(old)!=1:raise RuntimeError('Versioned source anchor differs: '+old)
    return text.replace(old,new)


def main():
    if PKG.exists():raise RuntimeError('Immutable package already exists')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;text=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),bytes=p.stat().st_size,lines=len(text.splitlines()))
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    restored=BASE/'runs/M400-controlled-owner-restore-board-02/BOARD_RESULT.json'
    assert sha(restored)=='6288c7b041831ae3f4b1e29c7bb29cded9b34e1c40cb5c7c7bf102a83b1f1a1d'
    r=json.loads(restored.read_text(encoding='utf-8'))
    assert r['status']=='PASS_CONTROLLED_OWNER_EXIT_AND_STABLE_RESTORE'
    assert all(sha(restored) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')==OLD_SHA
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert all(sha(OLD/f['path'])==f['sha256'] and (OLD/f['path']).stat().st_size==f['bytes'] for f in m['files'])
    source=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    frozen=BASE/'runs/M400-source-compatibility-preparation-02/frozen_last_layer.py'
    proof=validate(source.read_bytes(),frozen.read_bytes(),FROZEN_SHA)
    payload={f['path']:(OLD/f['path']).read_bytes() for f in m['files'] if f['path']!='SHA256SUMS'}
    scope=payload['m400_tail_layer_scope.py'].decode('utf-8')
    start=scope.index('def derive(source):');end=scope.index('class TailLayerScope',start)
    scope=scope[:start]+'from m400_tail_source_02 import derive\n\n\n'+scope[end:]
    payload['m400_tail_layer_scope.py']=scope.encode('utf-8')
    payload['m400_tail_source_02.py']=(HERE/'m400_tail_source_02.py').read_bytes()
    payload['m400_layer_entry_02.py']=(HERE/'m400_layer_entry_02.py').read_bytes()
    payload['frozen_last_layer.py']=frozen.read_bytes()
    gate=payload['m400_tail_layer_gate.py'].decode('utf-8').replace('/home/ubuntu/m400_tail_layer_01','/home/ubuntu/m400_tail_layer_02')
    gate=replace_once(gate,"    EVIDENCE=Path('/home/ubuntu/m400_tail_layer_02')/args.case", "    if not globals().get('SOURCE_PRECHECK_PROOF'):raise RuntimeError('Stdlib pre-entry source proof required before resource setup')\n    EVIDENCE=Path('/home/ubuntu/m400_tail_layer_02')/args.case")
    gate=replace_once(gate,"    runtime = engine = base = lock = policy = None", "    result['source_precheck_before_hardware_import']=dict(SOURCE_PRECHECK_PROOF)\n    runtime = engine = base = lock = policy = None")
    payload['m400_tail_layer_gate.py']=gate.encode('utf-8')
    runner=payload['run_m400_tail_layer.sh'].decode('utf-8').replace('/home/ubuntu/m400_tail_layer_01','/home/ubuntu/m400_tail_layer_02')
    runner=replace_once(runner,'"$task_dir/m400_tail_layer_gate.py"','"$task_dir/m400_layer_entry_02.py"')
    payload['run_m400_tail_layer.sh']=runner.encode('utf-8')
    payload['m400_export_result.py']=payload['m400_export_result.py'].replace(b'/home/ubuntu/m400_tail_layer_01',b'/home/ubuntu/m400_tail_layer_02')
    assembly=payload['m400_assemble.py'].decode('utf-8').replace('/home/ubuntu/m399_tail_chain_candidate_01','/home/ubuntu/m400_tail_layer_candidate_01').replace('e762fa83ff45ad2b50266370e42de43ab27b30517efaa306ef1c0f04cae8c5df',OLD_SHA)
    payload['m400_assemble.py']=assembly.encode('utf-8')
    trees={n[:-3]:ast.parse(raw.decode('utf-8'),feature_version=(3,10)) for n,raw in payload.items() if n.endswith('.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads(payload['SOURCE_CLOSURE.json'])['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for name,tree in trees.items():
        for n in ast.walk(tree):
            imports=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((name,x) for x in imports if x and x not in trees and x not in allowed)
    assert not missing,missing
    # Preserve every original scope method and numerical execution region.
    oldclass=next(n for n in ast.parse((OLD/'m400_tail_layer_scope.py').read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef))
    newclass=next(n for n in trees['m400_tail_layer_scope'].body if isinstance(n,ast.ClassDef))
    assert ast.dump(oldclass)==ast.dump(newclass)
    oldgate=(OLD/'m400_tail_layer_gate.py').read_text(encoding='utf-8')
    a=oldgate.index('        model=engine.language');z=oldgate.index('    except RetainedChainOwnerError',a)
    assert oldgate[a:z]==gate[gate.index('        model=engine.language'):gate.index('    except RetainedChainOwnerError')]
    for f in json.loads(payload['HARDWARE_CLOSURE.json'])['prerequisites']:assert sha(ROOT/f['path'])==f['sha256']
    PKG.mkdir(parents=True)
    for n,raw in payload.items():atomic(PKG/n,raw)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(f['sha256']+'  '+f['path']+'\n' for f in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M400-isolated-last-layer-tail-sourceguard-v2',files=rows,file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows))))
    controller=(HERE/'m400_control.ps1').read_text(encoding='utf-8-sig')
    controller=controller.replace('M400-tail-layer-01','M400-tail-layer-02').replace('M399-tail-chain-01','M400-tail-layer-01').replace('m400_tail_layer_candidate_01','m400_tail_layer_candidate_02').replace('tmp/m400/','tmp/m40002/').replace('m400_workflow.py','m400_workflow02.py')
    for key in ('preparation','support','transfer'):controller=controller.replace('latest_m400_tail_layer_'+key,'latest_m400_tail_layer_'+key+'02')
    controller=controller.replace('M400-tail-layer-board-01','M400-tail-layer-board-02')
    atomic(HERE/'m400_control02.ps1',controller.encode('utf-8'))
    workflow=(HERE/'m400_workflow.py').read_text(encoding='utf-8')
    workflow=workflow.replace('M400-tail-layer-01','M400-tail-layer-02').replace('M399-tail-chain-01','M400-tail-layer-01').replace('tmp/m400','tmp/m40002').replace('M400-tail-layer-transfer-01','M400-tail-layer-transfer-02').replace('latest_m400_tail_layer_transfer','latest_m400_tail_layer_transfer02').replace('from m400_collect import','from m400_collect02 import').replace('精确M399','精确M400-01')
    atomic(HERE/'m400_workflow02.py',workflow.encode('utf-8'))
    collector=(HERE/'m400_collect.py').read_text(encoding='utf-8')
    collector=collector.replace('M400-tail-layer-01','M400-tail-layer-02').replace('M400-tail-layer-board-01','M400-tail-layer-board-02').replace('latest_m400_tail_layer_board','latest_m400_tail_layer_board02')
    anchor="    if r['status']=='PASS_M400_TAIL_LAYER_NUMERICAL':"
    collector=replace_once(collector,anchor,"    if r.get('source_precheck_before_hardware_import')!="+repr(proof)+":raise ValueError('Pre-resource source proof differs')\n"+anchor)
    atomic(HERE/'m400_collect02.py',collector.encode('utf-8'))
    closure=(HERE/'m400_close_layer.py').read_text(encoding='utf-8').replace('from m400_collect import','from m400_collect02 import').replace('tmp/m400/','tmp/m40002/').replace('M400-tail-layer-closure-01','M400-tail-layer-closure-02').replace("sha(HERE/'m400_close_layer.py')","sha(HERE/'m400_close_layer02.py')")
    for key in ('board','transfer','support','closure'):closure=closure.replace('latest_m400_tail_layer_'+key,'latest_m400_tail_layer_'+key+'02')
    atomic(HERE/'m400_close_layer02.py',closure.encode('utf-8'))
    value=dict(status='PASS_OFFLINE_LAST_LAYER_SOURCE_GUARD_PACKAGE02',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),original_package_sha256=OLD_SHA,source_precheck=proof,
               owner_restored_sha256=sha(restored),file_count=len(rows),total_bytes=sum(f['bytes'] for f in rows),recursive_missing=missing,
               scope_class_AST_unchanged=True,numerical_region_exact_unchanged=True,hardware_same_SHA_reused=True,python310_syntax=True,recovery_read=recovery,
               expected_logical_calls=8,expected_physical_layer_calls=8,total_physical_with_minimal=9,extra_DMA=0,board_run=False,numerical_pass=False,performance_pass=False)
    out=BASE/'runs/M400-tail-layer-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m400_tail_layer_preparation02',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),
         f'## M400 同级单层修复包02准备（2026-10-04）\n\nSHA `{h}`，manifest `{value["manifest_sha256"]}`。原owner受控退出/稳定恢复已闭合。stdlib完整包SHA/原M241 SHA/确定性提取及同解释器AST检查先于硬件gate导入、Overlay和DMA；原scope全部方法AST、数值执行region逐字保持，同SHA硬件47项复用，missing0/3.10语法。新不可变02包，原01失败不改；8逻辑/8层物理加minimal9，新增DMA0，生产政策保持。仍只准备，未上传或数值PASS，后级未解锁。')
    print(json.dumps(value|{'result_sha256':h}))


if __name__=='__main__':main()
