"""Freeze actual159-video gate only after exact missing visual reference closure."""
import ast
import json
import shutil
import subprocess
import sys
import m351_workflow as w
import m368_component_checks

OLD=w.BASE/'candidates/M366-staged-text-03'
PKG=w.BASE/'candidates/M368-staged-video-01'
OUT=w.BASE/'runs/M368-video-support-01'


def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Immutable video preparation exists')
    visual=w.BASE/'runs/M367-PS-reference-board-01/BOARD_RESULT.json'
    vr=json.loads(visual.read_text(encoding='utf-8'))
    assert vr['status']=='PASS_MISSING_PS_VISUAL_REFERENCE' and not vr['errors'] and vr['gate_return_code']==0
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m367_visual_reference_closure']['raw_sha256']==w.sha(visual)
    for n in ('CURRENT_STATE.md','docsMILESTONES.md'):assert w.sha(visual) in (w.ROOT/n).read_text(encoding='utf-8')
    checked=m368_component_checks.checks()
    raw=w.BASE/'runs/M345-fixed-video-board-01/BOARD_RESULT.json';assert w.sha(raw)=='b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'
    baseline=json.loads(raw.read_text(encoding='utf-8'))['passes'][0]
    keys=('input','families','token','logits','keys','values','grouped_attention_calls','logical_calls','host_calls','retry_count','retry_launches','nonfinite_detections','scale_attempts','stage_bytes','logical_expected_macros','expected_macros','language_retries','head_retries','semantic')
    closure=json.loads((OLD/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    hw=json.loads((OLD/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hw['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for row in hw['prerequisites']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    prior=w.BASE/'runs/M366-staged-text-closure-02/RESULT.json'
    assert w.sha(prior)=='ec450256bea9f4f8baf1f8b0df6c400108048ac338424a3f19e72d2adcff4b1b'
    names=('measurement.py','owned_buffer_release.py','m363_package_identity.py','m363_observers.py','m341_build_id_gate.py','frozen_video_identity.py','memory_lifecycle.py','ps_slot_capacity.py','m120_board_common.py','m120_board_env_preflight.py','board_safety.py','m363_tokenizer_once.py','SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json')
    PKG.mkdir()
    for name in names:shutil.copyfile(OLD/name,PKG/name)
    for name in ('m368_staged_video_gate.py','m368_stage_policy.py','m368_video_contract.py'):shutil.copyfile(w.HERE/name,PKG/name)
    shutil.copyfile(OLD/'m366_head_observer.py',PKG/'m368_head_observer.py')
    shutil.copyfile(prior,PKG/'STAGE_PREREQUISITE.json');shutil.copyfile(visual,PKG/'VISUAL_EXPECTED.json')
    shutil.copyfile(w.BASE/'candidates/M367-PS-visual-reference-02/VIDEO_BUDGET.json',PKG/'VIDEO_BUDGET.json')
    w.atomic(PKG/'VIDEO_EXPECTED.json',w.encoded(dict(raw_sha256=w.sha(raw),baseline={k:baseline[k] for k in keys})))
    for oldname,newname in [('m366_export_result.py','m368_export_result.py'),('run_m366_staged_text.sh','run_m368_staged_video.sh')]:
        text=(OLD/oldname).read_text(encoding='utf-8').replace('M366','M368').replace('m366','m368').replace('staged_text_02','staged_video_01').replace('staged_text_gate','staged_video_gate').replace('ENABLE_STAGED_LAYER','ENABLE_STAGED_VIDEO').replace('enable-staged-layer','enable-staged-video').replace('independent-fixed-text-capacity-diagnostic','independent-fixed159-video-capacity-diagnostic')
        w.atomic(PKG/newname,text.encode('utf-8'))
    assembly=(OLD/'m366_assemble.py').read_text(encoding='utf-8').replace('M366','M368').replace('/home/ubuntu/m366_staged_text_candidate_02','/home/ubuntu/m366_staged_text_candidate_03').replace('f3138f0d3e0c2d308329fbdbb8b9e3cc0f2a9ccf45ca3fe35fc6d73231d26484',w.sha(OLD/'PACKAGE_MANIFEST.json'))
    w.atomic(PKG/'m368_assemble.py',assembly.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m368-independent159-video-capacity-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers','m276_m254_video_server'};missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            names=[a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else ([node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [])
            missing.extend((module,n) for n in names if n not in trees and n not in allowed)
    assert not missing,missing
    assert not list(PKG.rglob('*.pyc')) and not list(PKG.rglob('__pycache__'))
    control=(w.HERE/'m36603_control.ps1').read_text(encoding='utf-8').replace('M366','M368').replace('m366','m368').replace('m36803','m368').replace('M368-staged-text-03','M368-staged-video-01').replace('M368-staged-text-support-03','M368-video-support-01').replace('M368-staged-text-transfer-02','M368-video-transfer-01').replace('M368-staged-text-02','M366-staged-text-03').replace('m368_staged_text_candidate_03','m368_staged_video_candidate_01').replace('run_m368_staged_text.sh','run_m368_staged_video.sh').replace('ENABLE_STAGED_LAYER','ENABLE_STAGED_VIDEO').replace('PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT','PASS_OFFLINE_FIXED_VIDEO_SCOPE_BUDGET_AND_SUPPORT').replace('-TimeoutSeconds 900','-TimeoutSeconds 1200')
    w.atomic(w.HERE/'m368_control.ps1',control.encode('utf-8'))
    receipt=(w.HERE/'m36603_transfer_receipt.py').read_text(encoding='utf-8').replace('M366','M368').replace('m36603','m368').replace('m366','m368').replace('M368-staged-text-transfer-02','M368-video-transfer-01').replace('固定文本','159视频').replace('已冻结M368-02','已冻结M366-03').replace('不自动文本/视频','不自动性能')
    w.atomic(w.HERE/'m368_transfer_receipt.py',receipt.encode('utf-8'))
    collect=(w.HERE/'m36603_collect.py').read_text(encoding='utf-8').replace('M366','M368').replace('m366','m368').replace('M368-staged-text-03','M368-staged-video-01').replace('M368-staged-text-board-02','M368-staged-video-board-01').replace('independent-fixed-text-capacity-diagnostic','independent-fixed159-video-capacity-diagnostic').replace('PASS_M368_FIXED_TEXT_DIAGNOSTIC','PASS_M368_FIXED_VIDEO_DIAGNOSTIC').replace('LAYER_EXPECTED','VIDEO_EXPECTED').replace('layer_result','video_result')
    collect=collect.replace("        if r['model_forward_calls']!=1 or not all(r['exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Layer coverage differs')", "        if r['model_forward_calls']!=1 or r['vision_forward_calls']!=1 or not all(r['exact_comparison'].values()) or not all(r['visual_exact_comparison'].values()) or r['blocked_inference_attempts']:raise ValueError('Video coverage differs')")
    collect=collect.replace('完整runtime对象保留，原30-token文本/36层/完整head，非视频','完整runtime对象保留，原159-token视频/视觉/36层/完整head').replace('先固定文本解读并同步，真实视频需独立论证与新包，不能自动扩大','先视频裁决并同步；通过后才可准备轻量交错完整请求性能')
    w.atomic(w.HERE/'m368_collect.py',collect.encode('utf-8'))
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    c=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m368_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert c.returncode==0 and 'M368_CONTROL_SELFTEST_PASS' in c.stdout,c.stdout+c.stderr
    ast.parse(collect,feature_version=(3,10))
    assert 'candidates/M366-staged-text-03/PACKAGE_MANIFEST.json' in control
    r=dict(status='PASS_OFFLINE_FIXED_VIDEO_SCOPE_BUDGET_AND_SUPPORT',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),policy_and_reference_checks=checked,source_closure_missing=missing,python310_syntax=True,visual_raw_sha256=w.sha(visual),stable_video_raw_sha256=w.sha(raw),fixed_text_closure_sha256=w.sha(prior),reused_head_observer_actual_frozen_executor_support_sha256='5cbc726714c01d38339e823fa3da382f2e292f0dc21d2b7f00e98f5df81f5379',same_sha_hardware_prerequisites=True,controller_failure_collected=True,extra_CMA_bytes=0,PS_growth_limit_bytes=1024<<20,MemAvailable_margin_bytes=64<<20,production64MiB_unchanged=True,native_peak_certified=False,board_executed=False,performance_pass=False)
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.sync('latest_m368_video_support',dict(status=r['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M368 真实159视频独立诊断准备\n\n原M276四源帧最后一帧两224视图、98视觉token/159输入、权重/数学不变。复用M345完整稳定语言参考及M367缺失PS视觉参考；778逻辑/实际重试，154family/72KV/full logits/判断、原7缓冲释放和稳定重载。独立1024MiB PS增长+64MiB余量、额外CMA0，生产门槛不改。{checked}项政策/参考正负例及同SHA硬件/实际head观察器证据复用，支持SHA `{digest}`。尚未执行，下一步只一次视频数值诊断；性能未解锁。')
    print(json.dumps(r))


if __name__=='__main__':main()
