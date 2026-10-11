"""Finish independent timing packet with reviewed producer bookkeeping."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once
OLD=BASE/'candidates/M430-late11-visual-warm-01'
PKG=BASE/'candidates/M430-late11-visual-warm-02'
def prepare():
    PKG.mkdir(parents=True,exist_ok=False)
    for p in OLD.iterdir():
        if p.name not in ('m430_gate.py','PLAN.json'):atomic(PKG/p.name,p.read_bytes(),immutable=True)
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan['component_package']='/home/ubuntu/m430_late11_visual_warm_candidate_02';atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    gate=(OLD/'m430_gate.py').read_text(encoding='utf-8')
    gate=once(gate,"bootstrap_prior['status']!='PASS_M430_ISOLATED_CPU_BOOTSTRAP_ONLY'", "bootstrap_prior['status']!='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY'")
    gate=once(gate,"        environment=read_environment();", "        result['overlay_loaded']=True;result['DMA_sealed_after_main']=True\n        environment=read_environment();")
    gate=once(gate,"            result['visual_forward_calls']+=1", "            result['visual_forward_calls']+=1\n            if variant=='A':result['original_visual_forward_calls']+=1")
    # Constructor/normal numerical changes are limited to timing bookkeeping.
    atomic(PKG/'m430_gate.py',gate.encode(),immutable=True)
    stage=ROOT/'tmp/m43001/component_stage';stage.mkdir(parents=True,exist_ok=False)
    for name in ('m430_timed_scope.py','m429_pl_range.py','m426_range02.py','m411_mlp_binding.py','test_m430_timing.py'):atomic(stage/name,(PKG/name).read_bytes(),immutable=True)
    entry="""import sys,json
from pathlib import Path
assert sys.flags.isolated
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
stage=root/'tmp/m43001/component_stage'
ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'
sys.path[:0]=[str(stage),str(ref)]
import torch
torch.set_num_threads(1)
from test_m430_timing import component
print('M430_COMPONENT='+json.dumps(component(root)),flush=True)
"""
    atomic(stage/'entry.py',entry.encode(),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    print('M430_FINAL_STAGE_PREPARED')
def component():
    folder=ROOT/'tmp/m43001/component'
    if folder.exists():raise RuntimeError('Original component logs exist')
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43001/component_stage/entry.py'],capture_output=True,timeout=180)
    atomic(folder/'stdout.bin',cp.stdout,immutable=True);atomic(folder/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Timed scope component rejected; inspect original bytes')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode().splitlines() if x.startswith('M430_COMPONENT=')];assert len(lines)==1
    c=json.loads(lines[0]);assert c['complete_wire_batches']==286 and c['restored'] and len(c['negative_checks'])==20 and len(c['timed_light_negative_checks'])==8
    r=dict(status='PASS_M430_ACTUAL_FROZEN_TIMED_SCOPE_FIXTURE_ONLY',component=c,stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),stage_sources={p.name:sha(p) for p in (ROOT/'tmp/m43001/component_stage').iterdir()},board_run=False,hardware_visual_numerics_from_M429=True,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M430-timed-scope-component-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m430_timed_scope_component',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),f'## M430 轻量计时scope实际组件（2026-10-06）\n\nSHA {sha(out)}；真实冻结包装/encoder/M207/PL binding，明确合成窄权重/Attention及fake PL，286完整输出与24边界一致，28项拒绝/恢复通过。新scope仅移除诊断边界转换和wire SHA，原算术/退出保持；不证明性能，无板端执行或测温。')
    print('M430_TIMED_COMPONENT_SYNC',sha(out))
def seal():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m430_timed_scope_component'];assert sha(ROOT/e['result'])==e['sha256']
    plan=json.loads((PKG/'PLAN.json').read_bytes());reused=[]
    for row in plan['reused_packages']:
        matches=[p.parent for p in (BASE/'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p)==row['manifest_sha256']];assert len(matches)==1
        for f in json.loads((matches[0]/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(matches[0]/f['path'])==f['sha256']
        reused+=matches
    modules={}
    for folder in [PKG]+reused:
        for p in folder.glob('*.py'):modules.setdefault(p.stem,p)
    source=json.loads((PKG/'SOURCE_IDENTITIES.json').read_bytes())
    for row in source['files']:
        candidates=[ROOT/row['path'],ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'/row['path']]
        matches=[p for p in candidates if p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']]
        if not matches:
            # Only dependencies actually imported below need a local AST copy.
            continue
        modules.setdefault(matches[0].stem,matches[0])
    seen=set();missing=[]
    def inspect(name):
        if name in seen:return
        seen.add(name);t=ast.parse(modules[name].read_text(encoding='utf-8-sig'))
        deps=[a.name.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names]+[(n.module or '').split('.')[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom)]
        for d in deps:
            if d in modules:inspect(d)
            elif len(d)>1 and d[0]=='m' and d[1].isdigit():missing.append((name,d))
    for name in ('m430_gate','m430_component_entry','m430_export'):inspect(name)
    if missing:raise RuntimeError('Recursive imports missing '+repr(missing))
    atomic(PKG/'DEPENDENCY_CLOSURE.json',encoded(dict(missing=missing,recursive_module_count=len(seen),sources={n:sha(modules[n]) for n in sorted(seen)})),immutable=True)
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode(),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    r=dict(status='M430_COMPLETE_VISUAL_WARM_PACKET_SUPPORT_PENDING',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],component_sha256=e['sha256'],recursive_modules=len(seen),missing=missing,draft_01_preserved='Unexecuted review corrected CPU prior receipt literal after version substitution, overlay-loaded marker and actual original visual call count. Math unchanged.',board_run=False,temperature_measurement_enabled=False,performance_pass=False)
    out=BASE/'runs/M430-packet-preparation-02/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m430_complete_visual_packet',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M430 完整视觉02计时包（2026-10-06）\n\nSHA {sha(out)}，manifest {r["manifest_sha256"]}，{m["file_count"]}文件/{m["total_bytes"]}B，递归{len(seen)}模块missing0。实际scope组件通过，01未执行稿保留，修正前级ID/分配标记/原视觉计数；固定4预热＋8正式，只视觉、不测温。待实际collector/export/control门禁，未上板或性能。')
    print('M430_PACKET_SYNC',sha(out),r['manifest_sha256'])
if __name__=='__main__':
    import sys
    {'prepare':prepare,'component':component,'seal':seal}[sys.argv[1]]()
