"""Freeze bounded combination question after the two local net-gain gates."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());keys=('latest_m419_complete_mlp_board03','latest_m419_complete_mlp_closure03','latest_m412_complete_mlp_closure','latest_m414_layer12_visual_closure','latest_m415_saved_feature_language_closure','latest_m417_reference_closure02','latest_m418_visual_lower_closure')
    for k in keys:
        e=b[k];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads((ROOT/b['latest_m419_complete_mlp_board03']['result']).read_bytes());assert r['numerical_pass'] and r['performance_pass'] and r['stable_restored'] and len(r['allocations'])==len(r['releases'])==19
    v=dict(status='PLANNED_M420_BOUNDED_LAYERS12_13_FEATURE_QUALITY',selected_layers=[12,13],prerequisites={k:b[k]['sha256'] for k in keys},
        protocol=dict(original_visual_calls=1,software_combination_visual_calls=1,PL_combination_visual_calls=1,language_calls=0,
            same_fixed_original_A_required=True,both_original_layer_captures_exact_before_Overlay=True,
            software_reference_uses_actual_changed_layer13_input=True,all52_wire_batches_exact=True,software_PL_complete_features_bit_equal=True,
            final_feature_thresholds=dict(maximum_relative_l2=.02,minimum_cosine=.999,minimum_token_cosine=.995),
            samples_or_performance_claim=False,extra_runs=False),
        DMA_payload_bytes=3440656,reuse_same_seven_buffers_sequentially=True,new_DMA_sealed_after_allocation=True,fixed_CMA_floor=None,
        ordinary_RSS_growth_budget_bytes=768<<20,ordinary_MemAvailable_reserve_bytes=64<<20,
        preserved=['original last-frame two views','Attention','GELU','normalization','other22 visual layers','language','stable rollback','production admission'],
        feature_screen_not_semantic_accuracy=True,expanded_24_layers=False,board_run=False,
        stop='Any fixed original mismatch, dynamic reference/wire mismatch, final feature rejection, actual allocation or lifecycle failure stops this combination level; no larger subset.')
    out=BASE/'runs/M420-combination-plan-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m420_combination_plan',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),f'## M420 仅12＋13完整视觉组合计划（2026-10-06）\n\nSHA {sha(out)}；第13层完整MLP局部数值与30.65%净时间、释放和稳定恢复闭合后，只新增13至12组合。固定原版A及两层原capture前置核对；软件组合按实际改变后的13输入生成全部52 packet/raw，PL组合及完整特征逐位对照，再原98×2560阈值筛选。三次视觉/0语言/0性能样本，七DMA复用且封锁新增、原普通768MiB预算，未扩24层，尚未执行。')
    stage=ROOT/'tmp/m42001/component_stage';stage.mkdir(parents=True,exist_ok=True)
    for name in ('m420_combination.py','test_m420_combination.py'):atomic(stage/name,(HERE/name).read_bytes(),immutable=True)
    # This checker runs in isolated WSL with the clean stage and frozen reference package only.
    checker='''import json,sys\nfrom pathlib import Path\nroot=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')\nassert sys.flags.isolated\nstage=root/'tmp/m42001/component_stage'\nref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'\nsys.path[:0]=[str(stage),str(ref)]\nimport torch\nfrom m414_entry import run_component\nfolder=root/'tmp/m42001/component';folder.mkdir(parents=True,exist_ok=True)\nvalue,isolation=run_component(root,folder,stage/'test_m420_combination.py')\nassert isolation['parent_state_unchanged'] and isolation['return_code']==0\nwith (folder/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(dict(status='PASS_M420_CLEAN_DYNAMIC_COMBINATION_COMPONENT',component=value,isolation=isolation,no_developer_directory_on_child_path=True,board_run=False),f,indent=2)\nprint('M420_CLEAN_DYNAMIC_COMPONENT_PASS')\n'''
    atomic(stage/'check.py',checker.encode('utf-8'),immutable=True)
    print('M420_PLAN_SYNC',sha(out))

if __name__=='__main__':main()
