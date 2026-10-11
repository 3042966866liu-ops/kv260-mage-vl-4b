"""Immutable range protocol/isolated oracle component; no board I/O."""
import ast,hashlib,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M426-all-FP32-MLP-software-01'

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    required=('latest_m425_warm_closure','latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board')
    verified={}
    for key in required:
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        verified[key]=e
    closure=json.loads((ROOT/verified[required[0]]['result']).read_bytes())
    assert closure['status']=='NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_VARIANT' and closure['performance_pass'] is False
    origin=BASE/'candidates/M420-layers12-13-full-visual-02';oldplan=json.loads((origin/'PLAN.json').read_bytes())
    source=BASE/'candidates/M417-layer13-saved-reference-02'
    plan=dict(selected_layers=list(range(2,24)),candidate_PL_enabled=False,temperature_measurement_enabled=False,
        default_off=True,visual_calls=2,language_calls=0,rows=392,budget_seconds=4200,
        reused_packages=oldplan['reused_packages'],resolved_module_names=oldplan['resolved_module_names'],
        prerequisites=[dict(path='/home/ubuntu/m420_combination_visual_02/BOARD_RESULT.json',sha256=verified['latest_m420_combination_board']['sha256'])],
        feature_thresholds=dict(maximum_relative_l2=.02,minimum_cosine=.999,minimum_token_cosine=.995),
        software_math='Unchanged M409 ordered FP32 group products/accumulation, scale-first A8, exact T32, FP16+FTZ, adaptive shifts, original FP32 PS bias and GELU.',
        performance_branch_closed_sha256=verified[required[0]]['sha256'],
        task_required_after_feature_pass='Saved candidate feature through unchanged original language; same159-token knife prompt/max_new1. Compare complete logits, constrained ABSENT/PRESENT and token against saved original M421; fixed-input consistency only, no labeled accuracy.',
        task_complete=False,hardware_visual_timing_unlocked=False,full_request_timing_unlocked=False,
        maximum_automatic_candidates=1,
        failure_next_step='If all22 complete features or task fail, freeze one smaller partition/localization protocol against the same fixed original before executing. Do not change thresholds, mix two-layer references, or measure failed ranges.',
        ordinary_growth_budget_bytes=768<<20,ordinary_available_reserve_bytes=64<<20,fixed_CMA_floor=None,
        history_retention='24 original BF16 boundary matrices converted to FP32, saved to disk; candidate streamed one boundary at a time. One active MLP window scope; retain hashes/batch metadata, never wire payload history.',
        unchanged=['BF16 layers0-1','Attention','GELU','normalization','original input/views','language','cache policy','thread policy','stable RTL/service/boot/DTB/CMA'])
    layout_path=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
    layout=json.loads(layout_path.read_bytes());entries={e['module']:e for e in layout['modules']}
    from m407_mlp_contract import chain_for
    plan['layout_sha256']=sha(layout_path);plan['chains']={};plan['windows']={}
    for index in plan['selected_layers']:
        chains={};windows={}
        for j,part in enumerate(('fc1','fc2')):
            chain=chain_for(entries[f'model.visual.encoder.layers.{index}.mlp.{part}'],index*2+j)
            assert chain['groups']==(16 if part=='fc1' else 64) and chain['stage_bytes_per_shard']==557056
            chains[part]=chain;windows[part]=[]
            for row in layout['files']:
                path=layout_path.parent/row['path'];assert path.stat().st_size==row['bytes']
                with path.open('rb') as f:f.seek(chain['stage_base_words']*16);raw=f.read(chain['stage_bytes_per_shard'])
                assert len(raw)==chain['stage_bytes_per_shard']
                windows[part].append(dict(path=row['path'],offset=chain['stage_base_words']*16,bytes=len(raw),file_bytes=row['bytes'],sha256=hashlib.sha256(raw).hexdigest()))
        plan['chains'][str(index)]=chains;plan['windows'][str(index)]=windows
    for row in layout['files']:assert sha(layout_path.parent/row['path'])==row['sha256']
    # Verify the selected precision policy through the frozen actual inheritance,
    # not the historical M207 class's original six-layer prefix.
    frozen=json.loads((BASE/'candidates/M423-integrated-video-01/SOURCE_CLOSURE.json').read_bytes())
    counterparts={}
    for row in frozen['files']:
        p=ROOT/row['path']
        if not p.exists():
            p=ROOT/'release_staging/kv260-mage-vl-4b'/row['path']
            counterparts[row['path']]=p.relative_to(ROOT).as_posix()
        assert sha(p)==row['sha256']
    policy=ROOT/frozen['modules']['m258_vectorized_w4_runtime'];policy_text=policy.read_text(encoding='utf-8')
    assert 'self.FP32_LAYERS = tuple(range(prefix, 24))' in policy_text and 'bf16_prefix=2' in policy_text
    costs_path=BASE/'runs/M406-vision-cost-board-02/BOARD_RESULT.json';costs=json.loads(costs_path.read_bytes())
    rows=[r for r in costs['costs']['rows'] if any(r['name']==f'encoder.layers.{i}.mlp.{part}' for i in plan['selected_layers'] for part in ('fc1','fc2'))]
    categories=('linear_weight_restore','linear_operand_conversion','linear_gemm','linear_output_conversion')
    cost={k:sum(r['exclusive_ns'] for r in rows if r['category']==k)/1e9 for k in categories}
    audit=dict(status='FROZEN_ALL22_FP32_MLP_SOFTWARE_RANGE_PROTOCOL',two_layer_performance_branch_closed=True,
        prior_correctness_lifecycle_reused=verified,selected_layers=plan['selected_layers'],selected_MLP_fraction_of_all24=22/24,
        logical_reference_calls=572,peak_live_window_bytes=4456448,original_boundary_disk_bytes=24*392*1024*4,
        M406_context_only_cost=cost,M406_raw_sha256=sha(costs_path),cost_not_net_savings=True,verified_local_source_counterparts=counterparts,
        offline_rejection_preserved='Initial audit refused missing workspace scripts/preflight.py; v2 counterpart then refused SHA mismatch. Both before any evidence/resources. Exact original release_staging/kv260-mage-vl-4b counterparts verified by SHA; board checks installed original paths.',
        plan=plan,source_policy_sha256=sha(policy),board_run=False,feature_screen_pass=False,task_screen_pass=False,
        hardware_visual_timing_unlocked=False,performance_pass=False,formal_promotion_allowed=False)
    out=BASE/'runs/M426-range-protocol-01/RESULT.json';atomic(out,encoded(audit),immutable=True)
    sync('latest_m426_range_protocol',dict(status=audit['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),performance_pass=False,board_run=False),
        f'## M426 结束两层性能分支，冻结22层软件质量筛查（2026-10-06）\n\nSHA {sha(out)}；M425原裁决不改、不追加样本，M420/M421正确性与生命周期复用。当前实际M258前2层BF16、2–23共22层FP32，仅两个MLP Linear按已有精确A8/FP16/FTZ软件参考替换，Attention/GELU/归一化/语言不改。572逻辑参考批次，逐层暂存峰值4.25MiB，24边界原版保存磁盘、候选流式比较；0Overlay/DMA/语言/测温。原完整特征阈值不变，原始板端feature SHA必须先对齐；完整特征和后续保存特征任务判断两项成立才解锁视觉硬件计时，尚未执行或证明质量/提速。')
    report='# M426 较大视觉MLP范围筛查协议\n\n两层性能分支结束；原M425裁决及M420/M421正确性证据保留。\n\n首轮范围为第2–23层（22/24个视觉MLP），每层仅fc1/fc2替换为已有完整精确软件参考；原偏置、GELU、Attention、归一化、BF16边界不变。392行仍按12×32＋8批处理，共572逻辑参考调用。\n\n完整特征沿用relative L2≤0.02、cosine≥0.999、最差token cosine≥0.995；逐层边界误差用于定位，不改阈值以获得通过。首先核对固定原版feature SHA，误差必须经过完整后续网络累计。\n\n特征通过后，复用保存特征接入原语言路径检查完整logits及原固定knife判断；现有样例只提供固定输入一致性，不提供独立标注准确率。未取得任务证据前，不能宣布范围质量通过或上板计时。若失败，先冻结较小范围定位方案，不能直接扩层或反复加测。\n\n本次无Overlay、DMA、语言或性能运行。不读温度、不清缓存。只同时保留一个层的权重窗口，不保存历史packet/raw/诊断张量。\n\n原M406成本仅用于范围价值估计：\n```json\n'+json.dumps(cost,indent=2)+'\n```\n这些CPU成本不是可兑现的净节省，完整视觉净耗时仍需质量通过后的硬件验证。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    stage=ROOT/'tmp/m42601/component_stage';stage.mkdir(parents=True,exist_ok=False)
    for name in ('m426_range.py','test_m426_range.py'):atomic(stage/name,(HERE/name).read_bytes(),immutable=True)
    entry="import sys,json\nfrom pathlib import Path\nassert sys.flags.isolated\nroot=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')\nstage=root/'tmp/m42601/component_stage';ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'\nsys.path[:0]=[str(stage),str(ref)]\nimport torch\ntorch.set_num_threads(1)\nfrom test_m426_range import component\nprint('M426_COMPONENT='+json.dumps(component(root)),flush=True)\n"
    atomic(stage/'entry.py',entry.encode('utf-8'),immutable=True)
    print('M426_PROTOCOL_SYNC',sha(out),json.dumps(cost));print('M426_COMPONENT_STAGE_READY')

if __name__=='__main__':main()
