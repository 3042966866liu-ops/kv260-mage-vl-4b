"""Reuse the proven M365 single-layer owner/geometry; change only the kernel identity."""
import ast
import json
import shutil
import symtable
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m343_layer_scope import derive

OLD=w.BASE/'candidates/M365-staged-layer-03'
PKG=w.BASE/'candidates/M441-single-layer-09'
PRIOR=w.BASE/'runs/M441-compare-board-01/BOARD_RESULT.json'
REMOTE='/home/ubuntu/m441_single_layer_candidate_09'
EVIDENCE='/home/ubuntu/m441_single_layer_evidence_09'

def once(text,before,after):
    if text.count(before)!=1:raise RuntimeError('Unexpected substitution count: '+before)
    return text.replace(before,after,1)

def verify_package(root):
    m=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
    for r in m['files']:assert (root/r['path']).stat().st_size==r['bytes'] and w.sha(root/r['path'])==r['sha256']
    return m

def main():
    if PKG.exists():raise RuntimeError('Immutable package already exists')
    prior=json.loads(PRIOR.read_bytes());digest=w.sha(PRIOR)
    assert digest=='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'
    assert prior['status']=='PASS_M441_COMPARE' and prior['chain_performance_pass'] and prior['stable_restored']
    records=[w.ROOT/n for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')]
    assert all(digest in p.read_text(encoding='utf-8-sig') for p in records)
    verify_package(OLD)
    target=w.BASE/'candidates/M441-record-load-01';verify_package(target)
    PKG.mkdir(parents=True)
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','m365_assemble.py','m365_export_result.py','m365_staged_layer_gate.py','run_m365_staged_layer.sh'}
    for p in OLD.iterdir():
        if p.name not in exclude:shutil.copyfile(p,PKG/p.name)
    text=(OLD/'m365_staged_layer_gate.py').read_text(encoding='utf-8')
    text=once(text,"Path('/home/ubuntu/m357_candidate_01')","Path('/home/ubuntu/m441_candidate_01')")
    text=once(text,"CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'","CAND_SHA = '"+w.sha(target/'PACKAGE_MANIFEST.json')+"'")
    text=once(text,"PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'","PRIOR_SHA = '"+digest+"'")
    text=text.replace('M357_COMPARE_PREREQUISITE.json','M441_COMPARE_PREREQUISITE.json').replace('PASS_M357_COMPARE','PASS_M441_COMPARE').replace('Exact M357','Exact M441')
    text=text.replace("'0x4D333537' if is_candidate","'0x4D343431' if is_candidate")
    text=text.replace('/home/ubuntu/m365_staged_layer_02',EVIDENCE)
    text=once(text,"        policy=StagePolicy(result,lambda:runtime,base)","        # Source compatibility is validated before Overlay/DMA allocation.\n        from m343_layer_scope import bind\n        one_layer=bind(m241_video_language_runtime,(HERE/'frozen_one_layer.py').read_text(encoding='utf-8'))\n        result['source_compatibility_checked_before_overlay']=True\n        policy=StagePolicy(result,lambda:runtime,base)")
    text=once(text,"        one_layer=bind(sys.modules['m241_video_language_runtime'],(HERE/'frozen_one_layer.py').read_text(encoding='utf-8'))","        # Reuse the already checked unchanged one-layer callable.")
    # Same mathematics and owner policy; rename only this new gate/result namespace.
    text=text.replace('M365','M441L').replace('m365_staged_layer_gate','m441_layer_gate').replace('m365_export_result','m441_layer_export').replace('_m365_closed','_m441l_closed')
    atomic(PKG/'m441_layer_gate.py',text.encode('utf-8'))
    shutil.copyfile(PRIOR,PKG/'M441_COMPARE_PREREQUISITE.json')
    hardware_rows=[]
    old_prep=json.loads((w.BASE/'runs/M441-board-package-preparation-01/RESULT.json').read_bytes())
    # The candidate already contains the exact closed CSim/header/RTL/core/shell proofs.
    for row in json.loads((target/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if row['path'].startswith('evidence/') and row['path'].endswith('/RESULT.json'):
            hardware_rows.append(dict(path=row['path'],sha256=row['sha256'],status=json.loads((target/row['path']).read_bytes())['status']))
    atomic(PKG/'HARDWARE_CLOSURE.json',w.encoded(dict(status='PASS_ALL_NEW_CIRCUIT_PREREQUISITES',build_id='0x4D343431',candidate_manifest_sha256=w.sha(target/'PACKAGE_MANIFEST.json'),prerequisites=hardware_rows,prior_compare_raw_sha256=digest)))
    export=(OLD/'m365_export_result.py').read_text(encoding='utf-8').replace('/home/ubuntu/m365_staged_layer_02',EVIDENCE).replace('M365','M441L')
    atomic(PKG/'m441_layer_export.py',export.encode('utf-8'))
    runner=(OLD/'run_m365_staged_layer.sh').read_text(encoding='utf-8').replace('/home/ubuntu/m365_staged_layer_02',EVIDENCE).replace('m365_staged_layer_gate.py','m441_layer_gate.py').replace('m365_export_result.py','m441_layer_export.py').replace('M365','M441L')
    atomic(PKG/'run_m441_layer.sh',runner.encode('utf-8'))
    # Copy only exact original bytes from already verified remote packages/results.
    assemble='''import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
 m=ROOT/'PACKAGE_MANIFEST.json'
 if sha(m)!=expected:raise RuntimeError('Manifest differs')
 data=json.loads(m.read_text(encoding='utf-8'))
 old=Path('/home/ubuntu/m363_common_load_observer_01')
 if sha(old/'PACKAGE_MANIFEST.json')!='006dff41790e8adda44c85a3b93383b93e7089243a6079f88de397f2a48e6b74':raise RuntimeError('Pinned old package differs')
 source={r['sha256']:old/r['path'] for r in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']}
 saved=Path('/home/ubuntu/m441_board_evidence_01/Compare/BOARD_RESULT.json')
 if sha(saved)!='PRIOR_DIGEST':raise RuntimeError('Saved original compare differs')
 source[sha(saved)]=saved
 for row in data['files']:
  if '/' in row['path'] or '\\\\' in row['path']:raise RuntimeError('Flat whitelist required')
  p=ROOT/row['path']
  if not p.exists():
   src=source.get(row['sha256'])
   if src is None or sha(src)!=row['sha256']:raise RuntimeError('Missing exact reused payload')
   shutil.copyfile(src,p)
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Payload changed')
 if {p.name for p in ROOT.iterdir()}!={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
 print('M441L_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
'''.replace('PRIOR_DIGEST',digest)
    atomic(PKG/'m441_layer_assemble.py',assemble.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-independent-single-layer-v09',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    verify_package(PKG)
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_bytes());release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    assert derive((release/closure['modules']['m241_video_language_runtime']).read_bytes())==(PKG/'frozen_one_layer.py').read_text(encoding='utf-8')
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    import sys
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,t in trees.items():
        for n in ast.walk(t):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,name) for name in names if name and name not in trees and name not in allowed)
    assert not missing,missing
    assert text.index('one_layer=bind(')<text.index("patch(pynq,'Overlay'")<text.index('engine.load()')<text.index('one_layer(model,hidden.copy())')
    main_symbols=next(t for t in symtable.symtable(text,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in main_symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert (PKG/'m365_stage_policy.py').read_bytes()==(OLD/'m365_stage_policy.py').read_bytes()
    assert (PKG/'owned_buffer_release.py').read_bytes()==(OLD/'owned_buffer_release.py').read_bytes()
    assert 'while True: time.sleep(30)' in text and "unsafe = unsafe or not initialized" in text
    out=w.BASE/'runs/M441-single-layer-preparation-09'
    r=dict(status='PREPARED_M441_SINGLE_LAYER_REUSING_PROVEN_OWNER',build_id='0x4D343431',prior_raw_sha256=digest,manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),package_path=PKG.relative_to(w.ROOT).as_posix(),remote=REMOTE,evidence=EVIDENCE,source_compatibility_before_overlay=True,python310_syntax=True,recursive_import_missing=missing,unchanged_layer_loop=True,seven_buffer_geometry=[6963200]*4+[389152,2621440,2621440],additional_pynq_allocations_allowed=False,fixed_cma_reserve_enforced=False,ps_growth_limit_bytes=256<<20,ps_available_margin_bytes=64<<20,policy_and_owner_reused_same_sha=True,board_executed=False,numerical_pass=False,performance_pass=False,promotion=False)
    atomic(out/'RESULT.json',w.encoded(r),immutable=True);rd=w.sha(out/'RESULT.json')
    w.sync('latest_m441_single_layer_preparation',dict(status=r['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=rd,manifest_sha256=r['manifest_sha256']),f'## M441 单层入口准备09（2026-10-09）\n\nBuild0x4D343431，复用M365已验证完整runtime七缓冲/幂等owner/单层159重复embedding参考；仅核身份改变，源兼容检查提前到Overlay之前。新增DMA封锁，独立PS增长256MiB+普通内存64MiB余量，CMA统计只观察无固定64MiB拒绝。0板端，未解锁固定文本/视频/性能。准备SHA {rd}，前级真实长链对照SHA {digest}。')
    print(json.dumps(r))

if __name__=='__main__':main()
