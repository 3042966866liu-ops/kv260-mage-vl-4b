"""Default-off stdlib pre-entry: reject source before importing the hardware gate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from m400_tail_source_02 import validate

SOURCE=Path('/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py')
HERE=Path(__file__).resolve().parent
FROZEN_SHA='fc5543e48aecc49dad0c08eb5efefa82a12ed607088b30cbba1a9b792d06f40b'


def precheck(expected):
    path=HERE/'PACKAGE_MANIFEST.json'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Pre-entry manifest SHA differs')
    m=json.loads(path.read_bytes())
    rows=m['files'];names=[r['path'] for r in rows]
    if len(names)!=len(set(names)) or m['file_count']!=len(names):
        raise RuntimeError('Pre-entry package inventory differs')
    if any(Path(n).name!=n for n in names) or {p.name for p in HERE.iterdir()}!=set(names)|{'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Pre-entry recursive/package whitelist differs')
    for row in rows:
        p=HERE/row['path']
        if p.is_symlink() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Pre-entry payload SHA differs')
    if sum(r['bytes'] for r in rows)!=m['total_bytes']:
        raise RuntimeError('Pre-entry package byte count differs')
    proof=validate(SOURCE.read_bytes(),(HERE/'frozen_last_layer.py').read_bytes(),FROZEN_SHA)
    print('M400_SOURCE_PRECHECK_BEFORE_HARDWARE_IMPORT='+json.dumps(proof),flush=True)
    return proof


def main():
    if len(sys.argv)!=4 or sys.argv[2]!='B1' or sys.argv[3]!='--enable-tail-layer':
        raise RuntimeError('M400 entry disabled by default')
    proof=precheck(sys.argv[1])
    # No gate or its transitive imports run until the complete precheck succeeds.
    spec=importlib.util.spec_from_file_location('m400_tail_layer_gate_02',HERE/'m400_tail_layer_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    gate.SOURCE_PRECHECK_PROOF=proof
    return gate.main()


if __name__=='__main__':raise SystemExit(main())
