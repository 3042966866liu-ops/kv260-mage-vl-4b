"""Saved single-layer evidence only; never imports or calls a board runner."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m385_ps_layer_board'];path=ROOT/prior['result']
    assert sha(path)==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(path.read_text(encoding='utf-8'));passed=r['status']=='PASS_M385_PS_LAYER_NUMERICAL'
    p=r.get('ps_session',{});c=p.get('component',{});checks=p.get('independent_memory_checks',[])
    memory={}
    if checks:memory=dict(min_CmaFree_MiB=min(x['memory']['system_bytes']['CmaFree'] for x in checks)/(1<<20),min_MemAvailable_MiB=min(x['memory']['system_bytes']['MemAvailable'] for x in checks)/(1<<20),max_observed_RSS_growth_MiB=max(x['decision']['observed_rss_growth_bytes'] for x in checks)/(1<<20),budget_growth_MiB=p['budget_growth_bytes']/(1<<20),PS_payload_MiB=c['ps_payload_bytes']/(1<<20))
    value=dict(status='PASS_SINGLE_LAYER_PS_PLAN_ONLY' if passed else 'STOP_EXPANSION_AT_PS_LAYER',raw_sha256=prior['sha256'],build_id=r['build_id'],errors=r['errors'],physical_transactions=r['fpga_transactions'],layer_result=r.get('layer_result'),component=c,observed_memory=memory,sampled_memory=r.get('sampled_memory'),slot_release=p.get('slot_release'),session_weakref_dead=r.get('session_weakref_dead'),safe_buffers_released=r.get('safe_buffers_released'),stable_overlay_restored=r.get('stable_overlay_reloaded'),read_computation_overlap_schedule_enabled=passed,overlap_duration_or_speedup_proven=False,performance_pass=False,formal_promotion_allowed=False,production_admission_changed=False,next_step='Prepare independent original30-token fixed-text/36-layer/LMhead PS plan and original one parser; preserve actual physical head observation and frozen complete logits72KV reference. Only after each raw/closure triad expand fixed159 video, then lightweight interleaved same-hardware performance' if passed else 'Stop expansion; investigate only this layer capacity/lifecycle/numerical failure. Saved-byte recovery only if collection incomplete; no full-model or video retry')
    out=BASE/'runs/M385-ps-layer-closure-01';atomic(out/'RESULT.json',encoded(value),immutable=True);d=sha(out/'RESULT.json')
    report='# M385 原单层 PS 连续预读门禁\n\n'+value['status']+'，Build '+r['build_id']+'。\n\n原始SHA '+prior['sha256']+'；闭合SHA '+d+'。\n\n'+json.dumps(memory,ensure_ascii=False,indent=2)+'\n\n完整runtime与七块原DMA驻留，原layer0/159重复文本embedding，只原单解析线程；五family、hidden和一层K/V对冻结稳定参考。普通slot26.5625MiB，slot与层合计采用原独立256MiB RSS停止上限及64MiB普通可用余量，不改变生产CMA门槛；所有新增DMA申请封锁。\n\n下一窗口读取按已有PS方案在当前四端口复制同步之后提交，原family全部T32、解析和缩放重试结束后才复用CMA缓冲。本级未单独测得重叠时长或完整请求净收益，不能宣称新性能提升。\n\n'+value['next_step']+'。\n'
    atomic(out/'REPORT.md',report.encode('utf-8'))
    sync('latest_m385_ps_layer_closure',dict(status=value['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=d,raw_sha256=prior['sha256'],numerical_pass=passed,performance_pass=False),f'## M385 PS单层连续预读闭合（2026-10-03）\n\n{value["status"]}；Build{r["build_id"]}，原SHA {prior["sha256"]}，闭合SHA {d}。实际内存{json.dumps(memory)}；五family/hidden/单层KV、原重试和slot/session/七DMA生命周期，0新增DMA。预读调度允许重叠，但非重叠时长或新性能证明；旧硬件40.81%结论保持、原生产准入不改。下一步 {value["next_step"]}。')
    print(json.dumps(dict(status=value['status'],sha256=d,memory=memory,errors=r['errors'])))
if __name__=='__main__':main()
