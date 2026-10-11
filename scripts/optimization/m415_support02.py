"""Preserve passed CPU components; close host output decode and PASS validator."""
import copy,json,math,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m415_workflow as workflow
PKG=workflow.PKG

def main():
    prior=BASE/'runs/M415-saved-feature-support-01/RESULT.json'
    assert sha(prior)=='b6980405f2741f2c27d7a37012119370d9c03cedcd7b533b2fc4b989efc0f37a'
    old=json.loads(prior.read_bytes());assert len(old['components']['negative_checks'])==8 and len(old['recovery_negative_checks'])==13 and old['actual_frozen_head_AST_check'] and old['control_failure_collection_selftest']
    p=PKG/'run_m415.sh'
    completed=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+p.relative_to(ROOT).as_posix()],capture_output=True)
    if completed.returncode:raise RuntimeError((completed.stdout+completed.stderr).decode('utf-8',errors='replace'))
    # Real prior metadata, duplicated only as a declared synthetic validator fixture.
    raw=json.loads((BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json').read_bytes())
    expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())['baseline'];plan=json.loads((PKG/'PLAN.json').read_bytes())
    r=copy.deepcopy(raw);r.update(status='PASS_M415_SAVED_FEATURE_DECISION_CONSISTENCY',gate_level='saved-feature-fixed159-language-quality',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_return_code=0,
        features_verified_before_overlay=True,head_AST_checked_before_overlay=True,original_reference_pass=True,candidate_finite_complete=True,saved_features_unchanged_after=True,numerical_pass=True,decision_consistency_pass=True,
        semantic_accuracy_proven=False,expanded_24_layers=False,model_forward_calls=2,vision_forward_calls=0,decode_calls=0,output_budget=1,selected_frame_indices=[3],views=2,
        prompt='[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:',prompt_token_ids=json.loads((PKG/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids'],original_exact_comparison={'synthetic_original':True},fpga_transactions=1+2*expected['host_calls'],host_calls=2*expected['host_calls'],logical_calls=1556)
    r['transactions']=raw['transactions']*2
    token=expected['semantic']['token'];decision=dict(token_id=token['token_id'],text=token['text'],verdict=token['knife_verdict'],knife_score=token['knife_score'],logit_margin_yes_minus_no=math.log(token['knife_score']/(1-token['knife_score'])))
    counts={k:expected[k] for k in ('logical_calls','host_calls','retry_count','retry_launches','nonfinite_detections','stage_bytes','logical_expected_macros','expected_macros','scale_attempts','language_retries','head_retries')}
    r['samples']=[];r['logit_files']=[]
    for i,name in enumerate(plan['variants']):
        sample={k:expected[k] for k in ('input','families','token','logits','keys','values','grouped_attention_calls')}
        sample.update(variant=name,visual=plan['features'][i]['tensor'],counts=counts,physical_observed=counts['host_calls'],final_snapshot=raw['final_snapshot'],sampled_memory=raw['sampled_memory'],decision=decision)
        r['samples'].append(sample);r['logit_files'].append(dict(path=['original_logits.npy','layer12_candidate_logits.npy'][i],file_bytes=607872,file_sha256='1'*64,tensor=sample['logits']))
    r['logit_comparison']=dict(same_constrained_decision=True,accuracy_proven=False,performance_proven=False,original=decision,candidate=decision,relative_l2=0.,cosine=1.,RMSE=0.,max_abs=0.,knife_score_delta=0.,margin_delta=0.,changed_FP32_words=0)
    workflow.check(r);rejects=[]
    for label in ('original-logits','missing-KV','candidate-shape','logical-calls','physical-accounting','DMA-release','decision','real-visual-call','original-false','head-AST','logit-file','sample-order','unsafe-exit','observer-alive'):
        bad=copy.deepcopy(r)
        if label=='original-logits':bad['samples'][0]['logits']['sha256']='0'*64
        elif label=='missing-KV':bad['samples'][1]['keys'].pop()
        elif label=='candidate-shape':bad['samples'][1]['logits']['shape']=[16]
        elif label=='logical-calls':bad['samples'][1]['counts']['logical_calls']=777
        elif label=='physical-accounting':bad['fpga_transactions']-=1
        elif label=='DMA-release':bad['released_buffers'].pop()
        elif label=='decision':bad['logit_comparison']['same_constrained_decision']=False
        elif label=='real-visual-call':bad['vision_forward_calls']=1
        elif label=='original-false':bad['original_reference_pass']=False
        elif label=='head-AST':bad['head_observer_proof']['removed_observation_calls_ast_equals_original']=False
        elif label=='logit-file':bad['logit_files'][1]['file_bytes']-=1
        elif label=='sample-order':bad['samples'].reverse()
        elif label=='unsafe-exit':bad['final_snapshot']['ap_return']=0
        else:bad['samples'][1]['sampled_memory']['observer_stopped']=False
        try:workflow.check(bad)
        except (ValueError,RuntimeError):rejects.append(label)
        else:raise AssertionError('PASS validator accepted: '+label)
    v=dict(old,status='PASS_M415_SAVED_FEATURE_SUPPORT_WITH_STRICT_PASS_VALIDATOR',prior_support_sha256=sha(prior),CPU_components_reused_not_rerun=True,
           initial_host_WSLOutput_decode_exception_preserved=True,WSL_bash_n_raw_rc=completed.returncode,WSL_stdout_sha256=__import__('hashlib').sha256(completed.stdout).hexdigest(),WSL_stderr_sha256=__import__('hashlib').sha256(completed.stderr).hexdigest(),
           actual_PASS_validator_synthetic_fixture=True,PASS_validator_negative_checks=rejects,
           source_sha256={name:sha(HERE/name) for name in ('m415_saved_features.py','m415_trials.py','m415_workflow.py','m415_control.ps1','m415_support.py','m415_support02.py')})
    out=BASE/'runs/M415-saved-feature-support-02/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),
         f'## M415 回收PASS路径与主机输出解码闭合（2026-10-06）\n\nSHA {sha(out)}；前8组件和13回收负例不重跑，01原SHA {sha(prior)}保留。初次WSL stderr的主机UTF8解码异常保留，改字节捕获bash-n rc0和stdout/stderr SHA；严谨PASS收集器声明合成元数据正常路径及14完整logits/KV/事务/释放/原参考/视觉禁行/observer负例通过。未板端/质量/性能；允许同COM3一次上传执行。')
    print('M415_SUPPORT02_SYNC',sha(out),len(rejects))
if __name__=='__main__':main()
