import base64,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m431_borrowed_cpu_result_01/BOARD_RESULT.json')
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
    print('M431_BOOT_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M431_BOOT_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    pieces=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,b in enumerate(pieces):
        print('M431_BOOT_RESULT_CHUNK='+str(i)+'/'+str(len(pieces))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.03)
def main():
    if sys.argv[2]=='Collect':emit();return 0
    if sys.argv[2]!='--enable-CPU-bootstrap' or os.geteuid()!=0:raise RuntimeError('Explicit root CPU gate required')
    if OUTPUT.parent.exists():raise RuntimeError('Saved CPU attempt exists; Collect only')
    OUTPUT.parent.mkdir(mode=0o700);start=time.monotonic()
    r=dict(status='FAIL_M431_ISOLATED_CPU_BOOTSTRAP',gate_return_code=1,manifest_sha256=sys.argv[1],errors=[],overlay_loads=0,DMA_allocations=0,real_model_forward_calls=0,FPGA_transactions=0,temperature_measurement_enabled=False,performance_pass=False)
    try:
        package(HERE,sys.argv[1]);plan=json.loads((HERE/'PLAN.json').read_bytes())
        package(Path(plan['component_package']),plan['component_manifest_sha256'])
        for x in plan['reused_packages']:package(Path(x['directory']),x['manifest_sha256'])
        numerical_path=Path(plan['visual_result_path'])
        if digest(numerical_path)!=plan['visual_result_sha256']:raise RuntimeError('Completed visual source differs')
        prior=json.loads(numerical_path.read_bytes())
        if prior['status']!='PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED' or not prior['performance_pass'] or not prior['stable_restored']:raise RuntimeError('Visual net-benefit prerequisite rejected')
        root=Path(plan['release']);source=json.loads((HERE/'SOURCE_IDENTITIES.json').read_bytes())
        for x in source['files']:
            p=root/x['path']
            if p.is_symlink() or p.stat().st_size!=x['bytes'] or digest(p)!=x['sha256']:raise RuntimeError('Frozen source SHA differs')
        r['source_identities_verified']=len(source['files'])
        child=subprocess.run([sys.executable,'-I','-B',str(HERE/'m431_component_entry.py'),str(root)],capture_output=True,timeout=180)
        save(OUTPUT.parent/'child_stdout.bin',child.stdout);save(OUTPUT.parent/'child_stderr.bin',child.stderr)
        r['child_return_code']=child.returncode;r['child_stdout']=owned(OUTPUT.parent/'child_stdout.bin');r['child_stderr']=owned(OUTPUT.parent/'child_stderr.bin')
        if child.returncode:raise RuntimeError('Repaired isolated child rejected')
        text=child.stdout.decode('utf-8');receipts={}
        for tag in ('M431_BOOTSTRAP','M431_COMPONENT'):
            lines=[x.split('=',1)[1] for x in text.splitlines() if x.startswith(tag+'=')]
            if len(lines)!=1:raise RuntimeError('Unique CPU receipt required')
            receipts[tag]=json.loads(lines[0])
        b=receipts['M431_BOOTSTRAP'];c=receipts['M431_COMPONENT']
        if not b['isolated'] or b['release']!=str(root) or b['threads']!=1:raise RuntimeError('Isolated backend identity differs')
        Path(b['torch_path']).relative_to(root/'runtime_site')
        if c['window']['complete_batches']!=286 or c['window']['staged_windows']!=22 or not c['window']['fake_DMA_MMIO_policy_and_byte_content'] or len(c['negative']['negative_checks'])!=15 or not c['negative']['timeout_preserves_original_owner']:raise RuntimeError('Borrowed CPU fixture incomplete')
        r.update(status='PASS_M431_ISOLATED_CPU_BOOTSTRAP_ONLY',gate_return_code=0,bootstrap=b,component=c)
    except BaseException as e:r['errors'].append(dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
    r['elapsed_s']=time.monotonic()-start
    save(OUTPUT,(json.dumps(r,indent=2)+'\n').encode());emit();return r['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
