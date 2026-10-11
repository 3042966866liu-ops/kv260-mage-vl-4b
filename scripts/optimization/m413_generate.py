"""Derive one-layer full-visual quality gate; retain old sources unchanged."""
import ast
from m351_workflow import HERE, BASE, atomic, encoded, sha

def main():
    old=(BASE/'candidates/M412-complete-visual-MLP-01/m412_gate.py').read_text(encoding='utf-8')
    v=old.replace('M412','M413').replace('m412','m413')
    changes=[]
    def change(a,b):
        nonlocal v
        if v.count(a)!=1: raise RuntimeError('Anchor differs: '+a[:90])
        v=v.replace(a,b); changes.append((a,b))
    change('complete_mlp_01','layer12_full_visual_01')
    change('--enable-complete-MLP-gate','--enable-layer12-visual-quality')
    change('a.enable_complete_MLP_gate','a.enable_layer12_visual_quality')
    change("gate_level='isolated-complete-visual-MLP'", "gate_level='layer12-full-visual-feature-quality'")
    change("owner=runtime=mlp=layer=x=binding=cap=lock=None", "owner=runtime=mlp=layer=x=binding=cap=lock=checks=None; visual_a=visual_b=None")
    change("r.update(admission_policy=None,DMA_allocator_restored=False,DMA_sealed_after_main=False,PS_checkpoints=[])",
           "r.update(admission_policy=None,DMA_allocator_restored=False,DMA_sealed_after_main=False,PS_checkpoints=[],selected_layers=[12],semantic_quality_proven=False,feature_quality_pass=False)")
    change("from frozen_video_identity import module_paths,verify_m277_release_subset", "from frozen_video_identity import module_paths,verify_m277_release_subset,FRAMES,ADDON,STACK_SHA")
    change("from m273_latest_vision_runtime import M273LatestPSVisionRuntime", "from m273_latest_vision_runtime import M273LatestPSVisionRuntime\n        from m273_latest_multiscale_contract import preprocess\n        from m413_quality import tensor,visual_quality,VisualChecks")
    change('from m413_quality import tensor,visual_quality,VisualChecks','from m413_quality import tensor,visual_quality,VisualChecks,save_features')
    change('from test_m411_binding import component','from test_m413_quality import component')
    change("r['component']=component(ROOT,OUTPUT.parent)","r['component']=component(ROOT)")
    change('from m207_ps_vision_runtime import M207FP32GemmW4Linear','import contract_runtime\n        from m207_ps_vision_runtime import M207FP32GemmW4Linear')
    change("r['prior_chain_sha256']=plan['chain_raw_sha256'];r['package_verified']=True", """r['prior_chain_sha256']=plan['chain_raw_sha256'];r['package_verified']=True
        if digest(Path(plan['previous_local_result']))!=plan['previous_local_raw_sha256']:raise RuntimeError('Complete M412 result SHA differs')
        local_prior=json.loads(Path(plan['previous_local_result']).read_bytes())
        if local_prior['status']!='PASS_M412_COMPLETE_MLP_NET_GAIN' or not local_prior['numerical_pass'] or not local_prior['performance_pass'] or not local_prior['stable_restored']:raise RuntimeError('Complete M412 prerequisite rejected')
        r['prior_complete_MLP_sha256']=plan['previous_local_raw_sha256']""")
    change("before=proc();r['memory_before_constructor']=before", """frames=[]
        for name,expected_sha in FRAMES.items():
            path=ADDON/'fixtures'/name
            if digest(path)!=expected_sha:raise RuntimeError('Fixed source frame differs')
            frames.append(np.load(path,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Original ordered frame stack differs')
        tensors=preprocess(np.ascontiguousarray(frames[-1:]))
        expected_visual=json.loads((Path(plan['reference_package'])/'EXPECTED.json').read_bytes())
        r['preprocessed']={k:tensor(v) for k,v in sorted(tensors.items())}
        if r['preprocessed']!=expected_visual['preprocessed']:raise RuntimeError('Complete original preprocess differs')
        del frames
        before=proc();r['memory_before_constructor']=before""")
    change("frames=[]\n        for name,expected_sha", """identities={row['path']:row for row in ids['files']};r['resolved_modules']={}
        for name in ('ps_vision_runtime','m206_ps_vision_runtime','m207_ps_vision_runtime','m222_vectorized_w4_runtime','m258_vectorized_w4_runtime','m259_variable_vision_runtime','m260_cached_w4_runtime','m261_budgeted_w4_runtime','m273_latest_vision_runtime','m273_latest_multiscale_contract','contract_runtime'):
            path=Path(sys.modules[name].__file__).resolve();relative=path.relative_to(ROOT).as_posix()
            if digest(path)!=identities[relative]['sha256']:raise RuntimeError('Resolved frozen module differs:'+name)
            r['resolved_modules'][name]=dict(path=relative,sha256=identities[relative]['sha256'])
        frames=[]
        for name,expected_sha""")
    change("(1<<30)+(256<<20)+(64<<20)","(1<<30)+(768<<20)+(64<<20)")
    change("mlp=layer.mlp;x=torch.from_numpy(original['input']).unsqueeze(0);r['backend_before']=backend_evidence(torch)", "mlp=layer.mlp;r['backend_before']=backend_evidence(torch)")
    change("r['PL_rows'].append(dict(part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw)));return raw", "r['PL_rows'].append(dict(part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw),completed_snapshot=s,packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()));return raw")
    a=v.index('        with torch.inference_mode():\n');b=v.index("        if r['backend_before']!=r['backend_after']",a)
    oldblock=v[a:b]
    newblock="""        with torch.inference_mode():
            phase[0]='original-full-visual';r['visual_forward_calls']+=1
            r['PS_checkpoints'].append(budget.check('before-original-full-visual'))
            with VisualChecks(runtime.vision,budget,r['PS_checkpoints'],phase) as checks:
                with Capture(mlp,norm=layer.layer_norm2) as cap:
                    tick=time.perf_counter_ns()
                    visual_a=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
                    r['original_visual_elapsed_ns_diagnostic']=time.perf_counter_ns()-tick
            cap.require_complete();restored.extend([cap.restored,checks.restored])
            r['original_visual']=tensor(visual_a)
            if r['original_visual']!=expected_visual['visual']:raise RuntimeError('Original complete visual SHA differs')
            if any(not np.array_equal(cap.values[k].view(np.uint32),original[k].view(np.uint32)) for k in original):raise RuntimeError('Original layer12 real input/capture differs')
            r['original_layer12_capture']={k:tensor(v) for k,v in cap.values.items()}
            r['original_reference_pass']=True
            r['PS_checkpoints'].append(budget.check('after-original-full-visual'))
            print('M413_ORIGINAL_FULL_VISUAL_REFERENCE_PASS',flush=True)
            cap=checks=None
            phase[0]='layer12-PL-full-visual';r['visual_forward_calls']+=1
            r['PS_checkpoints'].append(budget.check('before-layer12-PL-full-visual'))
            binding=PLMLPBinding(torch,mlp,chains,initial,host,stage,owner.submit,expected)
            with VisualChecks(runtime.vision,budget,r['PS_checkpoints'],phase) as checks:
                with Capture(mlp,norm=layer.layer_norm2) as cap:
                    with binding:
                        tick=time.perf_counter_ns()
                        visual_b=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
                        r['candidate_visual_elapsed_ns_diagnostic']=time.perf_counter_ns()-tick
            cap.require_complete();restored.extend([cap.restored,binding.restored,checks.restored])
            if not np.array_equal(cap.values['residual'].view(np.uint32),original['residual'].view(np.uint32)):raise RuntimeError('Unchanged preMLP path differs')
            if any(not np.array_equal(cap.values[k].view(np.uint32),candidate[k].view(np.uint32)) for k in candidate):raise RuntimeError('Integrated complete actual PL software reference differs')
            r['candidate_layer12_capture']={k:tensor(v) for k,v in cap.values.items()}
            r['numerical_batches']=binding.batches;r['full_wire_reference_batches_exact']=26
            r['quality_metrics'],local_quality=compare(original,cap.values)
            r['candidate_visual']=tensor(visual_b)
            r['retained_visual_features']=save_features(OUTPUT.parent,dict(original=visual_a,candidate=visual_b))
            r['full_visual_quality']=visual_quality(visual_a,visual_b)
            r['feature_quality_pass']=r['full_visual_quality']['feature_screen_pass']
            r['PS_checkpoints'].append(budget.check('after-layer12-PL-full-visual'))
            if not local_quality or not r['feature_quality_pass']:raise RuntimeError('Predeclared complete visual feature quality screen rejected')
            r['numerical_pass']=True
            print('M413_COMPLETE_VISUAL_FEATURE_QUALITY_PASS '+json.dumps(r['full_visual_quality']),flush=True)
        r['backend_after']=backend_evidence(torch)
        r['CPU_store_after']=mlp.fc1.store.evidence()
        if r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=142:raise RuntimeError('Original full visual72 plus selected-layer candidate70 CPU restores differ')
        if time.monotonic()-started>840:raise RuntimeError('Bounded quality gate expired; no additional run')
"""
    v=v[:a]+newblock+v[b:];changes.append((oldblock,newblock))
    change("r['bindings_restored']=all(restored);owner.release();sealed_ids=None;binding=cap=mlp=layer=x=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None", "r['bindings_restored']=all(restored);owner.release();sealed_ids=None;binding=cap=checks=mlp=layer=x=None;visual_a=visual_b=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None")
    change("r['status']='PASS_M413_COMPLETE_MLP_NET_GAIN' if r['performance_pass'] else 'CLOSED_M413_COMPLETE_MLP_NO_RELIABLE_NET_GAIN'", "r['status']='PASS_M413_LAYER12_FULL_VISUAL_FEATURE_QUALITY'")
    change("if cap is not None and cap.handles:cap.__exit__(None,None,None)", "if cap is not None and cap.handles:cap.__exit__(None,None,None)\n        if checks is not None and checks.handles:checks.__exit__(None,None,None)")
    change("binding=cap=mlp=layer=x=None\n                if runtime", "binding=cap=checks=mlp=layer=x=None;visual_a=visual_b=None\n                if runtime")
    restored=v
    for a,b in reversed(changes):
        if restored.count(b)!=1:raise RuntimeError('Inverse anchor not unique')
        restored=restored.replace(b,a)
    expected=old.replace('M412','M413').replace('m412','m413')
    assert ast.dump(ast.parse(restored))==ast.dump(ast.parse(expected))
    ast.parse(v,feature_version=(3,10));atomic(HERE/'m413_gate.py',v.encode('utf-8'))
    policy=(HERE/'m412_policy.py').read_text(encoding='utf-8').replace('M412','M413').replace('256 << 20','768 << 20')
    atomic(HERE/'m413_policy.py',policy.encode('utf-8'))
    export=(HERE/'m412_export.py').read_text(encoding='utf-8').replace('m412_complete_mlp_01','m413_layer12_full_visual_01').replace('M412','M413').replace('isolated-complete-visual-MLP','layer12-full-visual-feature-quality')
    atomic(HERE/'m413_export.py',export.encode('utf-8'))
    atomic(BASE/'runs/M413-source-diff-03/RESULT.json',encoded(dict(status='PASS_M413_INVERSE_AST_DIFF',original_gate_sha256=sha(BASE/'candidates/M412-complete-visual-MLP-01/m412_gate.py'),derived_sha256=sha(HERE/'m413_gate.py'),changes=len(changes),original_PL_binding_unchanged=True)),immutable=True)
    print('M413_GATE_GENERATED',len(changes),sha(HERE/'m413_gate.py'))

if __name__=='__main__':main()
