"""One bounded readonly environment snapshot; no hardware/model imports."""
import base64, hashlib, json, os, sys, time
from pathlib import Path
from m424_environment import read_environment
HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m424_environment_probe_01/RESULT.json')


def emit():
    raw=OUT.read_bytes();parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M424_ENV_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i,p in enumerate(parts):
        print(f'M424_ENV_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True)
        time.sleep(.025)


def main():
    if os.geteuid()!=0:raise RuntimeError('Root required')
    if len(sys.argv)==3 and sys.argv[2]=='Collect':emit();return 0
    if len(sys.argv)!=3 or sys.argv[2]!='--enable-readonly-probe':raise RuntimeError('Probe disabled by default')
    if OUT.parent.exists():raise RuntimeError('Original result exists; Collect only')
    started=time.monotonic()
    r=dict(status='FAIL_M424_ENVIRONMENT_OBSERVABILITY',gate_return_code=1,errors=[],
           manifest_sha256=sys.argv[1],overlay_loaded=False,model_forward_calls=0,
           dma_allocations=0,fpga_transactions=0,cache_changes=False,
           performance_pass=False,throttling_absence_proven=False)
    try:
        manifest=HERE/'PACKAGE_MANIFEST.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Manifest differs')
        m=json.loads(manifest.read_bytes());names={x['path'] for x in m['files']}
        if len(names)!=m['file_count'] or {x.name for x in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
        for x in m['files']:
            p=HERE/x['path']
            if p.is_symlink() or p.stat().st_size!=x['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise RuntimeError('Payload SHA differs')
        if sum(x['bytes'] for x in m['files'])!=m['total_bytes']:raise RuntimeError('Payload byte count differs')
        r['environment']=read_environment()
        if r['environment']['observability_issues']:raise RuntimeError('Environment incomplete: '+repr(r['environment']['observability_issues']))
        r['status']='PASS_M424_READONLY_ENVIRONMENT_OBSERVABLE';r['gate_return_code']=0
    except BaseException as e:r['errors'].append(type(e).__name__+': '+str(e))
    r['elapsed_s']=time.monotonic()-started
    raw=(json.dumps(r,ensure_ascii=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>32768:raise RuntimeError('Export budget exceeded')
    OUT.parent.mkdir();temp=OUT.with_suffix('.partial')
    with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,OUT);emit();return r['gate_return_code']


if __name__=='__main__':raise SystemExit(main())
