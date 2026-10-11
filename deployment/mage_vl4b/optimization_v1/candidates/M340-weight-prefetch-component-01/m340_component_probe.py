"""CPU-only real-Python component check and read-only CMA measurement."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback
import unittest
sys.dont_write_bytecode=True
RELEASE=Path('/home/ubuntu/tellme_release_install_20260926')
HERE=Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result=dict(status='FAIL_CPU_COMPONENT_ONLY', overlay_loaded=False, hardware_gate_run=False,
                cma_allocated=False, performance_pass=False, source_build='0x4D395832')
    try:
        manifest=HERE/'PACKAGE_MANIFEST.json'
        if sha(manifest)!=sys.argv[1]: raise RuntimeError('Component manifest mismatch')
        rows=json.loads(manifest.read_text(encoding='utf-8'))['files']
        for row in rows:
            path=HERE/row['path']
            if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']: raise RuntimeError('Component hash mismatch')
        release_manifest=RELEASE/'INSTALL_PACKAGE_MANIFEST.json'
        if sha(release_manifest)!='fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e':
            raise RuntimeError('Installed release identity differs')
        source=RELEASE/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
        if sha(source)!='5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201':
            raise RuntimeError('Stable copy source differs')
        sys.path.insert(0,str(RELEASE/'runtime_site'))
        import test_weight_prefetch
        test_weight_prefetch.SOURCE=source
        output=io.StringIO()
        measured=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_weight_prefetch))
        result.update(tests_run=measured.testsRun,test_output=output.getvalue(),python_version=sys.version,
                      copy_source_sha256=sha(source))
        if not measured.wasSuccessful() or measured.testsRun!=10: raise RuntimeError('CPU component tests failed')
        info={}
        for line in Path('/proc/meminfo').read_text().splitlines():
            fields=line.split()
            if fields[0].rstrip(':') in ('MemAvailable','CmaTotal','CmaFree'):
                info[fields[0].rstrip(':')]=int(fields[1])*1024
        if 'CmaFree' not in info: raise RuntimeError('CmaFree unavailable')
        required=4*6963200
        result.update(memory_bytes=info,extra_bank_bytes=required,reserve_bytes=64<<20,
                      cma_idle_snapshot_meets_reserve=info['CmaFree']>=required+(64<<20),
                      cma_caveat='Idle read-only snapshot; must remeasure after real runtime allocation, not proof of full-request fit',
                      status='PASS_CPU_COMPONENT_ONLY_NO_FPGA',measured_unix_s=time.time())
    except BaseException as exc:
        result.update(error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    payload=(json.dumps(result,indent=2)+'\n').encode()
    destination=HERE/'COMPONENT_RESULT.json'
    if destination.exists(): raise RuntimeError('Immutable result exists')
    temp=destination.with_suffix('.part');temp.write_bytes(payload);os.replace(temp,destination)
    print('M340_RESULT_SHA256='+hashlib.sha256(payload).hexdigest(),flush=True)
    print('M340_RESULT_BASE64='+base64.b64encode(payload).decode(),flush=True)
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__': raise SystemExit(main())
