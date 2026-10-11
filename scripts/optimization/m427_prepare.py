"""Freeze two disjoint halves once; reuse original saved full visual reference."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OLD=BASE/'candidates/M426-all-FP32-MLP-software-02'
PKG=BASE/'candidates/M427-half-ranges-software-01'
RANGES=[dict(name='early_2_12',selected_layers=list(range(2,13))),dict(name='late_13_23',selected_layers=list(range(13,24)))]

def once(t,a,b):
    if t.count(a)!=1:raise RuntimeError('Frozen derivation anchor differs '+a[:80])
    return t.replace(a,b)

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites={}
    for key in ('latest_m426_range_software_board','latest_m426_range_closure','latest_m426_range_component','latest_m426_range_preparation','latest_m426_range_support'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256'] and all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prerequisites[key]=row
    rawpath=ROOT/prerequisites['latest_m426_range_software_board']['result'];raw=json.loads(rawpath.read_bytes())
    assert raw['status']=='REJECT_M426_ALL22_FEATURE_RANGE' and raw['gate_return_code']==0 and raw['original_reference_pass'] and raw['visual_owner_closed'] and raw['bindings_restored'] and raw['logical_reference_calls']==572
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan.update(candidate_ranges=RANGES,baseline_raw_sha256=sha(rawpath),baseline_raw_bytes=rawpath.stat().st_size,
        baseline_directory='/home/ubuntu/m426_range_software_02',original_visual_forward_calls=0,visual_calls=2,budget_seconds=900,
        maximum_automatic_candidates=2,partition_order_fixed=True,task_complete=False,
        failure_next_step='Read the two predeclared half results. No thresholds changed, automatic extra ranges, PL or timing. Only a feature-passing half may enter saved-feature task consistency.')
    plan['prerequisites'].append(dict(path='/home/ubuntu/m426_range_software_02/BOARD_RESULT.json',sha256=sha(rawpath)))
    gate=(OLD/'m426_gate.py').read_text(encoding='utf-8').replace('M426','M427').replace('/home/ubuntu/m426_range_software_02/','/home/ubuntu/m427_half_ranges_software_01/')
    gate=gate.replace("status='FAIL_M427_SOFTWARE_RANGE'","status='FAIL_M427_HALF_RANGE_SCREEN'").replace("gate_level='CPU-only-cumulative-visual-MLP-range-screen'","gate_level='CPU-only-two-half-visual-MLP-screen'")
    gate=once(gate,"feature_screen_pass=False,task_screen_pass=False,task_screen_recorded=False,","feature_screen_pass=False,feature_pass_ranges=[],ranges=[],original_visual_forward_calls=0,task_screen_pass=False,task_screen_recorded=False,")
    gate=once(gate,"from m426_range02 import resolve,RangeScope,SELECTED,prefix_evidence","from m426_range02 import resolve,RangeScope,SELECTED,prefix_evidence\n        from m427_saved_baseline import source as baseline_source,feature as baseline_feature,boundary as baseline_boundary")
    gate=once(gate,"        def original_sink(index,arr):\n            array_file(OUTPUT.parent/f'original_boundary_{index:02d}.npy',arr)\n", "        original_record=baseline_source(plan)\n        original=baseline_feature(original_record)\n        result['baseline_source_sha256']=plan['baseline_raw_sha256']\n        result['original_visual']=tensor(original)\n        if result['original_visual']!=expected['visual']:raise RuntimeError('Saved complete original feature SHA differs')\n        for index in range(24):\n            checked_boundary=baseline_boundary(original_record,index)\n            del checked_boundary\n        result['saved_original_all24_boundaries_verified']=True\n        result['original_reference_pass']=True\n        active_range={}\n")
    gate=once(gate,"            ref=np.load(OUTPUT.parent/f'original_boundary_{index:02d}.npy',allow_pickle=False)","            ref=baseline_boundary(original_record,index)")
    gate=once(gate,"            result['boundary_comparison'].append(dict(layer=index,original=tensor(ref),candidate=tensor(arr),metrics=metrics(ref,arr)))","            active_range['boundary_comparison'].append(dict(layer=index,original=tensor(ref),candidate=tensor(arr),metrics=metrics(ref,arr)))")
    gate=once(gate,"        def vision(mode,sink):","        def vision(mode,sink,selected):")
    gate=once(gate,"phase[0]=mode+'-full-visual'","phase[0]=active_range['name']+'-full-visual'")
    gate=once(gate,"targets,SELECTED,mode,load_case","targets,selected,mode,load_case")
    start=gate.index("        original=vision('original'");end=gate.index("        result['backend_after']",start)
    replacement="""        result['retained_features']=[]
        for specification in plan['candidate_ranges']:
            active_range=dict(name=specification['name'],selected_layers=specification['selected_layers'],boundary_comparison=[])
            candidate=vision('software',candidate_sink,active_range['selected_layers'])
            active_range['candidate_visual']=tensor(candidate)
            saved=array_file(OUTPUT.parent/(active_range['name']+'_candidate_visual.npy'),candidate)
            result['retained_features'].append(saved);active_range['saved_feature']=saved
            active_range['reference_batches']=scope.batches
            active_range['peak_live_layer_scopes']=scope.peak_live_layer_scopes
            active_range['logical_reference_calls']=sum(len(rows) for parts in scope.batches.values() for rows in parts.values())
            active_range['physical_reference_attempts']=sum(x['physical_reference_attempts'] for parts in scope.batches.values() for rows in parts.values() for x in rows)
            if active_range['logical_reference_calls']!=286 or active_range['peak_live_layer_scopes']!=1:raise RuntimeError('One11-layer half reference count differs')
            active_range['full_visual_quality']=visual_quality(original,candidate)
            active_range['feature_screen_pass']=active_range['full_visual_quality']['feature_screen_pass']
            result['ranges'].append(active_range)
            if active_range['feature_screen_pass']:result['feature_pass_ranges'].append(active_range['name'])
            del candidate
        result['feature_screen_pass']=bool(result['feature_pass_ranges'])
        result['software_screen_completed']=True;result['bindings_restored']=all(scopes)
