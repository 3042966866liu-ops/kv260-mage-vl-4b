"""Saved M420 features only; derivative of actually passed M415 packet04."""
import ast,json,re
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OLD=BASE/'candidates/M415-saved-feature-language-04'
PKG=BASE/'candidates/M421-combination-saved-language-01'

def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('Derivation anchor differs: '+a[:100])
    return s.replace(a,b)

def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),characters=len((ROOT/n).read_text(encoding='utf-8-sig'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior={}
    for key in ('latest_m420_combination_board','latest_m420_combination_closure','latest_m415_saved_feature_language_board','latest_m415_saved_feature_language_closure','latest_m368_video_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prior[key]=row
    source=json.loads((ROOT/prior['latest_m420_combination_board']['result']).read_bytes())
    assert source['status']=='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY' and source['gate_return_code']==0 and source['feature_quality_pass'] and source['safe_buffers_released'] and source['stable_restored']
    assert source['selected_layers']==[12,13] and source['language_forward_calls']==0
    passed=json.loads((ROOT/prior['latest_m415_saved_feature_language_board']['result']).read_bytes());assert passed['status']=='PASS_M415_SAVED_FEATURE_DECISION_CONSISTENCY' and not passed['gate_return_code']
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    assert prior['latest_m415_saved_feature_language_board']['manifest_sha256']==sha(OLD/'PACKAGE_MANIFEST.json')
    for row in manifest['files']:assert (OLD/row['path']).stat().st_size==row['bytes'] and sha(OLD/row['path'])==row['sha256']
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan.pop('M414_raw_sha256')
    plan.update(prerequisites=prior,M420_raw_sha256=prior['latest_m420_combination_board']['sha256'],features=source['retained_visual_features'],feature_directory='/home/ubuntu/m420_combination_visual_02',selected_layers=[12,13],variants=['original','layer12_13_candidate'])
    assert [x['path'] for x in plan['features']]==['original_visual.npy','candidate_visual.npy']
    texts={}
    for name in ('m415_gate.py','m415_trials.py','m415_export.py'):
        s=(OLD/name).read_text(encoding='utf-8').replace('m415','m421').replace('M415','M421').replace('layer12_candidate','layer12_13_candidate').replace('m421_saved_feature_language_03','m421_saved_feature_language_01')
        s=s.replace('original-then-layer12','original-then-layers12-13')
        texts[name.replace('415','421')]=s
    helper=(OLD/'m415_saved_features.py').read_text(encoding='utf-8')
    helper=once(helper,"M414_SHA='5733f75049b8bee7aae6da9d8a1cdc451416a637d5a4e7b28c617aa767043408'",'')
    helper=once(helper,"FEATURE_DIR=Path('/home/ubuntu/m414_layer12_full_visual_01')","FEATURE_DIR=Path('/home/ubuntu/m420_combination_visual_02')")
    helper=once(helper,"if hashlib.sha256(raw).hexdigest()!=M414_SHA or plan['M414_raw_sha256']!=M414_SHA:raise ValueError('M414 identity differs')","if hashlib.sha256(raw).hexdigest()!=plan['M420_raw_sha256']:raise ValueError('M420 identity differs')")
    helper=once(helper,"if r['status']!='PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY' or not r['feature_quality_pass'] or r['gate_return_code']:raise ValueError('M414 quality prerequisite differs')","if r['status']!='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY' or r['feature_quality_pass'] is not True or type(r['gate_return_code']) is not int or r['gate_return_code']!=0 or r['selected_layers']!=[12,13] or plan['selected_layers']!=[12,13] or r['safe_buffers_released'] is not True or r['stable_restored'] is not True or r['language_forward_calls']!=0:raise ValueError('M420 quality prerequisite differs')")
    texts['m421_saved_features.py']=helper
    assemble=(OLD/'m415_assemble.py').read_text(encoding='utf-8')
    assemble=once(assemble,"OLD=Path('/home/ubuntu/m415_saved_feature_candidate_03')","OLD=Path('/home/ubuntu/m415_saved_feature_candidate_04')")
    assemble=once(assemble,'139ab88bc170ca10a5c57dbae3f331b0b5fc43e7e00009823a43800cf76fa9e7',sha(OLD/'PACKAGE_MANIFEST.json'))
    texts['m421_assemble.py']=assemble.replace('M415_ASSEMBLY_PASS','M421_ASSEMBLY_PASS')
    texts['run_m421.sh']=(OLD/'run_m415.sh').read_text(encoding='utf-8').replace('m415','m421').replace('M415','M421').replace('m421_saved_feature_language_03','m421_saved_feature_language_01')
    # Preserve the complete numerical executor and post-load Tokenizer restoration.
    original_trials=(OLD/'m415_trials.py').read_text(encoding='utf-8')
    normalized=texts['m421_trials.py'].replace('m421','m415').replace('M421','M415').replace('layer12_13_candidate','layer12_candidate')
    assert ast.dump(ast.parse(normalized))==ast.dump(ast.parse(original_trials))
    g=texts['m421_gate.py'];assert g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")>g.index('engine.load()') and g.index('features,feature_ids=load_features(plan)')<g.index('import pynq')
    texts['m421_gate.py']=once(g,"        result['saved_feature_identities']=feature_ids","        result['saved_feature_identities']=feature_ids\n        result['selected_layers']=plan['selected_layers']\n        result['saved_feature_source_sha256']=plan['M420_raw_sha256']")
    PKG.mkdir()
    changed={row['path'] for row in manifest['files'] if row['path'].startswith('m415') or row['path'] in ('PLAN.json','SHA256SUMS','run_m415.sh')}
    for row in manifest['files']:
        if row['path'] not in changed:atomic(PKG/row['path'],(OLD/row['path']).read_bytes(),immutable=True)
    for name,s in texts.items():
        if name.endswith('.py'):ast.parse(s,feature_version=(3,10))
        atomic(PKG/name,s.encode('utf-8'),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    names=sorted(p.name for p in PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(PKG/n)}  {n}\n' for n in names).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    v=dict(status='PASS_M421_PREPARATION_ONLY',recovery=recovery,prerequisites=prior,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],plan=plan,
        exact_prior_packet_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),unchanged_language_trial_AST_except_names=True,loader_tokenizer_restore_preserved=True,features_checked_before_Overlay=True,actual_visual_calls=0,board_run=False,decision_consistency_pass=False,performance_pass=False,expanded_24_layers=False)
    out=BASE/'runs/M421-saved-language-preparation-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m421_saved_language_preparation',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),f'## M421 两层保存特征接原语言准备（2026-10-06）\n\nSHA {sha(out)}；M420 raw {plan["M420_raw_sha256"]}双层特征、0视觉重算，复用实际M41504成功入口及Tokenizer修复。原语言/量化/完整LM head/159IDs/154family/72KV/778逻辑调用保持；仅特征来源12＋13，全词表与原判定比较，无拟合阈值/准确率/性能/24层扩展。七块原DMA封锁新增，无固定CMA floor，普通PS1024MiB＋64MiB余量不变。未上传执行，组件及严格回收通过才上板。')
    print('M421_PREPARATION_SYNC',sha(out),v['manifest_sha256'],m['file_count'],m['total_bytes'])
if __name__=='__main__':main()
