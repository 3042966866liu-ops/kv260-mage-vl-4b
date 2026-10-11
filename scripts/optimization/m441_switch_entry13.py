"""Frozen original owner gate, one new literal evidence path and narrow trials."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

OLD=Path('/home/ubuntu/m441_complete_request_candidate_09')
REUSE=Path('/home/ubuntu/m368_staged_video_candidate_03')
OUT=Path('/home/ubuntu/m441_first_switch_cma_evidence_13')
OLD_SHA='74584820f1989d62614c0d50a74ce913fe56a7b19bdd44da5eda63d8c4e8ee57'

def verify(path,sha):
    assert hashlib.sha256((path/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()==sha
    manifest=json.loads((path/'PACKAGE_MANIFEST.json').read_bytes())
    for r in manifest['files']:
        p=path/r['path']
        if p.is_symlink() or p.stat().st_size!=r['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Frozen payload changed: '+str(p))

def main():
    assert sys.flags.isolated and len(sys.argv)==2 and sys.argv[1]=='--enable-first-switch-only'
    assert not OUT.exists(),'Collect only: existing attempt'
    here=Path(__file__).resolve().parent
    verify(OLD,OLD_SHA);verify(REUSE,'f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66')
    sys.path[:0]=[str(here),str(OLD),str(REUSE)]
    from frozen_video_identity import module_paths
    sys.path[:0]=[str(p) for p in module_paths()]
    import m441_cma_trace13 as diagnostic
    import m441_performance_trials as trials
    trials.run=diagnostic.narrow_run
    import m441_performance_export as exporter
    from m441_switch_export13 import emit
    exporter.emit_saved=emit  # collect fresh raw while the unsafe original owner remains alive
    source=(OLD/'m441_performance_gate.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    replacements=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and node.value=='/home/ubuntu/m441_complete_request_evidence_09':
            node.value=str(OUT);replacements+=1
    assert replacements==1,'Only the new immutable evidence path may differ'
    namespace={'__file__':str(OLD/'m441_performance_gate.py'),'__name__':'m441_original_owner_diagnostic13'}
    exec(compile(tree,str(OLD/'m441_performance_gate.py'),'exec'),namespace)
    sys.argv=[namespace['__file__'],OLD_SHA,'B1','--enable-staged-video']
    rc=namespace['main']()
    gate=json.loads((OUT/'BOARD_RESULT.json').read_bytes())
    detail=diagnostic.verdict(gate)
    diagnostic.save(OUT/'DIAG_RESULT.json',dict(schema='m441-first-switch-cma13',status=detail['status'],original_gate_rc=rc,
                    original_owner_raw_sha256=hashlib.sha256((OUT/'BOARD_RESULT.json').read_bytes()).hexdigest(),gate=gate,diagnostic=detail))
    print('M441D_DIAGNOSTIC_RESULT '+detail['status'],flush=True)
    return rc

if __name__=='__main__':raise SystemExit(main())
