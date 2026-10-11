"""Bounded CPU fixture tests of actual saved-feature helper and byte collector."""
import ast,base64,copy,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m421_workflow as w

def main():
    pkg=w.PKG;plan=json.loads((pkg/'PLAN.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    rejected=[]
    def reject(label,call):
        try:call()
        except (ValueError,RuntimeError,KeyError,AssertionError,FileNotFoundError):rejected.append(label)
        else:raise AssertionError('Invalid evidence accepted: '+label)
    spec=importlib.util.spec_from_file_location('m421_actual_saved_features',pkg/'m421_saved_features.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
        folder=Path(temp);x=np.linspace(-1,1,98*2560,dtype=np.float32).reshape(98,2560)
        rows=[helper.save_array(folder/name,x+i) for i,name in enumerate(('original_visual.npy','candidate_visual.npy'))]
        raw=dict(status='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY',gate_return_code=0,selected_layers=[12,13],feature_quality_pass=True,safe_buffers_released=True,stable_restored=True,language_forward_calls=0,retained_visual_features=rows)
        (folder/'BOARD_RESULT.json').write_bytes(encoded(raw));fake=dict(plan,features=rows,M420_raw_sha256=sha(folder/'BOARD_RESULT.json'))
        arrays,identities=helper.load_features(fake,folder)
        assert len(arrays)==2 and all(not a.flags.writeable for a in arrays) and np.array_equal(arrays[0],x) and np.array_equal(arrays[1],x+1)
        for key,value in [('status','PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY'),('gate_return_code',True),('gate_return_code',1),('selected_layers',[12]),('feature_quality_pass',False),('safe_buffers_released',False),('stable_restored',False),('language_forward_calls',1)]:
            bad=copy.deepcopy(raw);bad[key]=value;(folder/'BOARD_RESULT.json').write_bytes(encoded(bad));p=dict(fake,M420_raw_sha256=sha(folder/'BOARD_RESULT.json'))
            reject('feature-source-'+key+str(value),lambda p=p:helper.load_features(p,folder))
        (folder/'BOARD_RESULT.json').write_bytes(encoded(raw));reject('feature-source-SHA',lambda:helper.load_features(dict(fake,M420_raw_sha256='0'*64),folder))
        reject('plan-layer-scope',lambda:helper.load_features(dict(fake,selected_layers=[12]),folder))
        p=folder/'candidate_visual.npy';original=p.read_bytes();p.write_bytes(original[:-1]+bytes([original[-1]^1]));reject('feature-file-SHA',lambda:helper.load_features(fake,folder));p.write_bytes(original)
        bad=copy.deepcopy(fake);bad['features'][0]['tensor']['shape']=[1];reject('feature-manifest',lambda:helper.load_features(bad,folder))
    r=json.loads((ROOT/b['latest_m415_saved_feature_language_board']['result']).read_bytes())
    r.update(status='PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY',manifest_sha256=digest,selected_layers=[12,13],saved_feature_source_sha256=plan['M420_raw_sha256'],saved_feature_identities=[dict(path=plan['feature_directory']+'/'+x['path'],file_sha256=x['file_sha256'],tensor=x['tensor']) for x in plan['features']])
    r['samples'][1]['variant']='layer12_13_candidate';r['samples'][1]['visual']=plan['features'][1]['tensor'];r['logit_files'][1]['path']='layer12_13_candidate_logits.npy'
    # Explicit synthetic collection fixture: previous actual language record, new source metadata.
    w.check(r)
    def export(value):
        raw=encoded(value);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M421_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM421_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join(f'M421_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M421_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    text=export(r);assert w.decode(text)[2]==r
    for label in ('wrong-source','scope-layer','original-logits','missing-KV','candidate-shape','logical-count','physical-count','DMA-release','changed-decision','visual-recomputed','tokenizer-restore','head-AST','logit-file','sample-order','unsafe','observer-alive'):
        bad=copy.deepcopy(r)
        if label=='wrong-source':bad['saved_feature_source_sha256']='0'*64
        elif label=='scope-layer':bad['selected_layers']=[12]
        elif label=='original-logits':bad['samples'][0]['logits']['sha256']='0'*64
        elif label=='missing-KV':bad['samples'][1]['values'].pop()
        elif label=='candidate-shape':bad['samples'][1]['logits']['shape']=[1]
        elif label=='logical-count':bad['samples'][1]['counts']['logical_calls']-=1
        elif label=='physical-count':bad['fpga_transactions']-=1
        elif label=='DMA-release':bad['released_buffers'].pop()
        elif label=='changed-decision':bad['logit_comparison']['same_constrained_decision']=False
        elif label=='visual-recomputed':bad['vision_forward_calls']=1
        elif label=='tokenizer-restore':bad['request_tokenizer_restored_before_prefill']=False
        elif label=='head-AST':bad['head_observer_proof']['removed_observation_calls_ast_equals_original']=False
        elif label=='logit-file':bad['logit_files'][1]['file_bytes']-=1
        elif label=='sample-order':bad['samples'].reverse()
        elif label=='unsafe':bad['final_snapshot']['ap_return']=0
        else:bad['samples'][1]['sampled_memory']['observer_stopped']=False
        reject('collector-'+label,lambda bad=bad:w.check(bad))
    for label,t in [('truncated',text[:text.index('M421_RESULT_CHUNK=1/')]),('duplicate',text+text),('wrong-rc',text.replace('M421_SAVED_GATE_RC=0','M421_SAVED_GATE_RC=1')),('wrong-export',text.replace('export_rc=0','export_rc=1')),('unordered',text.replace('M421_RESULT_CHUNK=1/','M421_RESULT_CHUNK=0/')),('wrong-hash',text.replace(hashlib.sha256(encoded(r)).hexdigest(),'0'*64))]:reject(label,lambda t=t:w.decode(t))
    failure=dict(r,status='FAIL',errors=['EXPLICIT synthetic source failure'],gate_return_code=1,features_verified_before_overlay=False,overlay_loaded=False,model_forward_calls=0)
    assert w.decode(export(failure))[2]==failure
    g=(pkg/'m421_gate.py').read_text(encoding='utf-8')
    assert g.index('load_features(plan)')<g.index('import pynq')<g.index('engine.load()')<g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")<g.index('from m421_trials import run')
    assert 'Same-terminal root required' in g and 'Allocator sealed: extra DMA allocation refused' in g
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    ps=Path('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe')
    cp=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m421_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert cp.returncode==0 and b'M421_CONTROL_SELF_TEST_PASS' in cp.stdout,(cp.stdout,cp.stderr)
    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m421.sh').relative_to(ROOT).as_posix()],capture_output=True)
    assert bash.returncode==0,(bash.stdout,bash.stderr)
    v=dict(status='PASS_M421_SAVED_LANGUAGE_SUPPORT_ONLY',manifest_sha256=digest,negative_checks=rejected,real_size_numpy_fixture=True,synthetic_collector_fixture=True,prior_actual_language_raw_sha256=b['latest_m415_saved_feature_language_board']['sha256'],complete_original_language_trial_AST_reused=True,head_AST_and_tokenizer_proof_reused=True,source_before_resources=True,control_failure_collection_selftest=True,runner_bash_n_rc=bash.returncode,board_run=False,quality_pass=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m421_prepare.py','m421_host_prepare.py','m421_support.py','m421_workflow.py','m421_control.ps1')})
    out=BASE/'runs/M421-saved-language-support-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m421_saved_language_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),f'## M421 组合保存特征语言组件与回收闭合（2026-10-06）\n\nSHA {sha(out)}；真实98×2560自有NPY只读加载、原件/错误SHA/范围/安全状态拒绝，以及声明合成的完整logits/KV/事务/Tokenizer/释放/分块回收负例共{len(rejected)}项；原语言算法AST除来源名字保持实际M41504，已有head AST/Tokenizer证明复用，不重复硬件。源特征检查在资源之前；runner bash-n和故意失败收集自测通过。未上板/判定/性能，允许同COM3确认sudo后一次执行。')
    print('M421_SUPPORT_SYNC',sha(out),len(rejected))
if __name__=='__main__':main()
