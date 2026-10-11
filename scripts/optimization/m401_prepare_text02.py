"""Immutable same-level packaging repair; no board access or numerical changes."""
import ast
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync

OLD=BASE/'candidates/M401-tail-text-01'
PKG=BASE/'candidates/M401-tail-text-02'
SCOPE='sealed-DMA-fixed30-full36-layer-tail-prefill'
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def namespace(p):
    n={'__file__':str(p),'__name__':'offline_scope_check'}
    exec(compile(p.read_bytes(),str(p),'exec'),n)
    return n
def main():
    closure=BASE/'runs/M401-tail-text-failure-closure-01/RESULT.json'
    assert sha(closure)=='395514e8987bab4bb61136c9e9cc6faf35fbd901e33d9732fc52b64e854edff5'
    assert all(sha(closure) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    assert not (BASE/'runs/M401-tail-text-support-03/RESULT.json').exists(),'Completed support is immutable'
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='8f6e63c18bda343ce365bebab2cb48466d0268472062578527c7580c9d8d687e'
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    payload={r['path']:(OLD/r['path']).read_bytes() for r in manifest['files'] if r['path']!='SHA256SUMS'}
    assert all(sha(OLD/r['path'])==r['sha256'] for r in manifest['files'])
    gate=payload['m401_tail_text_gate.py'].decode('utf-8')
    fixed=once(gate,"HERE/'TAIL_TEXT_PREREQUISITE.json'","HERE/'TAIL_LAYER_PREREQUISITE.json'")
    fixed=once(fixed,"/home/ubuntu/m401_tail_text_01","/home/ubuntu/m401_tail_text_02")
    payload['m401_tail_text_gate.py']=fixed.encode('utf-8')
    assert fixed.replace('TAIL_LAYER_PREREQUISITE.json','TAIL_TEXT_PREREQUISITE.json').replace('m401_tail_text_02','m401_tail_text_01')==gate
    export=payload['m401_export_result.py'].decode('utf-8')
    export=once(export,'sealed-DMA-isolated-layer35-fullAttention-last31',SCOPE).replace('m401_tail_text_01','m401_tail_text_02')
    payload['m401_export_result.py']=export.encode('utf-8')
    payload['run_m401_tail_text.sh']=payload['run_m401_tail_text.sh'].replace(b'm401_tail_text_01',b'm401_tail_text_02')
    payload['m401_text_entry.py']=payload['m401_text_entry.py'].replace(b'm401_tail_text_gate_01',b'm401_tail_text_gate_02')
    assembly=payload['m401_assemble.py'].decode('utf-8').replace('/home/ubuntu/m400_tail_layer_candidate_02','/home/ubuntu/m401_tail_text_candidate_01').replace('79ad703a9e23761f922084243f15de1e582058e83db552b10a3bae7d36ca5fc7',sha(OLD/'PACKAGE_MANIFEST.json'))
    payload['m401_assemble.py']=assembly.encode('utf-8')
    # Check actual active code references, not a proposed filename list.
    references=[]
    for name in ('m401_text_entry.py','m401_tail_text_gate.py'):
        tree=ast.parse(payload[name].decode('utf-8'),feature_version=(3,10))
        for node in ast.walk(tree):
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div) and isinstance(node.left,ast.Name) and node.left.id=='HERE' and isinstance(node.right,ast.Constant) and isinstance(node.right.value,str):
                ref=node.right.value
                assert ref in payload or ref=='PACKAGE_MANIFEST.json',(name,ref)
                references.append([name,ref])
    assert SCOPE in fixed and SCOPE in export
    runner=payload['run_m401_tail_text.sh'].decode('utf-8')
    assert 'set -euo pipefail' in runner and 'M401_ENABLE_TAIL_TEXT:-0' in runner and '$EUID == 0' in runner
    assert 'm401_text_entry.py' in runner and '--enable-tail-text' in runner
    assert 'task_gate_rc=$?' in runner and 'exit "$task_gate_rc"' in runner
    for n,v in payload.items():
        if n.endswith('.py'):ast.parse(v.decode('utf-8'),feature_version=(3,10))
    PKG.mkdir(parents=True,exist_ok=True)
    for n,v in payload.items():atomic(PKG/n,v,immutable=True)
    rows=[dict(path=p.name,bytes=len(payload[p.name]),sha256=sha(p)) for p in sorted(PKG/n for n in payload)]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M401-fixed30-full-prefill-tail-v2',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    digest=sha(PKG/'PACKAGE_MANIFEST.json')
    # Native stdlib entry checks complete package/source before any hardware import.
    entry=namespace(PKG/'m401_text_entry.py');entry['SOURCE']=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    proof=entry['precheck'](digest)
    # Actual exporter with a temporary saved early-failure result; os/Path are explicit fakes.
    prior=json.loads((BASE/'runs/M401-tail-text-board-01/BOARD_RESULT.json').read_bytes())
    prior['manifest_sha256']=digest
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m401') as temp:
        temp=Path(temp);(temp/'B1').mkdir();atomic(temp/'B1/load-memory.json',encoded(prior))
        ex=namespace(PKG/'m401_export_result.py');ex['Path']=lambda _:temp;ex['os']=type('Root',(),{'geteuid':staticmethod(lambda:0)})();ex['time']=type('NoWait',(),{'sleep':staticmethod(lambda _:None)})()
        out=io.StringIO()
        with contextlib.redirect_stdout(out):ex['emit_saved']('B1')
        early_log=out.getvalue()
    # Versioned host files; original attempt01 code/package/logs untouched.
    collect=(HERE/'m401_collect.py').read_text(encoding='utf-8').replace('M401-tail-text-01','M401-tail-text-02')
    line="    if r['layer_prerequisite_sha256']!='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c' or r['layer_closure_sha256']!='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043':raise ValueError('Single layer prerequisite differs')\n"
    collect=once(collect,line,'')
    collect=once(collect,"    if r['status']=='PASS_M401_TAIL_TEXT_NUMERICAL':\n","    if r['status']=='PASS_M401_TAIL_TEXT_NUMERICAL':\n    "+line)
    atomic(HERE/'m401_collect02.py',collect.encode('utf-8'))
    workflow=(HERE/'m401_workflow.py').read_text(encoding='utf-8').replace("OLD=BASE/'candidates/M400-tail-layer-02'","OLD=BASE/'candidates/M401-tail-text-01'").replace("PKG=BASE/'candidates/M401-tail-text-01'","PKG=BASE/'candidates/M401-tail-text-02'").replace('tmp/m401/','tmp/m40102/').replace("'tmp/m401'","'tmp/m40102'").replace('M401-tail-text-transfer-01','M401-tail-text-transfer-02').replace('from m401_collect import','from m401_collect02 import').replace('精确M400-02','精确M401-01')
    atomic(HERE/'m401_workflow02.py',workflow.encode('utf-8'))
    controller=(HERE/'m401_control.ps1').read_text(encoding='utf-8').replace('M400-tail-layer-02/PACKAGE_MANIFEST.json','M401-tail-text-01/PACKAGE_MANIFEST.json').replace("$local='deployment/mage_vl4b/optimization_v1/candidates/M401-tail-text-01'","$local='deployment/mage_vl4b/optimization_v1/candidates/M401-tail-text-02'").replace('m401_tail_text_candidate_01','m401_tail_text_candidate_02').replace('tmp/m401/','tmp/m40102/').replace('m401_workflow.py','m401_workflow02.py').replace('M401-tail-text-board-01','M401-tail-text-board-02')
    atomic(HERE/'m401_control02.ps1',controller.encode('utf-8'))
    close=(HERE/'m401_close.py').read_text(encoding='utf-8').replace('from m401_collect import','from m401_collect02 import').replace('tmp/m401/','tmp/m40102/').replace('M401-tail-text-closure-01','M401-tail-text-closure-02')
    atomic(HERE/'m401_close02.py',close.encode('utf-8'))
    from m401_collect02 import decode
    assert decode(early_log)[2]==prior
    # Export rejects obsolete scope, strict recovery rejects a falsely promoted early failure.
    bad=dict(prior,gate_return_code=0,status='PASS_M401_TAIL_TEXT_NUMERICAL')
    from m400_support import export as envelope
    def emit(r):return envelope(r).replace('M400','M401')
    try:decode(emit(bad))
    except (ValueError,KeyError,AssertionError):pass
    else:raise AssertionError('Early failure accepted as PASS')
    # Reuse the existing explicit synthetic complete-result fixture construction;
    # exercise the repaired strict decoder, without rerunning model/scope tests.
    support=(HERE/'m401_support.py').read_text(encoding='utf-8')
    start=support.index('    original=json.loads(');end=support.index('    def emit(q):',start)
    import textwrap,copy
    fixtures={'BASE':BASE,'PKG':PKG,'PROOF':proof,'sha':sha,'json':json,'copy':copy}
    exec(compile(textwrap.dedent(support[start:end]),'<explicit-fake-result-fixture>','exec'),fixtures)
    assert decode(emit(fixtures['r']))[2]==fixtures['r']
    for n in ('m401_collect02.py','m401_workflow02.py','m401_close02.py'):
        ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    ps=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    selftest=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m401_control02.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert selftest.returncode==0,selftest.stdout+selftest.stderr
    names=json.loads(subprocess.check_output([str(ps),'-NoProfile','-File',str(HERE/'m401_control02.ps1'),'-Mode','List'],text=True,encoding='utf-8'))
    oldrows={r['path']:r for r in manifest['files']}
    assert names==['PACKAGE_MANIFEST.json']+[r['path'] for r in rows if oldrows.get(r['path'])!=r]
    # Actual frozen assembler against a temporary exact-source inventory.
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m401') as temp:
        temp=Path(temp);old=temp/'old';new=temp/'new';old.mkdir();new.mkdir()
        for p in OLD.iterdir():atomic(old/p.name,p.read_bytes())
        for n in names:atomic(new/n,(PKG/n).read_bytes())
        assembler=namespace(PKG/'m401_assemble.py');assembler['HERE']=new;assembler['OLD']=old;assembler['main'](digest)
        assert all(sha(new/r['path'])==r['sha256'] for r in rows)
    source_names=['m401_prepare_text02.py','m401_collect02.py','m401_workflow02.py','m401_control02.ps1','m401_close02.py','m401_prefill_source.py','m36603_collect.py']
    reused=json.loads((BASE/'runs/M401-tail-text-support-02/RESULT.json').read_bytes())
    value=dict(status='PASS_OFFLINE_M401_FIXED_TEXT_PACKAGE02',manifest_sha256=digest,prior_failure_closure_sha256=sha(closure),original_attempt_unchanged=True,source_precheck=proof,active_HERE_references=references,scope_and_export_consistent=True,actual_early_failure_export_and_decode=True,early_failure_fake_PASS_rejected=True,actual_assembly_PASS=True,actual_control_delta=names,controller_selftest=selftest.stdout.strip(),
        source_sha256={n:sha(HERE/n) for n in source_names},prior_support_sha256=sha(BASE/'runs/M401-tail-text-support-02/RESULT.json'),reused_full36_tests=5,reused_collector_negatives=13,reused_head_tests=14,same_SHA_hardware_checks=47,
        mathematical_region_unchanged=True,lifecycle_unchanged=True,python310_syntax_only=True,board_run=False,numerical_pass=False,performance_pass=False)
    for k in ('preparation','support'):
        p=BASE/f'runs/M401-tail-text-{k}-03/RESULT.json';atomic(p,encoded(value|{'record_kind':k}),immutable=True)
        sync('latest_m401_tail_text_'+k,dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=digest),f'## M401 固定文本02同级修复与实际包检查（2026-10-04）\n\n{sha(p)}，manifest `{digest}`。原01失败已闭合，0资源；新02仅修前置文件名/导出范围和独立路径，完整数学/关闭保持。实际HERE引用、导出早期失败/严格decode、assembly、控制差分与SelfTest、源码前置通过，原5组件/13负例/14head/47同SHA硬件复用。尚未上传/数值PASS；下一步只本固定30文本一次，无视频/性能。')
    print(json.dumps(value))

if __name__=='__main__':main()
