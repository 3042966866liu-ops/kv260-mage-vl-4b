import hashlib,json,os,runpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
own=Path(__file__).resolve().parent
assert len(sys.argv)==2 and os.geteuid()==0 and sha(own/'PACKAGE_MANIFEST.json')==sys.argv[1]
m=json.loads((own/'PACKAGE_MANIFEST.json').read_bytes())
assert {f.relative_to(own).as_posix() for f in own.rglob('*') if f.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
for r in m['files']:
 f=own/r['path'];assert not f.is_symlink() and f.stat().st_nlink==1 and f.stat().st_size==r['bytes'] and sha(f)==r['sha256']
plan=json.loads((own/'DEMO_BOARD_PLAN.json').read_bytes());session=os.environ['CAMPUS_SESSION_ID'];assert len(session)==32 and all(c in '0123456789abcdef' for c in session);out=Path(plan['output_root'])/session
assert not out.exists() and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==plan['expected_boot']
fs=os.statvfs('/home/ubuntu/tellme_results');assert fs.f_bavail*fs.f_frsize>=plan['required_available_bytes']
assert Path('/home/ubuntu/tellme_results').stat().st_dev!=Path('/dev/shm').stat().st_dev
component=Path(plan['original_component']);assert sha(component/'PACKAGE_MANIFEST.json')==plan['original_component_manifest_sha256']
sys.argv=[str(own/'native.py'),plan['hardware_manifest_sha256'],'Request','--component-manifest-sha',plan['original_component_manifest_sha256'],'--demo-manifest-sha',sys.argv[1],'--enable-saved-fixture-gate']
runpy.run_path(str(own/'native.py'),run_name='__main__')
