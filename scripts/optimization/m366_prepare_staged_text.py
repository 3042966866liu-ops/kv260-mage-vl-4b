"""Freeze a distinct full fixed-text capacity diagnostic after M365 closure."""
import ast
import json
import shutil
import symtable
import m351_workflow as w
from m358_prepare_capacity import replace_once as rep

PKG=w.BASE/'candidates/M366-staged-text-02'


def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    prior=w.BASE/'runs/M365-staged-layer-closure-01/RESULT.json'
    pr=json.loads(prior.read_text(encoding='utf-8'))
    assert pr['status']=='PASS_ONE_LAYER_UNDER_INDEPENDENT_POLICY'
    assert all(w.sha(prior) in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    old=w.BASE/'candidates/M365-staged-layer-03'
    text=(old/'m365_staged_layer_gate.py').read_text(encoding='utf-8')
    text=text.replace('M365','M366').replace('m365','m366').replace('m366_staged_layer_02','m366_staged_text_01')
    edits=[
        ("BLOCKED_BOARD_METHODS = ('lm_head',)","BLOCKED_BOARD_METHODS = ()"),
        ("for name in ('prefill','decode')", "for name in ('decode',)"),
        ("gate_level='independent-single-layer-capacity-diagnostic'","gate_level='independent-fixed-text-capacity-diagnostic'"),
        ('from m343_layer_scope import bind',''),
        ("if runtime.host_calls or runtime.logical_calls: raise RuntimeError('Unexpected prior transaction')", "if runtime.host_calls or runtime.logical_calls: raise RuntimeError('Unexpected prior transaction')"),
        ("hidden=np.tile(np.stack([selected_rows[contract['selected_embedding_ids'].index(t)] for t in contract['prompt_token_ids']]),(6,1))[:159].copy()", "hidden=np.stack([selected_rows[contract['selected_embedding_ids'].index(t)] for t in contract['prompt_token_ids']]).copy()"),
        ("        one_layer=bind(sys.modules['m241_video_language_runtime'],(HERE/'frozen_one_layer.py').read_text(encoding='utf-8'))\n", ""),
        ("if layer!=0 or len(families)>=5 or name!=FAMILIES[len(families)]:raise RuntimeError('Layer0 family sequence escaped')", "if len(families)>=len(FAMILIES) or (layer,name)!=FAMILIES[len(families)]:raise RuntimeError('Fixed-text family sequence escaped')"),
        ("print('M366_FAMILY '+name,flush=True)","print('M366_FAMILY layer='+str(layer)+' '+name,flush=True)"),
        ("families.append(dict(family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(output.items())}))", "families.append(dict(layer=layer,family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(output.items())}))"),
        ('before-layer0','before-fixed-text'),('after-layer0','after-fixed-text'),
        ("output,kv=one_layer(model,hidden.copy())", "token,logits,kv=model.prefill(hidden.copy())"),
        ("families=families,hidden=tensor(output)", "families=families,token=token,logits=tensor(logits),grouped_attention_calls=model.grouped_attention_calls"),
        ("stage_bytes=evidence['stage_bytes'])", "stage_bytes=evidence['stage_bytes'],logical_expected_macros=evidence['logical_expected_macros'],expected_macros=evidence['expected_macros'])"),
        ("result['layer_result']['logical_calls']!=25 or len(families)!=5", "result['layer_result']['logical_calls']!=162 or len(families)!=154 or token!=17 or len(kv.keys)!=36 or len(kv.values)!=36 or logits.shape!=(151936,)"),
        ('PASS_M366_SINGLE_LAYER_DIAGNOSTIC','PASS_M366_FIXED_TEXT_DIAGNOSTIC'),
        ('single_layer_diagnostic_pass','fixed_text_diagnostic_pass'),
        ('One original layer0 on159 repeated fixed-text embeddings with full runtime objects retained; no visual forward/LM head/full-model/video/performance','Original fixed30-token full36-layer Prefill and full LM head with complete runtime objects retained; no visual forward/actual video/performance'),
        ('independent one-layer diagnostic, no extra CMA/PS slot or vision/LMhead/multi-layer; production policy unchanged','independent fixed30-token diagnostic including36 layers/head, no extra CMA/PS slot or visual forward; production policy unchanged'),
        ('Independent layer adjudication then separately freeze fixed-text admission; no full-model/video/performance unlocked automatically','Independent fixed-text adjudication, then separately freeze real159-video capacity rules; no video/performance unlocked automatically'),
    ]
    for before,after in edits:
        if before==after:continue
        if before in ('before-layer0','after-layer0','PASS_M366_SINGLE_LAYER_DIAGNOSTIC'):text=text.replace(before,after)
        else:text=rep(text,before,after)
    text=text.replace('Independent layer0 capacity diagnostic; production admission unchanged.','Independent fixed-text capacity diagnostic; production admission unchanged.')
    assert 'one_layer(' not in text and 'layer0' not in text
    # Gate admission binds the exact preceding board/closure bytes before imports.
    needle="        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha"
    assert needle in text
    text=rep(text,needle,needle+"\n        prior=json.loads((HERE/'STAGE_PREREQUISITE.json').read_text(encoding='utf-8'))\n        if prior['status']!='PASS_ONE_LAYER_UNDER_INDEPENDENT_POLICY' or prior['raw_sha256']!='54261095541d69f53179f410df76640302e1f146714c52dc8e4ed52274c2771a':raise RuntimeError('Independent layer prerequisite differs')")
    tree=ast.parse(text,feature_version=(3,10))
    main_symbols=next(t for t in symtable.symtable(text,'text_gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in main_symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    policy=(old/'m365_stage_policy.py').read_text(encoding='utf-8').replace('m365','m366')
    policy=rep(policy,"FAMILIES=['q','kv','attention_out','gate_up','mlp_down']", "FAMILIES=[(layer,family) for layer in range(36) for family in (('q','kv','attention_out','gate_up','mlp_down') if layer<10 else ('qkv','attention_out','gate_up','mlp_down'))]")
    policy=rep(policy,"if chain.get('layer')!=0 or chain.get('family') not in FAMILIES:raise RuntimeError('Single-layer scope escaped')", "if (chain.get('layer'),chain.get('family')) not in FAMILIES and not (chain.get('layer') is None and chain.get('family')=='lm_head'):raise RuntimeError('Fixed-text scope escaped')")
    policy=policy.replace('>120:', '>240:').replace('Single-layer soft budget exceeded120s','Fixed-text soft budget exceeded240s')
    raw=w.BASE/'runs/M344-fixed-text-board-01/BOARD_RESULT.json'
    reference=json.loads(raw.read_text(encoding='utf-8'))
    assert w.sha(raw)=='897bb817d6bd2a12f5de5437bb015541210f86c297c85456bc570586d479673a' and reference['status']=='PASS'
    baseline=reference['passes'][0]
    keys=('families','token','logits','keys','values','grouped_attention_calls','logical_calls','host_calls','retry_count','retry_launches','nonfinite_detections','scale_attempts','stage_bytes','logical_expected_macros','expected_macros')
    contract=json.loads((w.BASE/'candidates/M344-fixed-text-01/INPUT_CONTRACT.json').read_text(encoding='utf-8'))
    assert len(contract['prompt_token_ids'])==30 and baseline['token']==17 and len(baseline['families'])==154
    PKG.mkdir(parents=True)
    excluded={'PACKAGE_MANIFEST.json','SHA256SUMS','m365_staged_layer_gate.py','m365_stage_policy.py','m365_export_result.py','run_m365_staged_layer.sh','LAYER_EXPECTED.json','frozen_one_layer.py','m343_layer_scope.py','m365_assemble.py'}
    for path in old.iterdir():
        if path.name not in excluded:shutil.copyfile(path,PKG/path.name)
    w.atomic(PKG/'m366_staged_text_gate.py',text.encode('utf-8'))
    w.atomic(PKG/'m366_stage_policy.py',policy.encode('utf-8'))
    w.atomic(PKG/'m366_assemble.py',(old/'m365_assemble.py').read_text(encoding='utf-8').replace('M365','M366').encode('utf-8'))
    w.atomic(PKG/'LAYER_EXPECTED.json',w.encoded(dict(prior_reference_raw_sha256=w.sha(raw),input_contract=contract,baseline={k:baseline[k] for k in keys})))
    shutil.copyfile(prior,PKG/'STAGE_PREREQUISITE.json')
    for original,new in [('m365_export_result.py','m366_export_result.py'),('run_m365_staged_layer.sh','run_m366_staged_text.sh')]:
        value=(old/original).read_text(encoding='utf-8').replace('M365','M366').replace('m365','m366').replace('m366_staged_layer_02','m366_staged_text_01').replace('m366_staged_layer_gate.py','m366_staged_text_gate.py').replace('independent-single-layer-capacity-diagnostic','independent-fixed-text-capacity-diagnostic')
        w.atomic(PKG/new,value.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m366-independent-fixed-text-capacity-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    result=dict(status='DRAFT_FIXED_TEXT_DIAGNOSTIC_PENDING_SUPPORT',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prior_layer_closure_sha256=w.sha(prior),stable_text_reference_sha256=w.sha(raw),production_policy_changed=False,explicit_extra_cma_requests=0,ps_growth_budget_bytes=256<<20,ps_available_margin_bytes=64<<20,known_payloads_bytes=dict(full36layer_KV=36*2*30*1024*4,gate_up_two_arrays=2*30*9728*4,full_logits=151936*4,attention_two_score_matrices=2*4*30*30*4),native_total_peak_certified=False,board_executed=False)
    out=w.BASE/'runs/M366-staged-text-preparation-02/RESULT.json';w.atomic(out,w.encoded(result),immutable=True)
    print(json.dumps(result))


if __name__=='__main__':main()
