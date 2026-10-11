"""Actual subprocess/parent-state and bounded reference-save CPU checks."""
import hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M409-saved-MLP-reference-01'
spec=importlib.util.spec_from_file_location('m414_check_paths',PKG/'frozen_video_identity.py')
identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity);identity.RELEASE=ROOT
sys.path[:0]=[str(p) for p in identity.module_paths() if p.name!='runtime_site']
sys.path.insert(0,str(PKG));sys.path.insert(0,str(ROOT/'scripts/optimization'))
import numpy as np
from m414_entry import run_component,retain_reference
folder=ROOT/'tmp/m41401/entry-check';folder.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as temp:
    local=Path(temp);component,process=run_component(ROOT,local)
    assert component['negative_checks']==9 and process['parent_state_unchanged'] and process['separate_process']
    shapes=dict(residual=(392,1024),input=(392,1024),fc1=(392,4096),gelu=(392,4096),fc2=(392,1024),output=(392,1024))
    captures={k:np.ones(v,np.float32) for k,v in shapes.items()};visual=np.ones((98,2560),np.float32)
    rows=retain_reference(local,visual,captures)
    assert len(rows)==7 and sum(r['file_bytes'] for r in rows)<32<<20
    for r in rows:
        v=np.load(local/r['path'],allow_pickle=False)
        assert hashlib.sha256(v.tobytes()).hexdigest()==r['tensor']['sha256']
    rejects=0
    for kind in ('duplicate','shape','nonfinite'):
        try:
            if kind=='duplicate':retain_reference(local,visual,captures)
            else:retain_reference(local,visual[:97] if kind=='shape' else visual*np.nan,captures)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Invalid failure evidence accepted')
    assert rejects==3
    result=dict(status='PASS_M414_ACTUAL_COMPONENT_PROCESS_AND_BOUNDED_EVIDENCE',WSL_not_board=True,
                component=component,component_process=process,reference_artifacts=7,negative_checks=rejects,
                model_quality_or_performance=False,source_sha256={n:hashlib.sha256((ROOT/'scripts/optimization'/n).read_bytes()).hexdigest() for n in ('m414_entry.py','test_m414_quality.py')})
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
with target.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('M414_ENTRY_CHECK='+json.dumps(result))
