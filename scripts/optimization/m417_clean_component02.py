"""Use Python -I and only one staged packet on PYTHONPATH, exposing masked imports."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and all(Path(p).resolve()!=HERE for p in sys.path if p)
clean=list(sys.path)
old=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-01'
new=old.with_name('M417-layer13-saved-reference-02')
sys.path[:]=[str(old),*clean]
import torch
from m414_entry import run_component
bad=ROOT/'tmp/m41702/component_old';bad.mkdir(parents=True,exist_ok=True)
try:run_component(ROOT,bad,old/'m417_component_entry.py')
except RuntimeError as e:
    assert "No module named 'm408_target03'" in str(e);old_error=str(e)
else:raise AssertionError('Clean staging masked old missing dependency')
sys.path[:]=[str(new),*clean]
good=ROOT/'tmp/m41702/component';good.mkdir(parents=True,exist_ok=True)
answer,isolation=run_component(ROOT,good,new/'m417_component_entry.py')
assert answer['independent_int32_full_output_equal'] and answer['invalid_native_inputs_rejected']==4 and answer['bindings_restored']
assert isolation['parent_state_unchanged'] and isolation['return_code']==0
result=dict(status='PASS_M417_CLEAN_STAGING_COMPONENT02',isolated_parent=True,no_developer_directory_on_child_path=True,
            old_missing_dependency_reproduced=True,old_error=old_error,new_actual_packaged_entry=True,
            component=answer,isolation=isolation,model_forward_calls=0,board_run=False)
with (good/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('M417_CLEAN_STAGING_OLD_FAIL_NEW_PASS',flush=True)
