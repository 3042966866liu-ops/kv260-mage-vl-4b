"""Freeze exact video budget and missing-only PS reference component."""
import ast
import importlib.util
import json
import shutil
import subprocess
import sys
import types
import m351_workflow as w

OLD=w.BASE/'candidates/M366-staged-text-03'
PKG=w.BASE/'candidates/M367-PS-visual-reference-02'
OUT=w.BASE/'runs/M367-PS-reference-preparation-02'


def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Immutable preparation exists')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        text=(w.ROOT/name).read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=w.sha(w.ROOT/name),bytes=(w.ROOT/name).stat().st_size,lines=len(text.splitlines()))
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=w.BASE/'runs/M366-staged-text-closure-02/RESULT.json'
    assert w.sha(prior)==board['latest_m366_staged_text_closure']['sha256']=='ec450256bea9f4f8baf1f8b0df6c400108048ac338424a3f19e72d2adcff4b1b'
    pr=json.loads(prior.read_text(encoding='utf-8'));assert pr['status']=='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS'
    assert all(w.sha(prior) in (w.ROOT/name).read_text(encoding='utf-8') for name in ('CURRENT_STATE.md','docsMILESTONES.md'))
    oldraw=w.BASE/'runs/M345-fixed-video-board-01/BOARD_RESULT.json'
    assert w.sha(oldraw)=='b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'
    baseline=json.loads(oldraw.read_text(encoding='utf-8'))['passes'][0]
    assert baseline['logical_calls']==778 and baseline['host_calls']==778+baseline['retry_count']==781
    assert len(baseline['keys'])==len(baseline['values'])==36 and len(baseline['families'])==154 and baseline['logits']['shape']==[151936]
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    closure=json.loads((OLD/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    d=release/'deployment/mage_vl4b/m181_m120_video_board_candidate'
    layout_path=d/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json';layout=json.loads(layout_path.read_text(encoding='utf-8'))
    largest=max(layout['modules'],key=lambda e:int(e['shape'][0])*int(e['input_groups'])*64)
    padded=int(largest['shape'][0])*int(largest['input_groups'])*64
    max_shard_elements=max(int(e['input_groups'])*int(t['rows_per_shard'])*64 for e in layout['modules'] for t in e['tiles'])
    cache_path=release/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/M261_CACHE_POLICY.json';cache=json.loads(cache_path.read_text(encoding='utf-8'))
    known=dict(visual_retained_code_cache=int(cache['expected_used_bytes']),max_visual_FP32_restored_weight=padded*4,max_visual_int16_codes=padded*2,max_visual_int16_codes_plus_qmin_temporary=padded*2,max_visual_FP32_scale_and_int16_qmin=int(largest['shape'][0])*int(largest['input_groups'])*6,max_visual_shard_unpack_and_transpose_copy=max_shard_elements*4,visual_conservative_BF16_and_FP32_GEMM_conversion=padded*6,visual_two_attention_score_arrays=2*16*392*392*4,visual_two_intermediate_arrays=2*392*4096*4,visual_feature_output=98*2560*4,video_source_frames=4*448*448*3,preprocessed_pixels=392*768*4,video_language_hidden=159*2560*4,full159_KV=36*2*159*8*128*4,language_two_gate_up_arrays=2*159*9728*4,language_two_group_attention_score_arrays=2*(32//8)*159*159*4,head_two_dense_T32_vocab_arrays=2*32*151936*4,logits_export_payload=151936*4,reference_hash_read_buffers=8<<20)
    visual_total=sum(v for k,v in known.items() if k.startswith(('visual_','max_visual_','video_source','preprocessed')))
    native=256<<20
    budget=dict(scope='Original last source frame global/detail two224 views,98 visual tokens,159 prompt tokens,originalW4/M238/M241,decode0',extra_explicit_CMA_after_original7_buffers_bytes=0,original7_buffer_bytes=[6963200]*4+[389152,2621440,2621440],known_conservative_payload_and_temporary_bytes=known,known_sum_not_exact_simultaneous_peak=sum(known.values()),visual_known_sum_not_exact_peak=visual_total,unproven_native_workspace_allowance_bytes=native,visual_reference_PS_growth_limit_bytes=768<<20,full_video_PS_growth_limit_bytes=1024<<20,MemAvailable_margin_bytes=64<<20,production64MiB_unchanged=True,not_native_peak_certificate=True,largest_visual_module=largest['module'],largest_visual_shape=largest['shape'],source_sha256=dict(vision_layout=w.sha(layout_path),cache_policy=w.sha(cache_path)),baseline_raw_sha256=w.sha(oldraw),baseline_input=baseline['input'],logical_calls=778,physical_calls_rule='778 plus actual converged retry attempts; compare full old baseline numerics, not assume zero retry',missing_reference='Independent board PS visual/preprocessed tensor SHA; old GPU-only feature SHA not accepted as board reference')
    assert visual_total+native<budget['visual_reference_PS_growth_limit_bytes']
    assert sum(known.values())+native<budget['full_video_PS_growth_limit_bytes']
    PKG.mkdir()
    names=['measurement.py','frozen_video_identity.py','m341_build_id_gate.py','board_safety.py','m120_board_common.py','m120_board_env_preflight.py','memory_lifecycle.py','SOURCE_CLOSURE.json']
    for name in names:shutil.copyfile(OLD/name,PKG/name)
    shutil.copyfile(w.HERE/'m367_visual_reference_gate.py',PKG/'m367_visual_reference_gate.py')
    shutil.copyfile(prior,PKG/'TEXT_PREREQUISITE.json')
    w.atomic(PKG/'VIDEO_EXPECTED.json',w.encoded(dict(raw_sha256=w.sha(oldraw),baseline=dict(input=baseline['input']))))
    w.atomic(PKG/'VIDEO_BUDGET.json',w.encoded(budget))
    assembler=(OLD/'m366_assemble.py').read_text(encoding='utf-8').replace('M366','M367').replace('/home/ubuntu/m366_staged_text_candidate_02','/home/ubuntu/m366_staged_text_candidate_03').replace('f3138f0d3e0c2d308329fbdbb8b9e3cc0f2a9ccf45ca3fe35fc6d73231d26484',w.sha(OLD/'PACKAGE_MANIFEST.json'))
    w.atomic(PKG/'m367_assemble.py',assembler.encode('utf-8'))
    export='''import base64,hashlib,json,os\nfrom pathlib import Path\nif os.geteuid()!=0:raise RuntimeError('Root required')\nraw=Path('/home/ubuntu/m367_visual_reference_01/RESULT.json').read_bytes();r=json.loads(raw)\nif r['gate_level']!='missing-PS-visual-reference-only':raise RuntimeError('Scope differs')\nprint('M367_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)\nprint('M367_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)\nchunks=[raw[i:i+900] for i in range(0,len(raw),900)]\nfor i,p in enumerate(chunks):print(f'M367_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)\n'''
    w.atomic(PKG/'m367_export_result.py',export.encode('utf-8'))
    runner='''#!/usr/bin/env bash\nset -euo pipefail\n[[ $EUID == 0 && $# == 3 && $3 == PS1 ]] || exit 64\ntask_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\ntask_python=/usr/local/share/pynq-venv/bin/python\nif [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m367_export_result.py"; exit 0; fi\n[[ $2 == Run && ${M367_ENABLE_PS_REFERENCE:-0} == 1 ]] || exit 66\n[[ ! -e /home/ubuntu/m367_visual_reference_01 ]] || exit 67\nset +e\n"$task_python" -B "$task_dir/m367_visual_reference_gate.py" "$1" --enable-ps-reference\ntask_gate_rc=$?\n"$task_python" -B "$task_dir/m367_export_result.py"\ntask_export_rc=$?\nset -e\necho "M367_DONE case=PS1 gate_rc=$task_gate_rc export_rc=$task_export_rc"\nif [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi\nexit "$task_export_rc"\n'''
    w.atomic(PKG/'run_m367_visual_reference.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m367-missing-PS-reference-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','torch','tokenizers','m276_m254_video_server'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            imports=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [])
            missing.extend((module,name) for name in imports if name not in trees and name not in allowed)
    assert not missing,missing
    # Import-only fake Linux module for host checks; never a board/environment proof.
    fake=types.ModuleType('fcntl');fake.LOCK_EX=fake.LOCK_NB=fake.LOCK_UN=0;fake.flock=lambda *a:None
    old_fcntl=sys.modules.get('fcntl');sys.modules['fcntl']=fake
    sys.path.insert(0,str(PKG))
    try:
        spec=importlib.util.spec_from_file_location('m367_policy_fixture',PKG/'m367_visual_reference_gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
        mem=dict(system_bytes={'MemAvailable':832<<20},process_bytes={'VmRSS':400<<20})
        assert gate.assess(mem,400<<20)['observed_growth_bytes']==0
        rejected=0
        for trial in [dict(system_bytes={'MemAvailable':831<<20},process_bytes={'VmRSS':400<<20}),dict(system_bytes={'MemAvailable':1000<<20},process_bytes={'VmRSS':1169<<20})]:
            try:gate.assess(trial,400<<20)
            except MemoryError:rejected+=1
            else:raise AssertionError('PS budget failure accepted')
        for name in ('pynq','pynq.buffer'):
            try:gate.DenyPynq().find_spec(name)
            except RuntimeError:rejected+=1
            else:raise AssertionError('PYNQ import permitted')
        try:gate.NoBoard().lm_head
        except RuntimeError:rejected+=1
        else:raise AssertionError('Language PL path accessible')
        assert gate.tensor(__import__('numpy').zeros((98,2560),dtype='float32'))['bytes']==1003520
    finally:
        sys.path.remove(str(PKG))
        if old_fcntl is None:sys.modules.pop('fcntl',None)
        else:sys.modules['fcntl']=old_fcntl
    source=(PKG/'m367_visual_reference_gate.py').read_text(encoding='utf-8')
    assert 'language.prefill(' not in source and '.Overlay(' not in source and '.allocate(' not in source
    control=(w.HERE/'m36603_control.ps1').read_text(encoding='utf-8').replace('M366','M367').replace('m366','m367').replace('m36703','m367').replace('M367-staged-text-03','M367-PS-visual-reference-02').replace('M367-staged-text-support-03','M367-PS-reference-preparation-02').replace('M367-staged-text-transfer-02','M367-PS-reference-transfer-01').replace('m367_staged_text_candidate_03','m367_visual_reference_candidate_01').replace('run_m367_staged_text.sh','run_m367_visual_reference.sh').replace('PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT','PASS_OFFLINE_PS_REFERENCE_AND_VIDEO_BUDGET').replace('M367_ENABLE_STAGED_LAYER','M367_ENABLE_PS_REFERENCE').replace(' $Mode B1',' $Mode PS1')
    w.atomic(w.HERE/'m367_control.ps1',control.encode('utf-8'))
    control=control.replace('M367-staged-text-02','M366-staged-text-03')
    w.atomic(w.HERE/'m367_control.ps1',control.encode('utf-8'))
    receipt=(w.HERE/'m36603_transfer_receipt.py').read_text(encoding='utf-8').replace('M366','M367').replace('m36603','m367').replace('m366','m367').replace('M367-staged-text-transfer-02','M367-PS-reference-transfer-01').replace('固定文本','PS视觉参考').replace('已冻结M367-02','已冻结M366-03').replace('只一次PS视觉参考诊断','只补缺失PS视觉参考，无Overlay或语言计算')
    w.atomic(w.HERE/'m367_transfer_receipt.py',receipt.encode('utf-8'))
    collect=(w.HERE/'m367_collect.py').read_text(encoding='utf-8')
    ast.parse(collect,feature_version=(3,10))
    import m367_collect
    negatives=m367_collect.self_test()
    assert not list(PKG.rglob('*.pyc')) and not list(PKG.rglob('__pycache__'))
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    result=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m367_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0 and 'M367_CONTROL_SELFTEST_PASS' in result.stdout,result.stdout+result.stderr
    assert 'candidates/M366-staged-text-03/PACKAGE_MANIFEST.json' in control
    r=dict(status='PASS_OFFLINE_PS_REFERENCE_AND_VIDEO_BUDGET',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),recovery_read=recovery,stable_actual_video_raw_sha256=w.sha(oldraw),prior_candidate_text_raw_sha256=pr['raw_sha256'],budget=budget,source_closure_missing=missing,python310_syntax=True,no_PYNQ_import_guard=True,PS_budget_negative_checks=rejected,collector_negative_checks=negatives,controller_failure_collect_selftest=True,fixture_checks_not_board_evidence=True,missing_reference_only=True,board_executed=False,performance_pass=False)
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.sync('latest_m367_visual_reference_preparation',dict(status=r['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M367 同视频参考与独立预算\n\n复用M345同输入完整语言参考778逻辑/实际重试，候选M366完整文本已PASS。最大视觉恢复64MiB/缓存63.61MiB/159KV44.72MiB及解包、GEMM转换、特征、32行head合并列账；视觉768MiB/全视频1024MiB PS增长监控+64MiB余量是有界停止规则，非精确原生峰值，原七缓冲后额外CMA为0，生产门槛不改。只补缺失板端PS视觉特征及原159输入组成参考，不重算完整语言基线。支持SHA `{digest}`。下一步一次纯PS参考，0Overlay/语言forward/FPGA；数值/性能尚未解锁。')
    print(json.dumps(r))


if __name__=='__main__':main()
