"""Prepare reviewable video diagnostic source; freeze only after M367 PASS."""
import ast
import json
import m351_workflow as w


def replace(text,before,after):
    if text.count(before)!=1:raise RuntimeError('Draft edit anchor differs: '+before[:100])
    return text.replace(before,after,1)


def main():
    old=w.BASE/'candidates/M366-staged-text-03'
    text=(old/'m366_staged_text_gate.py').read_text(encoding='utf-8').replace('M366','M368').replace('m366','m368').replace('m368_staged_text_02','m368_staged_video_01')
    text=text.replace('independent-fixed-text-capacity-diagnostic','independent-fixed159-video-capacity-diagnostic').replace('enable-staged-layer','enable-staged-video').replace('enable_staged_layer','enable_staged_video')
    text=replace(text,"from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, RELEASE","from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, RELEASE,FRAMES,STACK_SHA\nfrom types import SimpleNamespace\nfrom m368_video_contract import tensor,check_call_contract,validate_stream")
    text=replace(text,"from m368_stage_policy import StagePolicy,SHAPES","from m368_stage_policy import StagePolicy,SHAPES")
    text=text.replace('original fixed30-token','original fixed159-token').replace('Original fixed30-token','Original fixed159-token')
    text=text.replace('independent fixed30-token','independent fixed159-token')
    text=replace(text,"if prior['status']!='PASS_ONE_LAYER_UNDER_INDEPENDENT_POLICY' or prior['raw_sha256']!='54261095541d69f53179f410df76640302e1f146714c52dc8e4ed52274c2771a':raise RuntimeError('Independent layer prerequisite differs')", "if prior['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prior['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Independent text prerequisite differs')\n        visual_reference=json.loads((HERE/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))\n        if visual_reference['status']!='PASS_MISSING_PS_VISUAL_REFERENCE' or visual_reference['gate_return_code'] or visual_reference['fpga_transactions'] or visual_reference['language_forward_calls']:raise RuntimeError('Missing-only visual reference prerequisite differs')")
    text=replace(text,"        patch(base,'BUILD_ID',int(TARGET_BUILD,16))", "        patch(base,'BUILD_ID',int(TARGET_BUILD,16))\n        patch(video_server,'BUILD_ID',TARGET_BUILD)")
    before="""                # Block the Torch tower too, while leaving construction intact.
                self.vision.forward = forbid('vision.tower.forward',blocked)
                mark('after-original-PS-vision-constructor')
            __call__ = forbid('vision.__call__',blocked)"""
    after="""                mark('after-original-PS-vision-constructor')
            def __call__(self,*a,**kw):
                if result.get('vision_forward_calls',0):raise RuntimeError('Unexpected second visual forward')
                result['vision_forward_calls']=1
                policy.capture('before-original-visual-forward',True)
                visual=super().__call__(*a,**kw)
                policy.capture('after-original-visual-forward',True)
                result['visual_features']=tensor(visual)
                return visual"""
    text=replace(text,before,after)
    text=replace(text,"        engine.stream = forbid('engine.stream',blocked)", "        # Original M276 stream executes only the frozen request below.")
    text=replace(text,"        result['diagnostic_ps_growth_limit_bytes']=256<<20","        result['diagnostic_ps_growth_limit_bytes']=1024<<20")
    start=text.index("        expected=json.loads((HERE/'LAYER_EXPECTED.json')")
    end=text.index("        result['boot_unchanged']=",start)
    text=text[:start]+'''        expected=json.loads((HERE/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))
        frames=[]
        for name,digest in FRAMES.items():
            file=ADDON/'fixtures'/name
            if sha256(file)!=digest:raise RuntimeError('Frozen video file identity differs')
            frames.append(np.load(file,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Frozen frame tensor differs')
        result['frames_sha256']=STACK_SHA
        model=engine.language;families=[];captured={};original_family=model._family
        def observed_family(layer,name,values):
            if len(families)>=len(FAMILIES) or (layer,name)!=FAMILIES[len(families)]:raise RuntimeError('Video family sequence escaped')
            if name in ('q','qkv'):print('M368_LAYER '+str(layer),flush=True)
            policy.capture('before-family:'+str(layer)+':'+name,True)
            output=original_family(layer,name,values)
            policy.capture('after-family:'+str(layer)+':'+name,True)
            families.append(dict(layer=layer,family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(output.items())}))
            return output
        patch(model,'_family',observed_family)
        original_prefill=model.prefill
        def observed_prefill(hidden):
            if captured:raise RuntimeError('Unexpected second prefill')
            captured['input']=tensor(hidden)
            if captured['input']!=expected['baseline']['input'] or hidden.shape!=(159,2560):raise RuntimeError('Original159 video input differs')
            policy.capture('before-language-prefill',True)
            result['model_forward_calls']=1
            output=original_prefill(hidden)
            policy.capture('after-language-prefill-and-head',True)
            captured['output']=output
            return output
        patch(model,'prefill',observed_prefill)
        original_preprocess=m276_video_runtime.preprocess
        def observed_preprocess(frames):
            answer=original_preprocess(frames)
            result['preprocessed']={k:tensor(v) for k,v in sorted(answer.items())}
            if result['preprocessed']!=visual_reference['preprocessed']:raise RuntimeError('Frozen preprocessing reference differs')
            policy.capture('after-preprocess',True)
            return answer
        patch(m276_video_runtime,'preprocess',observed_preprocess)
        original_tokenize=m276_video_runtime.tokenize
        def observed_tokenize(*a,**kw):
            ids=original_tokenize(*a,**kw)
            if ids!=visual_reference['prompt_token_ids']:raise RuntimeError('Exact159 token identities differ')
            result['prompt_token_ids']=ids
            return ids
        patch(m276_video_runtime,'tokenize',observed_tokenize)
        # Loader-only reuse is complete; original request tokenization remains original.
        patch(tokenizers,'Tokenizer',original_tokenizer)
        original_progress=engine.vision.progress_callback if hasattr(engine.vision,'progress_callback') else None
        for wrapped in engine.vision.vision.encoder.layers:
            callback=wrapped.progress_callback
            def memory_progress(name,payload,_original=callback):
                if _original is not None:_original(name,payload)
                policy.capture('vision:'+name+':'+str(payload.get('index')),True)
            patch(wrapped,'progress_callback',memory_progress)
        request=SimpleNamespace(prompt=m276_video_runtime.M276_KNIFE_PROMPT,max_new_tokens=1,frames_rgb_u8=frames)
        policy.capture('before-original-video-stream',True);policy.begin_sampling()
        events=[]
        for event,payload in engine.stream(request):
            events.append((event,payload))
            if event=='stage':policy.capture('stream-stage:'+payload['name'],True)
            print('M368_EVENT '+event,flush=True)
        policy.capture('after-original-video-stream',True);policy.stop_sampling()
        token,logits,kv=captured['output'];evidence=runtime.evidence()
        row=dict(input=captured['input'],families=families,token=token,logits=tensor(logits),grouped_attention_calls=model.grouped_attention_calls,keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values],logical_calls=evidence['logical_calls'],host_calls=evidence['host_calls'],retry_count=evidence['scale_retry_count'],retry_launches=evidence['pipeline_retry_launches'],nonfinite_detections=evidence['fused_nonfinite_detections'],scale_attempts=evidence['scale_attempts'],stage_bytes=evidence['stage_bytes'],logical_expected_macros=evidence['logical_expected_macros'],expected_macros=evidence['expected_macros'])
        check_call_contract(row,expected['baseline']['logical_expected_macros'])
        result['decoder']=engine.vision.decoder_evidence()
        semantic=validate_stream(events,result['decoder'],TARGET_BUILD)
        stable_semantic=dict(semantic,proof=dict(semantic['proof'],build_id='0x4D395832'))
        # Only explicit expected Build identity is normalized for reference comparison.
        stable_semantic['proof']['build_id']=expected['baseline']['semantic']['proof']['build_id']
        row['semantic']=stable_semantic
        result['events']=events;result['candidate_semantic']=semantic;result['video_result']=row
        result['exact_comparison']={key:row[key]==expected['baseline'][key] for key in row}
        result['visual_exact_comparison']=dict(features=result['visual_features']==visual_reference['visual_features'],preprocessed=result['preprocessed']==visual_reference['preprocessed'],ids=result['prompt_token_ids']==visual_reference['prompt_token_ids'])
        if not all(result['exact_comparison'].values()) or not all(result['visual_exact_comparison'].values()):raise RuntimeError('Frozen video visual/family/KV/logits/decision/retry reference differs')
        if row['logical_calls']!=778 or len(families)!=154 or token!=15 or len(kv.keys)!=36 or len(kv.values)!=36 or logits.shape!=(151936,):raise RuntimeError('Incomplete actual159 video')
        if row['host_calls']!=len(result['transactions']):raise RuntimeError('Physical launch accounting differs')
        result['numerical_pass']=True;result['fixed_video_diagnostic_pass']=True
        result['status']='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'
        result['memory_capacity_proven']=False
''' +text[end:]
    text=text.replace('PASS_M368_FIXED_TEXT_DIAGNOSTIC','PASS_M368_FIXED_VIDEO_DIAGNOSTIC')
    text=text.replace('elapsed > 600','elapsed > 900').replace("performance'] > 600", "performance'] > 900")
    text=text.replace('Independent fixed-text adjudication, then separately freeze real159-video capacity rules; no video/performance unlocked automatically','Independent video adjudication; balanced full-request performance only after exact output and lifecycle PASS synchronized')
    text=text.replace('no extra CMA/PS slot or visual forward; production policy unchanged','no extra CMA/PS slot; original visual plus language and head; production policy unchanged')
    text=text.replace('Independent fixed-text capacity diagnostic; production admission unchanged.','Independent actual159 video capacity diagnostic; production admission unchanged.')
    ast.parse(text,feature_version=(3,10))
    policy=(old/'m366_stage_policy.py').read_text(encoding='utf-8').replace('m366','m368').replace('PS_GROWTH_LIMIT=256*MIB','PS_GROWTH_LIMIT=1024*MIB').replace('exceeded256MiB','exceeded1024MiB').replace('>240:', '>420:').replace('Fixed-text soft budget exceeded240s','Video soft budget exceeded420s')
    ast.parse(policy,feature_version=(3,10))
    original=(w.HERE/'m345_fixed_video_gate.py').read_text(encoding='utf-8');tree=ast.parse(original)
    functions=[ast.get_source_segment(original,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('tensor','check_call_contract','validate_stream')]
    contract='import hashlib\nimport numpy as np\n\n'+'\n\n'.join(functions)+'\n'
    contract=replace(contract,'def validate_stream(events, decoder):','def validate_stream(events, decoder,expected_build):')
    contract=replace(contract,"== '0x4d395832'","== expected_build.lower()")
    ast.parse(contract,feature_version=(3,10))
    for name,value in [('m368_staged_video_gate.py',text),('m368_stage_policy.py',policy),('m368_video_contract.py',contract)]:w.atomic(w.HERE/name,value.encode('utf-8'))
    print(json.dumps(dict(status='DRAFT_VIDEO_SOURCE_NOT_FROZEN',python310_syntax=True,full_video_PS_growth_bytes=1024<<20,logical_calls=778,extra_CMA=0,missing_visual_reference_required=True,uploaded=False,executed=False)))


if __name__=='__main__':main()
