"""Synthetic saved-evidence negative checks; no model or board execution."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m426_workflow as w
def main():
    plan=json.loads((w.PKG/'PLAN.json').read_bytes());expected=json.loads((w.PKG/'EXPECTED_VISUAL.json').read_bytes())
    original=json.loads((BASE/'runs/M420-combination-board-01/BOARD_RESULT.json').read_bytes())
    r=dict(status='PASS_M426_FEATURE_SCREEN_TASK_PENDING',gate_level='CPU-only-cumulative-visual-MLP-range-screen',gate_return_code=0,manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),selected_layers=list(range(2,24)),errors=[],visual_forward_calls=2,
        logical_reference_calls=572,peak_live_layer_scopes=1,physical_reference_attempts=572,preprocessed=expected['preprocessed'],original_visual=expected['visual'],candidate_visual=original['candidate_visual'],
        source_identities_verified=49,backend_before={},backend_after={},CPU_store_after=dict(cache_within_budget=True),release_preflight=dict(status='READY_FOR_BOARD_PREFLIGHT'),
        weight_windows=plan['windows'],targets={},reference_batches={},boundary_comparison=[],full_visual_quality=original['full_visual_quality'],feature_screen_pass=True,
        retained_features=[dict(path=name,bytes=1003648,sha256='0'*64) for name in ('original_visual.npy','candidate_visual.npy')],elapsed_s_diagnostic_not_performance=1)
    for k in ('overlay_loaded','dma_allocations','fpga_transactions','language_forward_calls','temperature_measurement_enabled','performance_pass','formal_promotion_allowed','task_screen_pass','task_screen_recorded','numerical_hardware_proven'):r[k]=False
    for k in ('software_screen_completed','bindings_restored','visual_owner_closed','no_pynq_import','boot_unchanged','cmdline_unchanged','original_reference_pass'):r[k]=True
    for i in range(2,24):
        r['targets'][str(i)]=dict(target_dtype='torch.float32',output_dtype='torch.bfloat16',matrices={part:dict(name=f'encoder.layers.{i}.mlp.{part}',shape=shape,bias_sha256='0'*64) for part,shape in (('fc1',[1024,4096]),('fc2',[4096,1024]))})
        r['reference_batches'][str(i)]={}
        for part in ('fc1','fc2'):
            c=plan['chains'][str(i)][part]
            r['reference_batches'][str(i)][part]=[dict(start=n*32,rows=32 if n<12 else 8,input_bytes=c['input_bytes'],output_bytes=c['output_bytes'],logical_calls=1,initial_shift=3,selected_shift=3,attempted_shifts=[3],physical_reference_attempts=1,packet_sha256='0'*64,raw_sha256='0'*64) for n in range(13)]
    metrics=dict(shape=[392,1024],cosine=.99999,relative_l2=.001,RMSE=.0001,max_abs=.01,min_token_cosine=.9999)
    r['boundary_comparison']=[dict(layer=i,metrics=metrics) for i in range(24)]
    def export(value):
        raw=json.dumps(value,separators=(',',':'),allow_nan=False).encode('utf-8');pieces=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M426_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM426_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join(f'M426_RESULT_CHUNK={i}/{len(pieces)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(pieces))+f'M426_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    assert w.decode(export(r))[2]==r
    rejected=copy.deepcopy(r);rejected['status']='REJECT_M426_ALL22_FEATURE_RANGE';rejected['full_visual_quality']['metrics']['relative_l2']=.03;rejected['full_visual_quality']['feature_screen_pass']=False;rejected['feature_screen_pass']=False
    assert w.decode(export(rejected))[2]==rejected
    failure=copy.deepcopy(r);failure.update(status='FAIL_M426_SOFTWARE_RANGE',gate_return_code=1,errors=['Explicit synthetic source failure'],visual_forward_calls=0,feature_screen_pass=False)
    assert w.decode(export(failure))[2]==failure
    negatives=[]
    def reject(label,fn):
        try:fn()
        except (ValueError,RuntimeError,KeyError,AssertionError):negatives.append(label)
        else:raise AssertionError('Invalid evidence accepted '+label)
    for key,value in [('manifest_sha256','0'*64),('gate_return_code',True),('temperature_measurement_enabled',True),('overlay_loaded',True),('dma_allocations',7),('fpga_transactions',1),('language_forward_calls',1),('performance_pass',True),('task_screen_pass',True),('formal_promotion_allowed',True),('visual_owner_closed',False),('bindings_restored',False),('source_identities_verified',48),('logical_reference_calls',571),('peak_live_layer_scopes',22),('physical_reference_attempts',573),('feature_screen_pass',False),('elapsed_s_diagnostic_not_performance',4300)]:
        bad=copy.deepcopy(r);bad[key]=value;reject(key,lambda bad=bad:w.check(bad))
    for label in ('missing-layer','missing-batch','wrong-tail','wrong-shift','window-SHA','wrong-precision','missing-boundary','nonfinite-metric','changed-threshold','bad-feature-file','bad-original-SHA'):
        bad=copy.deepcopy(r)
        if label=='missing-layer':bad['reference_batches'].pop('23')
        elif label=='missing-batch':bad['reference_batches']['2']['fc1'].pop()
        elif label=='wrong-tail':bad['reference_batches']['2']['fc1'][-1]['rows']=31
        elif label=='wrong-shift':bad['reference_batches']['2']['fc1'][0]['attempted_shifts']=[3,1]
        elif label=='window-SHA':bad['weight_windows']['2']['fc1'][0]['sha256']='0'*64
        elif label=='wrong-precision':bad['targets']['2']['target_dtype']='torch.bfloat16'
        elif label=='missing-boundary':bad['boundary_comparison'].pop()
        elif label=='nonfinite-metric':bad['full_visual_quality']['metrics']['cosine']=float('nan')
        elif label=='changed-threshold':bad['full_visual_quality']['thresholds']['maximum_relative_l2']=.04
        elif label=='bad-feature-file':bad['retained_features'][1]['bytes']=1
        else:bad['original_visual']['sha256']='0'*64
        reject(label,lambda bad=bad:w.check(bad))
    text=export(r)
    for label,value in [('duplicate-export',text+text),('wrong-order',text.replace('M426_RESULT_CHUNK=1/','M426_RESULT_CHUNK=0/')),('missing-chunks',text[:text.index('M426_RESULT_CHUNK=1/')]),('export-failure',text.replace('export_rc=0','export_rc=1')),('wrong-raw-SHA',text.replace(re.search if False else 'M426_RESULT_SHA256=','M426_RESULT_SHA256=0'))]:
        reject(label,lambda value=value:w.decode(value))
    for p in w.PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    control=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m426_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42601/control.stdout.bin',control.stdout,immutable=True);atomic(ROOT/'tmp/m42601/control.stderr.bin',control.stderr,immutable=True)
    assert control.returncode==0 and b'M426_CONTROL_SELF_TEST_PASS' in control.stdout
    result=dict(status='PASS_M426_CPU_RANGE_CONTROL_AND_STRICT_RECOVERY',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),
        collector_fixture_explicit_synthetic=True,accepted_completed_pass_and_quality_reject_and_execution_failure=True,negative_checks=negatives,
        controller_failure_collect=True,Python310_syntax=True,source_sha256={n:sha(HERE/n) for n in ('m426_control.ps1','m426_workflow.py','m426_support.py')},
        board_run=False,actual_model_feature_quality_pass=False,performance_pass=False)
    out=BASE/'runs/M426-range-support-01/RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m426_range_support',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=result['manifest_sha256'],board_run=False,performance_pass=False),f'## M426 控制与严格回收检查（2026-10-06）\n\nSHA {sha(out)}；明确合成的完成通过/质量拒绝/执行失败回收及{len(negatives)}负例、控制故意失败后始终收集、Python3.10通过。572批/完整边界/全特征/原SHA/窗口/重试/资源与禁止晋级检查。只补准备，不重复已通过算术组件或旧上板实验。下一步COM3一次授权后上传并执行仅PS完整软件范围筛查。')
    print('M426_SUPPORT_SYNC',sha(out),len(negatives))
if __name__=='__main__':main()
