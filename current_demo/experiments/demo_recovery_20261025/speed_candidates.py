"""Research masks selected by frozen training proxy and measured parent phases."""
from common_recovery import *
def main():
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'))
    old=read(RUNS/'M523-fixed-demo-pruning-128-protocol-01/RESULT.json')
    winner=read(RUNS/'M523-fixed-demo-pruning-128-search-01/trials/446fd135fbce546570b1/RESULT.json')
    observed=read(RUNS/'M523-fixed-demo-pruning-128-board-saved-02/RESULT.json')
    rows=[r['values']['SAMPLE.json'] for r in observed['samples'] if r['label'] in ('VALID_B_cal_04_t1','VALID_B_cal_00_t1')]
    phase={b:sum(x[k] for x in rows)/2 for b,k in [('vision','prepare_s'),('language','prefill_s')]}
    costs=old['costs'];bank=old['base_bank']
    def cost(branch,i):return costs[branch+'_'+str(i).zfill(2)]['modelled_seconds']
    def importance(branch,i):
        b=bank[branch+'_'+str(i).zfill(2)]
        return (b['residual2']/max(b['output2'],1e-30))**.5/max(cost(branch,i),1e-9)
    candidates=[]
    for nv,nl in [(10,18),(9,20),(11,16)]:
        result=dict(name='V'+str(nv)+'L'+str(nl),quality_gate_before_research_timing=False,recovery_required=True)
        estimate={}
        for branch,count,protect in [('vision',nv,{23}),('language',nl,{0,35})]:
            original=list(p['student'][branch]);remove=sorted([i for i in original if i not in protect],key=lambda i:(importance(branch,i),-cost(branch,i),i))[:len(original)-count]
            selected=sorted(set(original)-set(remove));assert len(selected)==count
            result[branch]=selected;result['removed_'+branch]=sorted(set(range(24 if branch=='vision' else 36))-set(selected))
            estimate[branch]=phase[branch]*sum(cost(branch,i) for i in selected)/sum(cost(branch,i) for i in original)
        result.update(predicted_phase_s=estimate,predicted_TTFT_s=sum(estimate.values()),actual_board_TTFT_s=None,
                      prediction_caveat='Simple additive proxy scaled by two observed failed-candidate validation phases; not warm repeated timing, ignores fixed overhead/cache changes and quality. Actual measurement decides.')
        candidates.append(result)
    out=RUNS/(PREFIX+'-speed-candidates-01');save(out/'RESULT.json',dict(status='FROZEN_THREE_SPEED_RESEARCH_MASKS_UNMEASURED',candidates=candidates,baseline_observed_phase_s=phase,training_proxy_only=True,heldout_opened=False,board_actions=0))
    report='# 三个更快结构：仅预测，未上板\n\n原14V27L保留用于恢复链路；以下组合允许暂时错答，研究测速必须如实保存输出，最终演示仍需答案通过。选择仅用原训练代理，六test未打开。\n\n| 结构 | 视觉预测(s) | 语言预测(s) | 合计预测(s) | 实测 |\n|---|---:|---:|---:|---|\n'
    for c in candidates:report+=f"| {c['name']} | {c['predicted_phase_s']['vision']:.3f} | {c['predicted_phase_s']['language']:.3f} | {c['predicted_TTFT_s']:.3f} | 未测 |\n"
    report+='\n这是由14V27L后两条失败候选验证分项缩放得到的粗略预算，不是低于30秒证据；固定开销、缓存、解析与计算重叠会破坏按层相加的近似。完整掩码与代理依据见RESULT.json。\n'
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps(candidates,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