"""
    gate=gate[:start]+replacement+gate[end:]
    gate=gate.replace('del original,candidate,load_case,vision','del original,original_record,load_case,vision')
    gate=once(gate,"'PASS_M427_FEATURE_SCREEN_TASK_PENDING' if result['feature_screen_pass'] else 'REJECT_M427_ALL22_FEATURE_RANGE'","'PASS_M427_HALF_FEATURES_TASK_PENDING' if result['feature_screen_pass'] else 'REJECT_M427_BOTH_HALF_RANGES'")
    gate=gate.replace("result['status']='FAIL_M427_SOFTWARE_RANGE'","result['status']='FAIL_M427_HALF_RANGE_SCREEN'")
    assert gate.index('original=baseline_feature')<gate.index("candidate=vision('software'") and "vision('original'" not in gate
    # The unchanged math/lifecycle scope is reused byte for byte.
    texts={'m427_gate.py':gate,'m426_range02.py':(OLD/'m426_range02.py').read_text(encoding='utf-8'),'m427_saved_baseline.py':(HERE/'m427_saved_baseline.py').read_text(encoding='utf-8')}
    exporter=(OLD/'m426_export.py').read_text(encoding='utf-8').replace('M426','M427').replace('/home/ubuntu/m426_range_software_02/','/home/ubuntu/m427_half_ranges_software_01/')
    texts['m427_export.py']=exporter
    runner=(OLD/'run_m426.sh').read_text(encoding='utf-8').replace('M426','M427').replace('m426_gate.py','m427_gate.py').replace('m426_export.py','m427_export.py').replace('/home/ubuntu/m426_range_software_02','/home/ubuntu/m427_half_ranges_software_01')
    texts['run_m427.sh']=runner
    PKG.mkdir(exist_ok=False)
    for name,text in texts.items():
        if name.endswith('.py'):ast.parse(text,feature_version=(3,10))
        atomic(PKG/name,text.encode('utf-8'),immutable=True)
    for name in ('EXPECTED_VISUAL.json','SOURCE_IDENTITIES.json'):atomic(PKG/name,(OLD/name).read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    assert sha(PKG/'m426_range02.py')==sha(OLD/'m426_range02.py')
    record=dict(status='FROZEN_M427_TWO_DISJOINT_HALF_SOFTWARE_SCREEN',prerequisites=prerequisites,
        candidate_ranges=RANGES,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],plan=plan,
        original_visual_reused_sha256=raw['original_visual']['sha256'],original_reference_calls=0,selected_reference_calls_per_half=286,
        unchanged_RangeScope_sha256=sha(PKG/'m426_range02.py'),unchanged_exact_oracle_reused=True,
        task_and_hardware_timing_locked=True,board_run=False,feature_quality_pass=False,performance_pass=False)
    out=BASE/'runs/M427-half-protocol-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m427_half_protocol',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256'],performance_pass=False),
        f'## M427 固定两半区软件定位协议（2026-10-06）\n\nSHA {sha(out)}；M426完整22层relativeL2 0.0329145、min token cosine0.975242未过原阈值，原裁决不改。固定2–12及13–23各11层、各286参考批，只有两个候选；复用M426已核SHA的原版feature/24边界，不重复原版视觉，不以累计层差直接认定局部敏感。原RangeScope/算术同SHA，输入、Attention/GELU/norm/语言/缓存/线程不变，无Overlay/DMA/语言/PL/测温；先组件与回收，特征通过的范围才可进入保存特征任务判断。')
    print('M427_PROTOCOL_FROZEN',sha(out),record['manifest_sha256'])

if __name__=='__main__':main()
