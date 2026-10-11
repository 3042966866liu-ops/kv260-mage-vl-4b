"""Exact derivative of previously passed M368 lifecycle, no visual execution."""
import ast, json, shutil
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M415-saved-feature-language-01'
OLD=BASE/'candidates/M368-staged-video-03'

def once(s,a,b):
    if s.count(a)!=1:raise ValueError('Derivation anchor differs: '+a[:100])
    return s.replace(a,b)

def main():
    if PKG.exists():raise RuntimeError('Immutable preparation exists')
    recovery={n:dict(sha256=sha(ROOT/n),full_read=True,characters=len((ROOT/n).read_text(encoding='utf-8-sig'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites={}
    for key in ('latest_m414_layer12_visual_board','latest_m414_layer12_visual_closure','latest_m368_video_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prerequisites[key]=row
    oldhash=sha(OLD/'PACKAGE_MANIFEST.json');assert oldhash=='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66'
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    hardware=json.loads((OLD/'HARDWARE_CLOSURE.json').read_bytes())
    for row in hardware['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for name in ('SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json'):
        closure=json.loads((OLD/name).read_bytes())
        for row in closure['files']:assert sha(release/row['path'])==row['sha256']
    raw=json.loads((ROOT/prerequisites['latest_m414_layer12_visual_board']['result']).read_bytes())
    assert raw['feature_quality_pass'] and raw['stable_restored'] and raw['safe_buffers_released']
    plan=dict(prerequisites=prerequisites,M414_raw_sha256=prerequisites['latest_m414_layer12_visual_board']['sha256'],features=raw['retained_visual_features'],
        feature_directory='/home/ubuntu/m414_layer12_full_visual_01',reuse_package='/home/ubuntu/m368_staged_video_candidate_03',reuse_manifest_sha256=oldhash,
        selected_layers=[12],language_build='0x4D333537',stable_build='0x4D395832',actual_visual_forwards=0,
        variants=['original','layer12_candidate'],prompt='M276_KNIFE_PROMPT unchanged',timestamp_seconds=3.0,prompt_tokens=159,views=2,last_frame_index=3,
        output_budget=1,decode_calls=0,logical_calls_each=778,physical_calls='778 plus recorded adaptive retries; 1 separate legal minimal',
        DMA_sizes=[6963200]*4+[389152,2621440,2621440],new_DMA_after_seal=0,CMA_fixed_floor=None,
        ordinary_growth_limit_bytes=1024<<20,ordinary_available_reserve_bytes=64<<20,
        quality_rule='Original all reference outputs exact. Candidate all finite full logits/KV/families and unchanged constrained knife decision. Distances and score change recorded, not tuned into an acceptance threshold.',
        ground_truth='Not independently labeled; one-input original/candidate consistency only',
        excluded_quality_claims=['motion direction','object category','spatial location','dataset accuracy'],
        expand_layers=False,performance_measurement=False,production_source_changed=False)
    # Local source is the exact immutable payload previously executed on the board.
    s=(OLD/'m368_staged_video_gate.py').read_text(encoding='utf-8')
    identity=s[s.index('        identity_path='):s.index('        prior=json.loads')]
    s=once(s,identity,"        from m415_saved_features import load_features\n        plan=json.loads((HERE/'PLAN.json').read_bytes())\n        features,feature_ids=load_features(plan)\n        result['saved_feature_identities']=feature_ids\n        result['features_verified_before_overlay']=True\n")
    start=s.index('            def __call__(self,*a,**kw):',s.index('        class ObservedVision'))
    end=s.index('        language_cls =',start)
    s=s[:start]+"            def __call__(self,*a,**kw):\n                result['vision_forward_calls']=result.get('vision_forward_calls',0)+1\n                raise RuntimeError('Saved-feature gate forbids visual forward')\n"+s[end:]
    start=s.index("        expected=json.loads((HERE/'VIDEO_EXPECTED.json')")
    end=s.index("        result['boot_unchanged']",start)
    s=s[:start]+"        from m415_trials import run\n        phase[0]='saved-feature-language-original-then-layer12'\n        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features)\n        result['status']='PASS_M415_SAVED_FEATURE_DECISION_CONSISTENCY'\n        features.clear()\n"+s[end:]
    # Fail any source instrumentation incompatibility before Overlay/DMA.
    anchor="        policy=StagePolicy(result,lambda:runtime,base)"
    check="        import inspect,textwrap\n        from m368_head_observer import instrument_source\n        from m230_prefill_runtime import M230PrefillRuntime\n        instrument_source(textwrap.dedent(inspect.getsource(M230PrefillRuntime._execute)))\n        result['head_AST_checked_before_overlay']=True\n"
    s=once(s,anchor,check+anchor)
    s=once(s,"from m368_stage_policy import StagePolicy,SHAPES","from m368_stage_policy import SHAPES\nfrom m369_light_policy import StagePolicy")
    s=s.replace('PASS_M368_FIXED_VIDEO_DIAGNOSTIC','PASS_M415_SAVED_FEATURE_DECISION_CONSISTENCY')
    s=s.replace('M368_HEARTBEAT','M415_HEARTBEAT').replace('M368_MEMORY','M415_MEMORY').replace('M368_FAILURE_OR_COMPLETION_STATE','M415_FAILURE_OR_COMPLETION_STATE').replace('M368_RESULT_SAVED','M415_RESULT_SAVED')
    s=s.replace("Path('/home/ubuntu/m368_staged_video_02')/args.case","Path('/home/ubuntu/m415_saved_feature_language_01')")
    s=s.replace("path = EVIDENCE / 'load-memory.json'","path = EVIDENCE / 'BOARD_RESULT.json'")
    s=s.replace('independent-fixed159-video-capacity-diagnostic','saved-feature-fixed159-language-quality')
    s=s.replace('Original complete runtime objects retained; independent fixed159-token diagnostic including36 layers/head, no extra CMA/PS slot; original visual plus language and head; production policy unchanged','Original complete runtime objects retained; two immutable saved features through unchanged language/head; no visual forward, no extra CMA/PS slot; no performance or layer expansion')
    s=once(s,"            from m368_export_result import emit_saved\n            emit_saved(args.case)","            from m415_export import emit_saved\n            emit_saved()")
    s=s.replace('Balanced full-request performance','Saved-feature quality').replace('Independent video adjudication; balanced full-request performance only after exact output and lifecycle PASS synchronized','Close saved-feature decision consistency; no automatic expansion or performance')
    # Bootstrap validates the entire reused CPU support package before imports.
    bootstrap="""import hashlib,json,sys
from pathlib import Path
reuse=Path('/home/ubuntu/m368_staged_video_candidate_03')
if hashlib.sha256((reuse/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()!='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66':raise RuntimeError('Reused package SHA differs')
reuse_manifest=json.loads((reuse/'PACKAGE_MANIFEST.json').read_bytes())
for entry in reuse_manifest['files']:
    p=reuse/entry['path']
    if p.is_symlink() or p.stat().st_size!=entry['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Reused payload differs')
sys.path.insert(1,str(reuse))
"""
    s=once(s,'from measurement import sha256, write_json',bootstrap+'from measurement import sha256, write_json')
    PKG.mkdir()
    atomic(PKG/'m415_gate.py',s.encode('utf-8'),immutable=True)
    for name in ('m415_saved_features.py','m415_trials.py','m415_export.py','m415_assemble.py'):
        atomic(PKG/name,(HERE/name).read_bytes(),immutable=True)
    atomic(PKG/'m369_light_policy.py',(BASE/'candidates/M369-light-video-01/m369_light_policy.py').read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    for name in ('STAGE_PREREQUISITE.json','VISUAL_EXPECTED.json','VIDEO_EXPECTED.json','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json'):
        atomic(PKG/name,(OLD/name).read_bytes(),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m415_export.py"; exit 0; fi
[[ $2 == Run && ${M415_ENABLE_SAVED_FEATURES:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m415_saved_feature_language_01 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m415_gate.py" "$1" B1 --enable-staged-video
task_gate_rc=$?
"$task_python" -B "$task_dir/m415_export.py"
task_export_rc=$?
set -e
echo "M415_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    atomic(PKG/'run_m415.sh',runner.encode('utf-8'),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    names=sorted(p.name for p in PKG.iterdir())
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(PKG/n)}  {n}\n' for n in names).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    r=dict(status='PASS_M415_SAVED_FEATURE_LANGUAGE_PREPARATION_ONLY',recovery=recovery,prerequisites=prerequisites,
           manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],
           plan=plan,source_derivation=dict(original_gate_sha256=sha(OLD/'m368_staged_video_gate.py'),derived_gate_sha256=sha(PKG/'m415_gate.py'),
                original_35_asset_checks_preserved=True,source_49_SHA_preserved=True,original_M238_M241_math_preserved=True,head_AST_check_before_overlay=True,actual_visual_forward_blocked=True),
           board_run=False,numerical_pass=False,decision_consistency_pass=False,accuracy_proven=False,performance_pass=False)
    out=BASE/'runs/M415-saved-feature-preparation-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m415_saved_feature_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
         f'## M415 保存视觉特征接原语言路径准备（2026-10-06）\n\nSHA {sha(out)}；只读取已保存M414两份98×2560 FP32特征，0视觉前向。共用原M238/M241语言及0x4D333537核、159原提示IDs、单token刀具0/1；先原版全部logits/72KV/family/retry/判定逐位参考，再候选完整有限输出与原判定一致，logits及分数差只记录，无阈值拟合。七块原DMA封锁新增，无CMA64固定门槛，普通PS1024MiB增长+64MiB余量；原35SHA/49源、head AST前移分配之前。未上板、无数据集准确率/对象类别/空间位置/运动方向/扩层/性能。组件/回收检查完成后一次执行。')
    print('M415_PREPARATION_SYNC',sha(out),r['manifest_sha256'],m['file_count'],m['total_bytes'])

if __name__=='__main__':main()
