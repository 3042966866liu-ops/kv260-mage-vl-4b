"""Exact retained M413 derivative; original CPU reference before any Overlay."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha


def main():
    old=BASE/'candidates/M413-layer12-full-visual-01'
    for name in ('m413_policy.py','m413_quality.py','m413_export.py','test_m413_quality.py'):
        s=(old/name).read_text(encoding='utf-8').replace('M413','M414').replace('m413','m414')
        if name=='test_m413_quality.py':
            line="if __name__=='__main__':print('M414_COMPONENT='+json.dumps(component()))"
            assert s.count(line)==1
            s=s.replace(line,"if __name__=='__main__':\n    result=component(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT)\n    assert 'pynq' not in sys.modules\n    print('M414_COMPONENT='+json.dumps(result))")
        atomic(HERE/name.replace('m413','m414'),s.encode('utf-8'),immutable=True)
    s=(old/'m413_gate.py').read_text(encoding='utf-8').replace('M413','M414').replace('m413','m414')
    s=s.replace('import argparse,gc,','import contextlib,argparse,gc,')
    anchor="        from test_m414_quality import component\n        r['component']=component(ROOT)"
    assert s.count(anchor)==1
    s=s.replace(anchor,"        from m414_entry import run_component,retain_reference\n        r['component'],r['component_process']=run_component(ROOT,OUTPUT.parent)")
    start=s.index('        with torch.inference_mode():\n            phase[0]=\'original-full-visual\'')
    boundary=s.index("            phase[0]='layer12-PL-full-visual'",start)
    body=s[start+len('        with torch.inference_mode():\n'):boundary]
    body=''.join(line[4:] if line.startswith('    ') else line for line in body.splitlines(keepends=True))
    old_assert="        if r['original_visual']!=expected_visual['visual']:raise RuntimeError('Original complete visual SHA differs')\n        if any(not np.array_equal(cap.values[k].view(np.uint32),original[k].view(np.uint32)) for k in original):raise RuntimeError('Original layer12 real input/capture differs')\n        r['original_layer12_capture']={k:tensor(v) for k,v in cap.values.items()}"
    assert body.count(old_assert)==1
    body=body.replace(old_assert,"""        r['original_layer12_capture']={k:tensor(v) for k,v in cap.values.items()}
        r['bindings_restored']=all(restored)
        r['reference_mismatches']=dict(visual=r['original_visual']!=expected_visual['visual'],
            **{k:not np.array_equal(cap.values[k].view(np.uint32),original[k].view(np.uint32)) for k in original})
        if any(r['reference_mismatches'].values()):
            r['retained_failed_reference']=retain_reference(OUTPUT.parent,visual_a,cap.values)
            raise RuntimeError('Original complete visual/capture reference differs')""")
    body="        assert owner is None and allocator is None and not r['overlay_loads'] and not r['allocations'] and 'pynq' not in sys.modules\n        r['original_reference_before_overlay']=True\n"+body
    s=s[:start]+'        with contextlib.nullcontext():\n'+s[boundary:]
    point=s.index('        class WorkOwner(lower.Owner):')
    s=s[:point]+body+s[point:]
    # Guard actual chronological separation, not just zero-count metadata.
    tree=ast.parse(s,feature_version=(3,10));assert s.index("phase[0]='original-full-visual'")<s.index("zero(Path(lower_case['hardware_directory'])")
    calls=[]
    def visit(n,context):
        if isinstance(n,ast.With):context=context+[ast.unparse(x.context_expr) for x in n.items]
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='runtime':calls.append(context)
        for x in ast.iter_child_nodes(n):visit(x,context)
    visit(tree,[]);assert len(calls)==2 and not any('torch.inference_mode' in x for c in calls for x in c)
    atomic(HERE/'m414_gate.py',s.encode('utf-8'),immutable=True)
    for name in ('m413_workflow.py','m413_support.py','m413_close.py'):
        original=(HERE/name).read_text(encoding='utf-8');derived=original.replace('M413','M414').replace('m413','m414')
        atomic(HERE/name.replace('m413','m414'),derived.encode('utf-8'))
    proof=dict(status='M414_EXACT_ENTRY_DERIVATION_PREPARATION',original_frozen_gate_sha256=sha(old/'m413_gate.py'),new_gate_sha256=sha(HERE/'m414_gate.py'),
               unchanged_PL_binding_sha256=sha(old/'m411_mlp_binding.py'),runtime_calls=2,
               external_inference_context_removed=True,original_reference_before_Overlay=True,
               component_isolated_child=True,original_capture_before_comparison=True,
               bounded_failed_arrays_retained=True,root_cause_not_yet_proven=True,
               prior_WSL_context_component_sha256=sha(BASE/'runs/M414-context-component-01/RESULT.json'),
               original_input_weights_reference_thresholds_preserved=True,hardware_run=False)
    atomic(BASE/'runs/M414-entry-derivation-01/RESULT.json',encoded(proof),immutable=True)
    print('M414_GENERATED',proof['new_gate_sha256'])


if __name__=='__main__':main()
