"""Freeze one three-visual-call numerical combination; no timing or language."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());plan_record=b['latest_m420_combination_plan'];assert sha(ROOT/plan_record['result'])==plan_record['sha256']
    component_path=ROOT/'tmp/m42002/component/RESULT.json';component=json.loads(component_path.read_bytes());assert component['isolation']['parent_state_unchanged'] and component['component']['complete52_packets_raw_exact'] and component['component']['negative_checks']==4
    old=BASE/'candidates/M414-layer12-full-visual-01';oldplan=json.loads((old/'PLAN.json').read_bytes());plan=dict(selected_layers=[12,13],rows=392,default_off=True,board_prerequisites=[],reused_packages=[],resolved_module_names=oldplan['resolved_module_names'],component_source_sha256={n:sha(HERE/n) for n in ('m420_combination.py','test_m420_combination.py')})
    reuse=[('M417-layer13-saved-reference-02','/home/ubuntu/m417_layer13_reference_candidate_02'),('M418-visual-linear-01','/home/ubuntu/m418_visual_linear_candidate_01'),('M409-saved-MLP-reference-01','/home/ubuntu/m409_mlp_reference_candidate_01'),('M410-visual-linear-01','/home/ubuntu/m410_visual_linear_candidate_01'),('M414-layer12-full-visual-01','/home/ubuntu/m414_layer12_full_visual_candidate_01')]
    # Actual M414 controller is authoritative for its remote directory.
    control=(HERE/'m414_control.ps1').read_text(encoding='utf-8');assert reuse[-1][1] in control
    for local,remote in reuse:
        p=BASE/'candidates'/local;m=json.loads((p/'PACKAGE_MANIFEST.json').read_bytes())
        for row in m['files']:assert sha(p/row['path'])==row['sha256']
        plan['reused_packages'].append(dict(directory=remote,manifest_sha256=sha(p/'PACKAGE_MANIFEST.json')))
    plan.update(reference13_package=reuse[0][1],lower_packages={'12':reuse[3][1],'13':reuse[1][1]},
        original_reference_result=b['latest_m414_layer12_visual_board']['result'],original_reference_sha256=b['latest_m414_layer12_visual_board']['sha256'],
        reference_results={'12':b['latest_m409_reference_board']['result'],'13':b['latest_m417_reference_board02']['result']},
        protocol=json.loads((ROOT/plan_record['result']).read_bytes())['protocol'],ordinary_growth_budget_bytes=768<<20,ordinary_available_reserve_bytes=64<<20,seven_DMA_payload_bytes=3440656,fixed_CMA_floor=None,
        stop_on_dynamic_software_retry=True,dynamic_retry_explanation='Existing oracle retains selected finite wire only; if retries occur, stop before Overlay rather than compare unrecorded attempts.')
    for key,remote in [('latest_m412_complete_mlp_board','/home/ubuntu/m412_complete_mlp_01/BOARD_RESULT.json'),('latest_m419_complete_mlp_board03','/home/ubuntu/m419_complete_mlp_03/BOARD_RESULT.json'),('latest_m414_layer12_visual_board','/home/ubuntu/m414_layer12_full_visual_01/BOARD_RESULT.json')]:
        e=b[key];assert sha(ROOT/e['result'])==e['sha256'];r=json.loads((ROOT/e['result']).read_bytes());assert r['gate_return_code']==0 and r['stable_restored'] and r['safe_buffers_released'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        plan['board_prerequisites'].append(dict(path=remote,sha256=e['sha256'],status=r['status'],local_net_gain=key!='latest_m414_layer12_visual_board',local_path=e['result']))
    pkg=BASE/'candidates/M420-layers12-13-full-visual-01';assert not pkg.exists();pkg.mkdir()
    for name in ('m420_gate.py','m420_combination.py','test_m420_combination.py'):
        data=(HERE/name).read_bytes();ast.parse(data,feature_version=(3,10));atomic(pkg/name,data,immutable=True)
    atomic(pkg/'m411_mlp_binding.py',(BASE/'candidates/M419-layer13-complete-MLP-03/m411_mlp_binding.py').read_bytes(),immutable=True)
    atomic(pkg/'EXPECTED_VISUAL.json',(old/'EXPECTED_VISUAL.json').read_bytes(),immutable=True);atomic(pkg/'PLAN.json',encoded(plan),immutable=True)
    exporter=(HERE/'m414_export.py').read_text(encoding='utf-8').replace('M414','M420').replace('m414_layer12_full_visual_01','m420_combination_visual_01').replace('layer12-full-visual-feature-quality','layers12-13-full-visual-feature-quality')
    atomic(pkg/'m420_export.py',exporter.encode('utf-8'),immutable=True)
    runner=(old/'run_m414_mlp.sh').read_text(encoding='utf-8').replace('M414','M420').replace('m414','m420').replace('m420_layer12_full_visual_01','m420_combination_visual_01').replace('--enable-layer12-visual-quality','--enable-combination-quality')
    atomic(pkg/'run_m420_mlp.sh',runner.encode('utf-8'),immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    v=dict(status='PREPARED_M420_DYNAMIC_COMBINATION_VISUAL',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=m['file_count'],bytes=m['total_bytes'],component_sha256=sha(component_path),actual_clean_component=component,unchanged_binding_sha256=sha(pkg/'m411_mlp_binding.py'),plan_sha256=plan_record['sha256'],board_run=False,expanded_24_layers=False,performance_pass=False,semantic_accuracy=False,
        prior_offline_missing_binding_rejection_preserved='tmp/m42001/component/component_stderr.txt',actual_component_paths_closed=True)
    out=BASE/'runs/M420-combination-preparation-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m420_combination_preparation',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),f'## M420 双层完整视觉准备（2026-10-06）\n\nSHA {sha(out)}；干净staging真实24包装/M207合成组件证明13输入改变、52全部wire/完整输出一致及第二层出错和部分进入恢复，4负例；首staging缺冻结binding已保留并在02闭合，未上板。原数学binding同SHA，实际同一七DMA复用；固定原版→动态软件组合→PL组合三次视觉、0语言/性能/24层，精度或资源失败停本级。先实际前级正负、源码顺序、回收和控制检查后才上板。')
    print('M420_PREPARED',sha(out),v['manifest_sha256'])
if __name__=='__main__':main()
