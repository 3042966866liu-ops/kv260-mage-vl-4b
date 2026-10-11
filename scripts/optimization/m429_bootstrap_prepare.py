"""Bounded isolated CPU bootstrap repair; preserve original numerical attempt."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OLD=BASE/'candidates/M429-late11-visual-PL-numeric-02'
PKG=BASE/'candidates/M429-isolated-bootstrap-02'
REMOTE='/home/ubuntu/m429_isolated_bootstrap_02'

ENTRY='''import sys,json
from pathlib import Path
if not sys.flags.isolated:raise RuntimeError('Isolated interpreter required')
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here),plan['component_package']]+[x['directory'] for x in plan['reused_packages']]
from frozen_video_identity import RELEASE,module_paths
if RELEASE!=Path(sys.argv[1]) or str(RELEASE)!=plan['release']:raise RuntimeError('Frozen release root differs')
# -I deliberately ignores PYTHONPATH. Bootstrap only frozen installed paths.
paths=[str(p) for p in module_paths()]
if paths[0]!=str(RELEASE/'runtime_site'):raise RuntimeError('Frozen runtime path differs')
sys.path[:0]=paths
import torch,numpy as np
torch_path=Path(torch.__file__).resolve()
torch_path.relative_to((RELEASE/'runtime_site').resolve())
torch.set_num_threads(1)
print('M429_BOOTSTRAP='+json.dumps(dict(isolated=True,release=str(RELEASE),module_paths=paths,torch_path=str(torch_path),torch_version=torch.__version__,numpy_path=str(Path(np.__file__).resolve()),numpy_version=np.__version__,threads=torch.get_num_threads())),flush=True)
from test_m429_range import component
value=component(RELEASE)
if any(x=='pynq' or x.startswith('pynq.') for x in sys.modules):raise RuntimeError('Unexpected PYNQ import')
print('M429_COMPONENT='+json.dumps(value),flush=True)
'''

PROBE='''import base64,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m429_isolated_bootstrap_result_01/BOARD_RESULT.json')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,b):
    if p.exists():raise RuntimeError('Immutable saved artifact exists')
    t=p.with_suffix(p.suffix+'.partial')
    with t.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
def owned(p):
    before=p.lstat()
    if p.is_symlink() or before.st_uid!=0 or before.st_size>32768:raise RuntimeError('Original diagnostic file identity rejected')
    with p.open('rb') as f:
        if identity(os.fstat(f.fileno()))!=identity(before):raise RuntimeError('Open identity differs')
        b=f.read(32769)
        if identity(os.fstat(f.fileno()))!=identity(before):raise RuntimeError('Read identity differs')
    if identity(p.lstat())!=identity(before) or len(b)!=before.st_size:raise RuntimeError('Final identity differs')
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),base64=base64.b64encode(b).decode(),identity=list(identity(before)))
def package(folder,expected):
    if digest(folder/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Manifest differs')
    m=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes())
    if {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}!={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Exact package closure differs')
    if len(m['files'])!=m['file_count'] or sum(r['bytes'] for r in m['files'])!=m['total_bytes']:raise RuntimeError('Manifest counts differ')
    for row in m['files']:
        p=folder/row['path']
        if p.is_symlink() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Payload differs')
def emit():
    raw=OUTPUT.read_bytes();r=json.loads(raw)
    if os.geteuid()!=0 or len(raw)>131072:raise RuntimeError('Root/size export rejected')
    print('M429_BOOT_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M429_BOOT_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    pieces=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,b in enumerate(pieces):
        print('M429_BOOT_RESULT_CHUNK='+str(i)+'/'+str(len(pieces))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.03)
def main():
    if sys.argv[2]=='Collect':emit();return 0
    if sys.argv[2]!='--enable-CPU-bootstrap' or os.geteuid()!=0:raise RuntimeError('Explicit root CPU gate required')
    if OUTPUT.parent.exists():raise RuntimeError('Saved CPU attempt exists; Collect only')
    OUTPUT.parent.mkdir(mode=0o700);start=time.monotonic()
    r=dict(status='FAIL_M429_ISOLATED_CPU_BOOTSTRAP',gate_return_code=1,manifest_sha256=sys.argv[1],errors=[],overlay_loads=0,DMA_allocations=0,real_model_forward_calls=0,FPGA_transactions=0,temperature_measurement_enabled=False,performance_pass=False)
    try:
        package(HERE,sys.argv[1]);plan=json.loads((HERE/'PLAN.json').read_bytes())
        package(Path(plan['component_package']),plan['component_manifest_sha256'])
        for x in plan['reused_packages']:package(Path(x['directory']),x['manifest_sha256'])
        root=Path(plan['release']);source=json.loads((HERE/'SOURCE_IDENTITIES.json').read_bytes())
        for x in source['files']:
            p=root/x['path']
            if p.is_symlink() or p.stat().st_size!=x['bytes'] or digest(p)!=x['sha256']:raise RuntimeError('Frozen source SHA differs')
        r['source_identities_verified']=len(source['files'])
        r['original_child_files']=[owned(Path('/home/ubuntu/m429_late11_visual_numeric_01')/n) for n in ('component_stdout.bin','component_stderr.bin')]
        child=subprocess.run([sys.executable,'-I','-B',str(HERE/'m429_component_entry.py'),str(root)],capture_output=True,timeout=180)
        save(OUTPUT.parent/'child_stdout.bin',child.stdout);save(OUTPUT.parent/'child_stderr.bin',child.stderr)
        r['child_return_code']=child.returncode;r['child_stdout']=owned(OUTPUT.parent/'child_stdout.bin');r['child_stderr']=owned(OUTPUT.parent/'child_stderr.bin')
        if child.returncode:raise RuntimeError('Repaired isolated child rejected')
        text=child.stdout.decode('utf-8');receipts={}
        for tag in ('M429_BOOTSTRAP','M429_COMPONENT'):
            lines=[x.split('=',1)[1] for x in text.splitlines() if x.startswith(tag+'=')]
            if len(lines)!=1:raise RuntimeError('Unique CPU receipt required')
            receipts[tag]=json.loads(lines[0])
        b=receipts['M429_BOOTSTRAP'];c=receipts['M429_COMPONENT']
        if not b['isolated'] or b['release']!=str(root) or b['threads']!=1:raise RuntimeError('Isolated backend identity differs')
        Path(b['torch_path']).relative_to(root/'runtime_site')
        if c['complete_wire_batches']!=286 or len(c['negative_checks'])!=20 or not c['restored'] or not c['fake_PL_submit'] or not c['no_DMA_or_Overlay']:raise RuntimeError('Actual CPU fixture incomplete')
        r.update(status='PASS_M429_ISOLATED_CPU_BOOTSTRAP_ONLY',gate_return_code=0,bootstrap=b,component=c)
    except BaseException as e:r['errors'].append(dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
    r['elapsed_s']=time.monotonic()-start
    save(OUTPUT,(json.dumps(r,indent=2)+'\\n').encode());emit();return r['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
'''

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m429_late11_visual_PL_board','latest_m429_late11_visual_numerical_closure'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    failed=json.loads((ROOT/board['latest_m429_late11_visual_PL_board']['result']).read_bytes())
    assert failed['dma_allocations']==failed['fpga_transactions']==failed['visual_forward_calls']==0 and not failed['overlay_loaded']
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan['component_package']='/home/ubuntu/m429_late11_visual_candidate_02';plan['component_manifest_sha256']=sha(OLD/'PACKAGE_MANIFEST.json');plan['release']='/home/ubuntu/tellme_release_install_20260926'
    PKG.mkdir(parents=True,exist_ok=False)
    for name,raw in [('PLAN.json',encoded(plan)),('SOURCE_IDENTITIES.json',(OLD/'SOURCE_IDENTITIES.json').read_bytes()),('m429_component_entry.py',ENTRY.encode()),('m429_bootstrap.py',PROBE.encode())]:atomic(PKG/name,raw,immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?explicit CPU gate or Collect}
printf '%s  PACKAGE_MANIFEST.json\\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
export PYTHONDONTWRITEBYTECODE=1
exec /usr/local/share/pynq-venv/bin/python -I -B ./m429_bootstrap.py "$task_manifest" "$task_mode"
'''
    atomic(PKG/'run_bootstrap.sh',runner.encode(),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    old_entry=ast.parse((OLD/'m429_component_entry.py').read_text(encoding='utf-8'));new_entry=ast.parse(ENTRY)
    old_tail=old_entry.body[-4:];new_tail=new_entry.body[-4:]
    # Import/component execution and output retain identical fixture calls.
    assert ast.dump(old_tail[0])==ast.dump(new_tail[0]) and ast.dump(old_tail[3])==ast.dump(new_tail[3])
    assert ast.dump(old_tail[1].value.func)==ast.dump(new_tail[1].value.func)
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    out=BASE/'runs/M429-isolated-bootstrap-preparation-01/RESULT.json'
    r=dict(status='M429_ISOLATED_CPU_BOOTSTRAP_PREPARED',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),original_failure_sha256=board['latest_m429_late11_visual_PL_board']['sha256'],old_component_packet_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],repair='Explicit frozen module_paths() bootstrap before Torch under -I; retain original component and checks.',unexecuted_draft_01='Preserved before manifest: host AST check treated equivalent checked RELEASE and Path(sys.argv[1]) expressions as different; narrowed to exact component callable plus explicit root equality. No board operation.',no_real_model_or_DMA_or_Overlay=True,temperature_measurement_enabled=False,board_run=False)
    atomic(out,encoded(r),immutable=True)
    sync('latest_m429_isolated_bootstrap_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M429 隔离CPU入口路径修复准备（2026-10-06）\n\nSHA {sha(out)}；原失败在isolated child import torch，0模型构造/Overlay/DMA/PL。新小包manifest {r["manifest_sha256"]}，仅显式复用冻结module_paths()，保留-I隔离、原fixture及49源码/旧包完整SHA。先板端CPU子进程，严格回收原stderr及新receipt，不重跑资产/视觉/语言，不测温。')
    print('M429_BOOTSTRAP_PREPARED',sha(out),r['manifest_sha256'],m['total_bytes'])
if __name__=='__main__':main()
