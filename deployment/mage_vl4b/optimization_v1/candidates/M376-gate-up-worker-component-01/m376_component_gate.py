"""Explicit CPU component capability; no Overlay, assets, model or DMA."""
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
HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m376_gate_up_component_evidence_01')
PRIOR='8ff1d4f94471584ec95ff60b8fa3c4c4a8840709f2c010ec356fd1a07fa05b56'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('manifest_sha');parser.add_argument('--enable-fixture-gate',action='store_true')
    args=parser.parse_args()
    if not args.enable_fixture_gate:raise RuntimeError('Disabled by default')
    if os.geteuid()!=0 or platform.system()!='Linux':raise RuntimeError('Linux root required')
    OUT.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    result=dict(status='FAIL_GATE_UP_WORKER_CPU_COMPONENT',gate_level='CPU-gate-up-worker-capability',
        target_build_id='0x4D333537',prior_raw_sha256=PRIOR,manifest_sha256=args.manifest_sha,
        overlay_loaded=False,real_assets_read=False,model_forward_calls=0,fpga_transactions=0,
        extra_pynq_allocations=0,ps_prefetch_enabled=False,memory_capacity_proven=False,
        numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        platform=dict(uname=list(platform.uname()),python=sys.version,executable=sys.executable,euid=os.geteuid()),
        scope='Actual Linux Python/NumPy; real pinned parser/Futures with synthetic packets and explicit fake DMA',errors=[])
    try:
        if sha(HERE/'PACKAGE_MANIFEST.json')!=args.manifest_sha:raise RuntimeError('Manifest differs')
        manifest=json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));names=set()
        for row in manifest['files']:
            name=row['path']
            if Path(name).name!=name or name in names:raise RuntimeError('Unapproved path')
            names.add(name)
            if (HERE/name).stat().st_size!=row['bytes'] or sha(HERE/name)!=row['sha256']:raise RuntimeError('Payload differs')
        if len(names)!=manifest['file_count'] or sum(r['bytes'] for r in manifest['files'])!=manifest['total_bytes']:raise RuntimeError('Count/bytes differs')
        if {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Unexpected member')
        if sha(HERE/'M376_AUDIT.json')!=PRIOR:raise RuntimeError('Audit differs')
        import test_m376_gate_up_workers as tests
        from m376_gate_up_workers import PINNED
        stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
        ids=[t.id().split('.')[-1] for s in suite for t in s]
        checks=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        import numpy as np
        result.update(tests_run=checks.testsRun,test_ids=ids,test_output=stream.getvalue(),numpy_version=np.__version__,
            pinned_source_sha256=PINNED,worker_component_sha256=sha(HERE/'m376_gate_up_workers.py'),
            fixture_sha256=sha(HERE/'GATE_UP_FIXTURE.json'))
        if checks.testsRun!=12 or not checks.wasSuccessful():raise RuntimeError('Component checks failed')
        result['lifecycle']=dict(active_workers=[t.name for t in threading.enumerate() if t is not threading.main_thread()])
        if result['lifecycle']['active_workers']:raise RuntimeError('Fixture workers retained')
        if time.monotonic()-started>60:raise RuntimeError('Fixture budget60s exceeded')
        result['status']='PASS_GATE_UP_TWO_WORKER_CPU_COMPONENT_ONLY'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()
    result.update(elapsed_s=time.monotonic()-started,gate_return_code=1 if result['errors'] else 0)
    raw=(json.dumps(result,ensure_ascii=True,indent=2)+'\n').encode('utf-8');part=OUT/'BOARD_RESULT.part'
    with part.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(part,OUT/'BOARD_RESULT.json');print('M376_COMPONENT_RESULT status='+result['status'],flush=True)
    return result['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
