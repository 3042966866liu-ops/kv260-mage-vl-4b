"""Freeze numerical fixture/FTZ policy and the two ordered minimal gate levels."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,data):
    part=path.with_name(path.name+'.m342-part');part.write_bytes(data);os.replace(part,path)


def main():
    package=BASE/'candidates/M342-prefetch-fixture-01';run=BASE/'runs/M342-fixture-offline-01'
    if package.exists() or run.exists():raise RuntimeError('Immutable preparation exists')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (ROOT/name).read_text(encoding='utf-8-sig')
    prerequisite=BASE/'runs/M341-build-id-board-01/BOARD_RESULT.json'
    if sha(prerequisite)!='3145e1aa9cc34a96a394ca1fda000ceaeb281d0d6427707f5366c1d61b8bc342':raise RuntimeError('Build proof drift')
    prior=json.loads(prerequisite.read_text(encoding='utf-8'))
    if prior['status']!='PASS' or prior['unsafe_dma_buffers_retained']:raise RuntimeError('Build gate not safely passing')
    initial=ROOT/'deployment/mage_vl4b/m120_text4b_board_candidate'
    spec=importlib.util.spec_from_file_location('m342_fixture_local',initial/'runtime/m120_fixture.py')
    fixture_module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixture_module;spec.loader.exec_module(fixture_module)
    source=(HERE/'m342_prefetch_fixture_gate.py').read_text(encoding='utf-8');tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='canonicalize')
    import numpy as np
    ns={'np':np};exec(ast.get_source_segment(source,node),ns)
    fixture=initial/'reference/m128_m120_real_record_csim_fixture.bin'
    if sha(fixture)!='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9':raise RuntimeError('Numerical fixture drift')
    cases=fixture_module.load_fixture(fixture)
    policy_path=ROOT/'deployment/mage_vl4b/M157_M120_FP16_FTZ_POLICY_RESULT.json'
    policy=json.loads(policy_path.read_text(encoding='utf-8'));golden=[]
    for level,contract in policy['contracts'].items():
        built=fixture_module.build_case(cases[0],contract['descriptor_count'])
        expected,count=ns['canonicalize'](built['expected'])
        rawsha=hashlib.sha256(built['expected']).hexdigest();canonicalsha=hashlib.sha256(expected).hexdigest()
        if (rawsha,canonicalsha,count)!=(contract['original_sha256'],contract['canonical_sha256'],contract['canonicalized_subnormal_count']):raise RuntimeError('Frozen independent golden mismatch')
        golden.append(dict(level=level,raw_sha256=rawsha,canonical_sha256=canonicalsha,descriptor_count=contract['descriptor_count']))
    package.mkdir(parents=True);run.mkdir(parents=True)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        shutil.copyfile(ROOT/name,run/(Path(name).name+'.before'))
    sources={'m342_prefetch_fixture_gate.py':HERE/'m342_prefetch_fixture_gate.py','m120_fixture.py':initial/'runtime/m120_fixture.py',
        'weight_prefetch.py':BASE/'candidates/M340-weight-prefetch-component-01/weight_prefetch.py',
        'M157_FTZ_POLICY.json':policy_path,'BUILD_ID_PREREQUISITE.json':prerequisite}
    prior_package=BASE/'candidates/M341-build-id-01'
    for name in ('m341_build_id_gate.py','measurement.py','board_safety.py','m120_board_common.py','m120_board_env_preflight.py','HARDWARE_CLOSURE.json'):
        sources[name]=prior_package/name
    for name,path in sources.items():shutil.copyfile(path,package/name)
    runner='''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
level=${1:?single-descriptor or single-chain required}
[[ $level == single-descriptor || $level == single-chain ]] || exit 2
manifest_sha=${2:?exact package SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
extra=()
if [[ $level == single-chain ]]; then extra=(--previous-sha "${3:?exact PASS descriptor SHA required}"); fi
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \\
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m342_prefetch_fixture_gate.py" "$level" "$manifest_sha" "${extra[@]}"
gate_rc=$?
set -e
printf 'M342_FIXTURE_DONE level=%s gate_rc=%s\\n' "$level" "$gate_rc"
exit "$gate_rc"
'''
    (package/'run_m342_fixture.sh').write_text(runner,encoding='utf-8',newline='\n')
    rows=[]
    for path in sorted(package.iterdir()):
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
        rows.append(dict(path=path.name,bytes=path.stat().st_size,sha256=sha(path)))
    (package/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in rows),encoding='utf-8',newline='\n')
    rows.append(dict(path='SHA256SUMS',bytes=(package/'SHA256SUMS').stat().st_size,sha256=sha(package/'SHA256SUMS')))
    manifest=dict(schema='tellme-m342-ordered-prefetch-fixture-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
                  hardware_changed=False,performance_pass=False,numerical_contract='Existing exact M157 FP16-subnormal-to-signed-zero; no new tolerance',golden=golden)
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    result=dict(status='PASS_OFFLINE_MINIMAL_GATE_PREPARATION',build_id='0x4D395832',package_manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),golden=golden,
        hardware_gate_run=False,prefetch_candidate_gate_run=False,performance_pass=False,
        next_step='Upload/verify; descriptor only first; collect and synchronize before chain invocation with exact descriptor PASS hash')
    atomic(run/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(dict(status=result['status'],manifest_sha=result['package_manifest_sha256'],files=len(rows),bytes=manifest['total_bytes'],golden=golden)))


if __name__=='__main__':main()
