"""Preserve the failed packet; add its indirect dependency in independent staging."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m417_reference_board','latest_m417_reference_closure'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    failure=json.loads((ROOT/board['latest_m417_reference_board']['result']).read_bytes())
    assert failure['gate_return_code']==1 and "No module named 'm408_target03'" in failure['errors'][0]['message']
    assert all(failure[k]==0 for k in ('dma_allocations','fpga_transactions','visual_forward_calls','language_forward_calls','local_mlp_forward_calls'))
    old=BASE/'candidates/M417-layer13-saved-reference-01';pkg=BASE/'candidates/M417-layer13-saved-reference-02'
    if pkg.exists():raise RuntimeError('New immutable package already exists')
    oldm=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes());oldrows={x['path']:x for x in oldm['files']}
    pkg.mkdir()
    for row in oldm['files']:
        assert sha(old/row['path'])==row['sha256']
        if row['path']!='SHA256SUMS':atomic(pkg/row['path'],(old/row['path']).read_bytes(),immutable=True)
    dependency=BASE/'candidates/M409-saved-MLP-reference-01/m408_target03.py'
    proof=json.loads((dependency.parent/'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(dependency)==next(x['sha256'] for x in proof['files'] if x['path']==dependency.name)
    atomic(pkg/dependency.name,dependency.read_bytes(),immutable=True)
    for name in ('m417_gate.py','run_m417_reference.sh'):
        original=(old/name).read_text(encoding='utf-8')
        changed=original.replace('m417_layer13_reference_01','m417_layer13_reference_02')
        assert changed!=original
        # These two are newly staged files, before their new manifest is frozen.
        atomic(pkg/name,changed.encode('utf-8'))
    assembler='''"""Hash-bound copies from one exact previously verified packet; no model imports."""
import hashlib,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')
OLD_SHA=OLD_DIGEST
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if os.geteuid()!=0:raise RuntimeError('Root assembly required')
if len(sys.argv)!=2 or sha(HERE/'PACKAGE_MANIFEST.json')!=sys.argv[1]:raise RuntimeError('Target manifest differs')
if sha(OLD/'PACKAGE_MANIFEST.json')!=OLD_SHA:raise RuntimeError('Old manifest differs')
old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes());oldrows={r['path']:r for r in old['files']}
new=json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes())
for r in old['files']:
    p=OLD/r['path']
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Old packet drift')
for r in new['files']:
    name=r['path']
    if Path(name).name!=name:raise RuntimeError('Plain whitelist filename required')
    p=HERE/name
    if not p.exists():
        if name not in oldrows or oldrows[name]!=r:raise RuntimeError('Missing delta payload')
        part=p.with_suffix(p.suffix+'.assembly-part')
        with part.open('xb') as f:f.write((OLD/name).read_bytes());f.flush();os.fsync(f.fileno())
        os.replace(part,p)
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Target packet drift')
    print('M417_ASSEMBLED_FILE '+name+' '+r['sha256'],flush=True)
allowed={'PACKAGE_MANIFEST.json'}|{r['path'] for r in new['files']}
if {p.name for p in HERE.iterdir()}!=allowed:raise RuntimeError('Unexpected staging files')
print('M417_ASSEMBLY_PASS '+sys.argv[1]+' '+str(new['file_count'])+' '+str(new['total_bytes']),flush=True)
'''.replace('OLD_DIGEST',repr(sha(old/'PACKAGE_MANIFEST.json')))
    atomic(pkg/'assemble_m417.py',assembler.encode('utf-8'),immutable=True)
    delta=['m408_target03.py','m417_gate.py','run_m417_reference.sh','assemble_m417.py','TRANSFER_FILES.json','SHA256SUMS']
    atomic(pkg/'TRANSFER_FILES.json',encoded(dict(files=delta,old_manifest_sha256=sha(old/'PACKAGE_MANIFEST.json'))),immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    # Actual entry closure includes the indirect import that the host previously masked.
    local={p.stem for p in pkg.glob('*.py')};missing=set()
    old_local={p.stem for p in (BASE/'candidates/M409-saved-MLP-reference-01').glob('*.py')}
    for p in pkg.glob('*.py'):
        tree=ast.parse(p.read_bytes(),feature_version=(3,10))
        for node in ast.walk(tree):
            names=[node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [v.name.split('.')[0] for v in node.names] if isinstance(node,ast.Import) else []
            missing.update(n for n in names if n in old_local and n not in local)
    assert not missing,missing
    workflow=(HERE/'m417_workflow.py').read_text(encoding='utf-8').replace('M417-layer13-saved-reference-01','M417-layer13-saved-reference-02').replace('tmp/m41701','tmp/m41702').replace('M417-layer13-reference-transfer-01','M417-layer13-reference-transfer-02').replace('M417-layer13-reference-board-01','M417-layer13-reference-board-02').replace('latest_m417_reference_transfer','latest_m417_reference_transfer02').replace('latest_m417_reference_board','latest_m417_reference_board02')
    workflow=workflow.replace("    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:","    transfer_names=json.loads((PKG/'TRANSFER_FILES.json').read_bytes())['files']\n    for name in ['PACKAGE_MANIFEST.json']+transfer_names:")
    anchor="    syntax = folder/'syntax.log'"
    if anchor not in workflow:anchor="    syntax=folder/'syntax.log'"
    assembly="""    assembly=folder/'assembly.log';assembly_text=assembly.read_text(encoding='utf-8-sig')
    if f'M417_ASSEMBLY_PASS {sha(PKG/"PACKAGE_MANIFEST.json")} {manifest["file_count"]} {manifest["total_bytes"]}' not in assembly_text:raise RuntimeError('Assembly manifest/count missing')
    for row in manifest['files']:
        if f'M417_ASSEMBLED_FILE {row["path"]} {row["sha256"]}' not in assembly_text:raise RuntimeError('Complete assembled identity missing')
