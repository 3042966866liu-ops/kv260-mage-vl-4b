"""One immutable CPU-only fixture gate; no PYNQ/model imports or PL calls."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
import traceback
import unittest
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
EVIDENCE = Path('/home/ubuntu/m351_ps_component_evidence_01')
FIXTURES = Path('/home/ubuntu/m351_ps_component_fixtures_01')
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
PRIOR = '087bd3fe93ef78d33e306f4b431937da01266b37a46995cd5a8b557e9719c256'
SOURCE_SHA = '5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def memory():
    row = {}
    for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
        key, value = line.split(':', 1)
        if key in ('MemAvailable', 'Cached', 'CmaFree', 'CmaTotal'): row[key] = int(value.split()[0])*1024
    for line in Path('/proc/self/status').read_text(encoding='utf-8').splitlines():
        if line.startswith(('VmRSS:', 'VmHWM:')): row[line.split(':')[0]] = int(line.split()[1])*1024
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest_sha');p.add_argument('--enable-fixture-gate',action='store_true');a=p.parse_args()
    if not a.enable_fixture_gate: raise RuntimeError('Disabled by default')
    if os.geteuid()!=0: raise RuntimeError('Same-terminal sudo/root required')
    EVIDENCE.mkdir(mode=0o700, exist_ok=False)
    started=time.monotonic()
    r=dict(status='FAIL_PS_COMPONENT_ONLY',gate_level='PS-only-fixture-component',build_id='0x4D395832',
        prior_raw_sha256=PRIOR,manifest_sha256=a.manifest_sha,errors=[],
        overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,real_assets_read=False,
        memory_capacity_proven=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        cache_eviction=False,extra_pynq_allocations=0,
        scope='Real Linux fixture I/O and NumPy copy; explicit fake buffers/MMIO/memory. No completed PL or runtime-capacity proof',
        platform=dict(uname=list(platform.uname()),python=sys.version,executable=sys.executable,euid=os.geteuid()),
        memory_before=memory())
    try:
        if sha(HERE/'PACKAGE_MANIFEST.json')!=a.manifest_sha:raise RuntimeError('Manifest differs')
        m=json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        names=set()
        for row in m['files']:
            name=row['path']
            if Path(name).name!=name or name in names:raise RuntimeError('Non-whitelisted path')
            names.add(name);path=HERE/name
            if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise RuntimeError('Payload differs')
        if len(names)!=m['file_count'] or sum(v['bytes'] for v in m['files'])!=m['total_bytes']:raise RuntimeError('Count/bytes differ')
        if {v.name for v in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Unexpected package member')
        if json.loads((HERE/'DESIGN_PREREQUISITE.json').read_text(encoding='utf-8'))['raw_sha256']!=PRIOR:raise RuntimeError('Wrong M350')
        if sha(RELEASE/'INSTALL_PACKAGE_MANIFEST.json')!='fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e':raise RuntimeError('Installed release differs')
        source=RELEASE/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
        if sha(source)!=SOURCE_SHA:raise RuntimeError('Original copy source differs')
        FIXTURES.mkdir(mode=0o700,exist_ok=False)
        sys.path.insert(0,str(RELEASE/'runtime_site'))
        import test_ps_read_ahead as tests
        tests.SOURCE=source;tests.FIXTURE_PARENT=FIXTURES
        stream=io.StringIO()
        suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        r.update(tests_run=result.testsRun,test_output=stream.getvalue(),copy_source_sha256=sha(source),
            windows_ctime_adapter_active=False,maximum_window_bytes_per_port=6963200,
            maximum_ps_payload_bytes=27852800,fixture_data_max_live_bytes=4*(6963200+16),
            strict_linux_file_identity_fields=['dev','ino','size','mtime_ns','ctime_ns','mode','nlink'])
        if not result.wasSuccessful() or result.testsRun!=28:raise RuntimeError('PS component checks failed')
        if any(FIXTURES.iterdir()):raise RuntimeError('Fixture directories remain after tests')
        r['lifecycle']=dict(active_workers=[t.name for t in threading.enumerate() if t.name.startswith('m351-ps-read')],
            remaining_fixture_files=[v.name for v in FIXTURES.rglob('*')])
        if r['lifecycle']['active_workers'] or r['lifecycle']['remaining_fixture_files']:raise RuntimeError('CPU lifecycle not closed')
        if time.monotonic()-started>60:raise RuntimeError('60-second component budget exceeded')
        r['status']='PASS_PS_COMPONENT_ONLY_NO_FPGA'
    except BaseException as exc:
        r['errors'].append(type(exc).__name__+': '+str(exc));r['traceback']=traceback.format_exc()
    r.update(elapsed_s=time.monotonic()-started,memory_after=memory(),gate_return_code=0 if not r['errors'] else 1)
    raw=(json.dumps(r,ensure_ascii=True,indent=2)+'\n').encode('utf-8')
    out=EVIDENCE/'BOARD_RESULT.json';part=out.with_suffix('.part')
    with part.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(part,out)
    print('M351_COMPONENT_RESULT status='+r['status'],flush=True)
    return r['gate_return_code']

if __name__=='__main__':raise SystemExit(main())
