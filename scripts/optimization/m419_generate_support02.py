"""Actual producer/collector checks for the isolated layer13 complete segment."""
from m351_workflow import HERE,atomic
s=(HERE/'m412_support.py').read_text(encoding='utf-8').replace('M412','M419').replace('import m412_workflow as w','import m419_workflow02 as w').replace("load('m412_gate')","load('m419_gate')").replace("load('m412_export')","load('m419_export')").replace('m412_actual_','m419_actual_').replace('tmp/m41201','tmp/m41902').replace('m412_control.ps1','m419_control02.ps1').replace('m412_workflow.py','m419_workflow02.py').replace('m412_support.py','m419_support02.py').replace('run_m412_mlp.sh','run_m419_mlp.sh').replace('M419-complete-visual-MLP-01','M419-layer13-complete-MLP-02').replace('latest_m412_complete_mlp_','latest_m419_complete_mlp_').replace('latest_m419_complete_mlp_board','latest_m419_complete_mlp_board02').replace('latest_m419_complete_mlp_support','latest_m419_complete_mlp_support02').replace('M419-complete-MLP-support-01','M419-complete-MLP-support-02')
assert s.count('        good=dict(failure,status=')==1
s=s.replace('        good=dict(failure,status=',"        good=dict(failure,component_isolation=dict(separate_process=True,parent_state_unchanged=True,return_code=0),status=")
anchor='        mutations += [complete+complete'
assert s.count(anchor)==1
s=s.replace(anchor,"        for k,v in [('separate_process',False),('parent_state_unchanged',False),('return_code',1)]:\n            x=copy.deepcopy(good);x['component_isolation'][k]=v;mutations.append(export(x))\n"+anchor)
anchor="    v=dict(status='PASS_M419_ACTUAL_PRODUCER_EXPORT_CONTROL_RECOVERY'"
assert s.count(anchor)==1
checks="""    cp=ROOT/'tmp/m41902/component/RESULT.json';component=json.loads(cp.read_bytes())
    assert component['no_developer_directory_on_child_path'] and component['actual_packaged_entry'] and component['isolation']['parent_state_unchanged'] and component['isolation']['return_code']==0
    # Verify the three actual saved-result paths before any allocation or board work.
    def output_path(name):
        tree=ast.parse((pkg/name).read_bytes())
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUTPUT' for t in n.targets))
        return assignment.value.args[0].value
    actual_output=output_path('m419_gate.py');assert actual_output==output_path('m419_export.py')=='/home/ubuntu/m419_complete_mlp_02/BOARD_RESULT.json'
    assert '[[ ! -e '+str(Path(actual_output).parent)+' ]]' in (pkg/'run_m419_mlp.sh').read_text(encoding='utf-8')
"""
s=s.replace(anchor,checks+anchor)
s=s.replace('actual_default_off_and_resource_before_source_failure=True,','actual_clean_staged_component=component,actual_clean_staged_component_sha256=sha(cp),gate_export_runner_result_paths_equal=True,actual_default_off_and_resource_before_source_failure=True,')
atomic(HERE/'m419_support02.py',s.encode('utf-8'),immutable=True)
print('M419_SUPPORT02_READY')