"""
    assert workflow.count(anchor)==1;workflow=workflow.replace(anchor,assembly+anchor)
    atomic(HERE/'m417_workflow02.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m417_control.ps1').read_text(encoding='utf-8').replace('M417-layer13-saved-reference-01','M417-layer13-saved-reference-02').replace('m417_layer13_reference_candidate_01','m417_layer13_reference_candidate_02').replace('tmp/m41701','tmp/m41702').replace('M417-layer13-reference-board-01','M417-layer13-reference-board-02').replace('m417_workflow.py','m417_workflow02.py').replace('latest_m417_reference_preparation','latest_m417_reference_preparation02').replace('latest_m417_reference_support','latest_m417_reference_support02').replace('latest_m417_reference_transfer','latest_m417_reference_transfer02')
    control=control.replace("'latest_m416_local_mlp_closure','latest_m417_reference_preparation02'","'latest_m416_local_mlp_closure','latest_m417_reference_board','latest_m417_reference_closure','latest_m417_reference_preparation02'")
    control=control.replace("@($manifest.files | ForEach-Object path)","@((Get-Content -LiteralPath (Join-Path $package 'TRANSFER_FILES.json') -Raw -Encoding UTF8 | ConvertFrom-Json).files)")
    anchor='    & $uart -Command "sudo -n bash -n $remote/run_m417_reference.sh"'
    assert control.count(anchor)==1
    control=control.replace(anchor,'''    & $uart -Command "sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B $remote/assemble_m417.py $digest" -LogPath 'tmp/m41702/assembly.log' -TimeoutSeconds 90 -MarkerPrefix '__M417_ASSEMBLY_RC_'
    if (-not $?) { throw 'Complete assembly rejected; no gate' }
'''+anchor)
    atomic(HERE/'m417_control02.ps1',control.encode('utf-8'),immutable=True)
    closure=(HERE/'m417_close_reference.py').read_text(encoding='utf-8').replace('latest_m417_reference_board','latest_m417_reference_board02').replace('latest_m417_reference_closure','latest_m417_reference_closure02').replace('M417-layer13-reference-closure-01','M417-layer13-reference-closure-02')
    atomic(HERE/'m417_close_reference02.py',closure.encode('utf-8'),immutable=True)
    note='## M417 独立组件间接依赖漏包（2026-10-06）\n\n原FAIL SHA '+board['latest_m417_reference_board']['sha256']+'，rc1/export0，7块完整回收；完整资产与49源码通过后，独立child导入m408_target_component04间接需要m408_target03，包内缺失。主机旧检查继承scripts/optimization的PYTHONPATH，同名文件掩盖了漏包。0模型构造/局部MLP/视觉/语言/Overlay/DMA/PL。必须从干净staging以隔离sys.path执行真实child并核对递归本地导入；不能把宿主开发目录当板端依赖。新02仅补同SHA依赖与新结果目录，原模型/数学与失败保持；M418不得在M417失败级启动。\n\n'
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';s=review.read_text(encoding='utf-8-sig')
    if note not in s:
        title,rest=s.split('\n',1);atomic(review,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    value=dict(status='PREPARED_M417_DEPENDENCY_REPAIR02',failed_raw_sha256=board['latest_m417_reference_board']['sha256'],
               old_manifest_sha256=sha(old/'PACKAGE_MANIFEST.json'),manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               recursive_known_local_missing=sorted(missing),unchanged_math=True,dependency_sha256=sha(dependency),delta_files=delta,
               delta_bytes=sum((pkg/n).stat().st_size for n in delta),board_run=False,performance_pass=False,
               next='Clean-path actual child must reproduce old missing import and pass corrected02, then actual delta assembly/collector/control before same software reference retry. No visual recapture or PL.')
    out=BASE/'runs/M417-layer13-reference-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m417_reference_preparation02',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
         f'## M417 同级依赖修复02准备（2026-10-06）\n\nSHA {sha(out)}；原失败和旧包保留，只补已验证同SHA m408_target03间接依赖及新02结果目录。递归已知本地依赖missing=0，先干净sys.path实际child复现旧失败/新通过，再实际差量组装与回收控制验证。0新视觉/MLP/Overlay/DMA/PL；M418尚未准备包或上板，失败级未解锁。')
    print('M417_DEPENDENCY_REPAIR_PREPARED',sha(out),value['manifest_sha256'],value['delta_bytes'])

if __name__=='__main__':main()
