"""Explicit synthetic recovery negatives + versioned two-half control."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m427_workflow as w

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m427_half_protocol','latest_m427_half_component'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    component=json.loads((ROOT/board['latest_m427_half_component']['result']).read_bytes())
    for name in ('m426_range02.py','m427_saved_baseline.py'):assert sha(w.PKG/name)==component['staged_sources'][name]
    original=(HERE/'m426_control03.ps1').read_text(encoding='utf-8')
    control=original.replace('M426','M427').replace('m426','m427')
    control=control.replace('M427-all-FP32-MLP-software-02','M427-half-ranges-software-01').replace('m427_range_software_candidate_02','m427_half_ranges_candidate_01').replace('M427-range-software-board-02','M427-half-software-board-01').replace('tmp/m42703','tmp/m42701').replace('m427_workflow03.py','m427_workflow.py')
    for label in ('protocol','component','preparation','support','transfer'):control=control.replace('latest_m427_range_'+label,'latest_m427_half_'+label)
    control=control.replace("'latest_m425_warm_closure',","'latest_m425_warm_closure','latest_m426_range_closure',",1)
    atomic(HERE/'m427_control.ps1',control.encode('utf-8'),immutable=True)
    cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m427_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42701/control.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42701/control.stderr.bin',cp.stderr,immutable=True)
    assert cp.returncode==0 and b'M427_CONTROL_SELF_TEST_PASS' in cp.stdout
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(w.PKG/'run_m427.sh').relative_to(ROOT).as_posix()],capture_output=True)
    atomic(ROOT/'tmp/m42701/bash.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42701/bash.stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Versioned runner syntax refused')
    for path in w.PKG.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10))
    plan=json.loads((w.PKG/'PLAN.json').read_bytes());baseline=json.loads((BASE/'runs/M426-range-software-board-02/BOARD_RESULT.json').read_bytes())
    r=copy.deepcopy(baseline);r.update(status='PASS_M427_HALF_FEATURES_TASK_PENDING',gate_level='CPU-only-two-half-visual-MLP-screen',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),
        original_visual_forward_calls=0,saved_original_all24_boundaries_verified=True,baseline_source_sha256=plan['baseline_raw_sha256'],ranges=[],feature_pass_ranges=[],retained_features=[],feature_screen_pass=True)
    for spec in plan['candidate_ranges']:
        boundaries=copy.deepcopy(baseline['boundary_comparison'])
        for index in range(spec['selected_layers'][0]):boundaries[index]['candidate']=copy.deepcopy(boundaries[index]['original'])
        quality=copy.deepcopy(baseline['full_visual_quality']);quality['metrics'].update(relative_l2=.01,cosine=.9999,min_token_cosine=.9995);quality['feature_screen_pass']=True
        saved=dict(path=spec['name']+'_candidate_visual.npy',bytes=1003648,sha256='0'*64)
        row=dict(spec,logical_reference_calls=286,physical_reference_attempts=286,peak_live_layer_scopes=1,reference_batches={str(i):copy.deepcopy(baseline['reference_batches'][str(i)]) for i in spec['selected_layers']},
            boundary_comparison=boundaries,candidate_visual=baseline['candidate_visual'],saved_feature=saved,full_visual_quality=quality,feature_screen_pass=True)
        r['ranges'].append(row);r['retained_features'].append(saved);r['feature_pass_ranges'].append(spec['name'])
    def export(value):
        raw=json.dumps(value,separators=(',',':'),allow_nan=False).encode('utf-8');parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M427_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM427_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join(f'M427_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(x).decode('ascii')+'\n' for i,x in enumerate(parts))+f'M427_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    assert w.decode(export(r))[2]==r
    mixed=copy.deepcopy(r);mixed['ranges'][0]['full_visual_quality']['metrics']['relative_l2']=.03;mixed['ranges'][0]['full_visual_quality']['feature_screen_pass']=False;mixed['ranges'][0]['feature_screen_pass']=False;mixed['feature_pass_ranges']=mixed['feature_pass_ranges'][1:]
    assert w.decode(export(mixed))[2]==mixed
    reject_all=copy.deepcopy(mixed)
    reject_all['ranges'][1]['full_visual_quality']['metrics']['relative_l2']=.03;reject_all['ranges'][1]['full_visual_quality']['feature_screen_pass']=False;reject_all['ranges'][1]['feature_screen_pass']=False;reject_all.update(status='REJECT_M427_BOTH_HALF_RANGES',feature_pass_ranges=[],feature_screen_pass=False)
    assert w.decode(export(reject_all))[2]==reject_all
    failure=copy.deepcopy(r);failure.update(status='FAIL_M427_HALF_RANGE_SCREEN',gate_return_code=1,errors=['Explicit synthetic source failure'],ranges=[],retained_features=[],feature_pass_ranges=[],feature_screen_pass=False,visual_forward_calls=0)
    assert w.decode(export(failure))[2]==failure
    negatives=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError,KeyError,AssertionError):negatives.append(name)
        else:raise AssertionError('Invalid half recovery accepted '+name)
    for key,value in [('manifest_sha256','0'*64),('gate_return_code',True),('overlay_loaded',True),('dma_allocations',7),('fpga_transactions',1),('language_forward_calls',1),('temperature_measurement_enabled',True),('performance_pass',True),('task_screen_pass',True),('formal_promotion_allowed',True),('visual_owner_closed',False),('bindings_restored',False),('original_visual_forward_calls',1),('source_identities_verified',48),('baseline_source_sha256','0'*64),('saved_original_all24_boundaries_verified',False),('feature_pass_ranges',[]),('elapsed_s_diagnostic_not_performance',961)]:
        bad=copy.deepcopy(r);bad[key]=value;reject(key,lambda bad=bad:w.check(bad))
    for label in ('half-order','missing-half','selection','count','missing-layer','missing-batch','tail','retry','attempt-count','window','boundary-count','original-boundary','prefix-changed','threshold','verdict','nonfinite','feature-shape','feature-file','prefix-topology'):
        bad=copy.deepcopy(r);x=bad['ranges'][0]
        if label=='half-order':bad['ranges'].reverse()
        elif label=='missing-half':bad['ranges'].pop()
        elif label=='selection':x['selected_layers'].pop()
        elif label=='count':x['logical_reference_calls']=285
        elif label=='missing-layer':x['reference_batches'].pop('2')
        elif label=='missing-batch':x['reference_batches']['2']['fc1'].pop()
        elif label=='tail':x['reference_batches']['2']['fc1'][-1]['rows']=31
        elif label=='retry':x['reference_batches']['2']['fc1'][0]['attempted_shifts']=[6,4]
        elif label=='attempt-count':x['physical_reference_attempts']=287
        elif label=='window':bad['weight_windows']['2']['fc1'][0]['sha256']='0'*64
        elif label=='boundary-count':x['boundary_comparison'].pop()
        elif label=='original-boundary':x['boundary_comparison'][2]['original']['sha256']='0'*64
        elif label=='prefix-changed':x['boundary_comparison'][0]['candidate']['sha256']='0'*64
        elif label=='threshold':x['full_visual_quality']['thresholds']['maximum_relative_l2']=.04
        elif label=='verdict':x['feature_screen_pass']=False
        elif label=='nonfinite':x['full_visual_quality']['metrics']['cosine']=float('nan')
        elif label=='feature-shape':x['candidate_visual']['shape']=[1,2560]
        elif label=='feature-file':x['saved_feature']['bytes']=1
        else:bad['prefix_topology']['0']['conversion_wrapper']=True
        reject(label,lambda bad=bad:w.check(bad))
    good=export(r)
    for label,value in [('duplicate',good+good),('chunk-order',good.replace('M427_RESULT_CHUNK=1/','M427_RESULT_CHUNK=0/')),('missing-chunks',good[:good.index('M427_RESULT_CHUNK=1/')]),('export-rc',good.replace('export_rc=0','export_rc=1')),('raw-SHA',good.replace('M427_RESULT_SHA256=','M427_RESULT_SHA256=0'))]:reject(label,lambda value=value:w.decode(value))
    sources={n:sha(HERE/n) for n in ('m427_control.ps1','m427_workflow.py','m427_support.py','m427_component.py','test_m427_baseline.py')}
    value=dict(status='PREPARED_M427_CPU_HALF_SCREEN_WITH_STRICT_RECOVERY',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),protocol_sha256=board['latest_m427_half_protocol']['sha256'],component_sha256=board['latest_m427_half_component']['sha256'],
        source_sha256=sources,negative_checks=negatives,collector_fixture_explicit_synthetic=True,pass_mixed_reject_and_failure_collected=True,controller_failure_collect=True,Python310_syntax=True,runner_bash_n=True,board_run=False,performance_pass=False)
    out=BASE/'runs/M427-half-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m427_half_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
        f'## M427 两半区控制与回收准备完成（2026-10-06）\n\nSHA {sha(out)}；{len(negatives)}项明确合成回收负例，通过双过/一过一拒/双拒/执行失败原rc和全SHA恢复、固定11层286批/24边界/原保存SHA/禁止晋级检查；Python3.10/bash-n与控制故意失败收集通过。实际组件已独立同步，未上传或执行，原版视觉不重算。')
    support=BASE/'runs/M427-half-support-01/RESULT.json';atomic(support,encoded(dict(value,status='PASS_M427_CPU_HALF_CONTROL_AND_RECOVERY')),immutable=True)
    sync('latest_m427_half_support',dict(status='PASS_M427_CPU_HALF_CONTROL_AND_RECOVERY',result=support.relative_to(ROOT).as_posix(),sha256=sha(support),manifest_sha256=value['manifest_sha256']),
        f'## M427 两半区门禁支持（2026-10-06）\n\nSHA {sha(support)}；准备{sha(out)}及源控制SHA锁定，{len(negatives)}负例通过。下一步仅COM3同终端sudo一次检查，manifest-first传输，两个固定CPU软件半区，不改变阈值、不自动加范围。')
    print('M427_PREPARATION_AND_SUPPORT_SYNC',sha(out),sha(support),len(negatives))
if __name__=='__main__':main()
