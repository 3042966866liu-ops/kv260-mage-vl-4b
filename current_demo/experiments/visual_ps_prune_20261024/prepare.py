"""Freeze only PS V2/V3/V6 3072, parent240 and unchanged V2 task."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def main():
    assert not PREP.exists() and not FIT.exists() and not FEATURES.exists() and not QUALITY.exists()
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        file=ROOT/name;file.read_text(encoding='utf-8-sig');recovery[name]=dict(bytes=file.stat().st_size,sha256=sha(file))
    plan=read(PACKAGE/'TWENTYTWO_LAYER_PLAN.json');assert len(plan['layers'])==22
    manifest=read(PACKAGE/'PACKAGE_MANIFEST.json')
    assert sha(PACKAGE/'PACKAGE_MANIFEST.json')=='47a425db63d36af8c1f665dd3b19972bd0965ecfed730aa21e3defece0b42ab1'
    source=R/'M523-layer-proxy-refinement-01/RESULT.json';proxy={r['key']:r for r in read(source)['rows']};chosen=[]
    for index in (2,3,6):
        key='vision_'+str(index).zfill(2);row=proxy[key]
        candidate=next(c for c in row['primary_candidates'] if c['width']==3072 and c['score_method']=='energy')
        remove=candidate['removed_original_groups'];keep=sorted(set(range(64))-set(remove))
        assert len(remove)==16 and len(keep)==48
        chosen.append(dict(index=index,key=key,module=row['module'],width=3072,original_width=4096,
            removed_original_G64_groups=remove,kept_original_G64_groups=keep,
            proxy=candidate,proxy_limit=row['primary_proxy']))
    original=read(R/'M523-V12-native-feature-language-protocol-01/RESULT.json')
    training=read(R/'M522-training-capture-protocol-03/RESULT.json')['requests'];ids={r['id'] for r in training}
    requests=[]
    for row in original['requests']:
        requests.append({k:row[k] for k in ('id','clip_id','source_group','knife_present','phase','timestamp_index','frames','frames_sha256','features')})
    assert len(requests)==12 and sum(r['id'] in ids for r in requests)==8
    assert len({r['source_group'] for r in requests if r['id'] in ids})==4
    closure=read(CLOSURE)
    frozen={}
    def add(file,expected=None):
        assert file.is_file(),str(file)
        h=sha(file)
        if expected:assert h==expected,str(file)
        frozen[relative(file)]=h
    for file in sorted(H.glob('*.py')):
        compile(file.read_text(encoding='utf-8'),str(file),'exec');add(file)
    for file in (source,CLOSURE,PACKAGE/'PACKAGE_MANIFEST.json',PACKAGE/'TWENTYTWO_LAYER_PLAN.json',
        OPT/'contracts/config.json',OPT/'contracts/M455_COMMON_COMPLETE_REQUEST_FIVE_BLOCK_20261022_V2.json',
        OPT/'contracts/M455_RESEARCH_RELATIVE_NONREGRESSION_20261023_V1.json',
        R/'M454-model-interface-preflight-01/RESULT.json',R/'M522-training-capture-protocol-03/RESULT.json',
        R/'M523-V12-native-feature-language-protocol-01/RESULT.json',
        ROOT/'experiments/pruning_plan_20261020/M455_L1_vectors52302.py',
        ROOT/'experiments/adaptive_exec_error/adaptive/language_mlp_probe.py',
        ROOT/'experiments/adaptive_exec_error/adaptive/language_mlp_kernel_fp1602.py',
        ROOT/'experiments/speed_target_30s_20261020/generate_flap522.py'):
        add(file)
    for row in manifest['files']:add(PACKAGE/row['path'],row['sha256'])
    for row in closure['files']:add(RELEASE/row['path'],row['sha256'])
    layout=read(PARENT/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json');add(PARENT/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json')
    for row in layout['files']:add(PARENT/'vision_layout'/row['path'],row['sha256'])
    raw=read(PARENT/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');add(PARENT/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    add(PARENT/'auxiliary'/raw['blob']['path'],raw['blob']['sha256'])
    for name in ('modeling_mage_vl.py','configuration_mage_vl.py','config.json'):add(PARENT/'ps_vision_payload'/name)
    for r in requests:
        add(ROOT/r['frames'],r['frames_sha256'])
        add(ROOT/r['features']['A']['path'],r['features']['A']['sha256'])
    private=OPT/'candidates/M455-original94-layout-performance-05'
    private_manifest=private/'private_runtime/PRIVATE_RUNTIME_MANIFEST.json'
    if not private_manifest.exists():
        matches=list((private/'private_runtime').glob('*MANIFEST*.json'));assert len(matches)==1
        private_manifest=matches[0]
    add(private/'m455_private_runtime_loader01.py');add(private_manifest)
    for row in read(private_manifest)['files']:add(private/'private_runtime'/row['path'],row['sha256'])
    contract=dict(status='FROZEN_PS_V2_V3_V6_3072_ON_CURRENT22_RESEARCH',original_rc=0,selected=chosen,
        parent_package=relative(PACKAGE),parent_manifest_sha256=sha(PACKAGE/'PACKAGE_MANIFEST.json'),
        unchanged_prior_layers=22,prior_R1_unchanged=True,V12_remains_PS=True,V13_V20_original_width=True,
        quantization='Preserve signed integer codes, original FP16 scales, group orientation and BF16-origin biases; exact slicing only.',
        PS_math='Actual M273/M261/M207 source; FP32 fc1/bias, original GELU, FP32 fc2/bias; R1 FP32 post-MLP before original BF16 boundary. WSL CPU, not native A53 bit-exact.',
        R1='For each of three layers separately at parent22-propagated training inputs: FP64 mean of (original full PS MLP - cropped PS MLP), cast once to FP32 1024-vector; 8 training requests/4 groups only.',
        full_features='Both arms use same actual PS runtime; late13..23 reproduce frozen M455 A8/orderedFP32/compact-half adaptive oracle, same three late vision crops/R1; no PL migration.',
        feature_gate=dict(max_relative_L2=.02,min_global_cosine=.999,min_token_cosine=.995),
        natural_answers='Original V2 160 tokens/5T32, cap32/naturalEOS151645; same software BF16+A8 language and19 frozen language crops/R1; relative no-new-errors/misses/explanation-loss/contradictions/truncation.',
        margin='Signed correct direction on previously correct cases; zero/tie is warning, not retroactive quality FAIL; save raw full logits.',
        shared_explanation_defect=True,full_release_quality_pass=False,board_performance_pass=False,
        heldout_opened=0,training_steps=0,new_quantization=False,solver=False,board_commands=0,
        retained_board='PID42676 stopped; no commands/signals/exit/free/reset/GDB permitted by this experiment.',
        on_failure='Preserve failed batch; no automatic further layers, restoration runs, prompt/cap/group search. Report concrete evidence.',
        future_batches_not_authorized=['V4/V5/V8','2048','branch/layer deletion'],
        budgets=dict(fit_seconds=1200,feature_seconds=2400,quality_seconds=1800,feature_forward_max=24,natural_answer_max=24,total_cap_tokens=768),
        AI_generated_pilot=True,source_group_independence_limited=True)
    save(PREP/'CONTRACT.json',contract)
    p=dict(**contract,frozen=frozen,recovery_full_read=recovery,requests=requests,training_ids=sorted(ids),
        token_ids=original['token_ids'],eos_id=151645,package=relative(PACKAGE),
        private_manifest_sha256=sha(private_manifest),private_manifest_path=relative(private_manifest),
        contract_sha256=sha(PREP/'CONTRACT.json'),budget_seconds=1800,source_sha256=sha(__file__))
    assert len(p['token_ids'])==160 and p['token_ids'].count(151655)==98
    save(PREP/'RESULT.json',p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'))
    from m455456_workflow02 import synchronized
    h=sha(PREP/'RESULT.json')
    synchronized('latest_m523_PS_V236_3072_protocol01',dict(status=p['status'],result=relative(PREP/'RESULT.json'),sha256=h,board=False),
        '## M523视觉PS V2/V3/V6 3072剪枝研究冻结\n\nRESULT SHA '+h+'；以240约60秒路径的22层轻剪为父，新增三PS视觉MLP各删16原energy G64组，保持原FP32 Linear/GELU/BF16边界及22码/scale/位宽/R1。8训练/4组仅拟合1024维新R1，12cal组合特征与原V2完整自然回答；晚13–23保留M455软件算术及原三视觉裁剪。WSL非A53逐位证据，heldout封闭，0新量化/梯度/板命令。42676现场不动；读取退化恢复前不测速，不自动扩下一批。')
    print(p['status'],h,flush=True)
    print([(r['key'],r['removed_original_G64_groups']) for r in chosen],flush=True)
if __name__=='__main__':main()
