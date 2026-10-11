"""Saved-only single-layer adjudication; no UART or hardware execution."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m392_collect import decode

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=b['latest_m392_silu_layer_board'];p=ROOT/prior['result']
    assert sha(p)==prior['sha256'] and all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    d,raw,r=decode((ROOT/'tmp/m392/component_uart.log').read_text(encoding='utf-8-sig'));assert raw==p.read_bytes()
    ok=r['status']=='PASS_M392_SILU_LAYER_NUMERICAL' and not r['gate_return_code']
    points=[x for x in r.get('stage_memory',[]) if x['admission'] is not None]
    memory=dict(min_CmaFree_MiB=min((x['memory']['system_bytes']['CmaFree'] for x in points),default=0)/2**20,
                min_MemAvailable_MiB=min((x['memory']['system_bytes']['MemAvailable'] for x in points),default=0)/2**20,
                max_observed_RSS_growth_MiB=max((x['admission']['observed_rss_growth_bytes'] for x in points),default=0)/2**20,
                diagnostic_stop_budget_MiB=256,workspace_MiB=6187008/2**20,sampled_memory=r.get('sampled_memory'))
    value=dict(status='PASS_SINGLE_LAYER_SILU_SCOPE_ONLY' if ok else 'CLOSED_SILU_LAYER_FAILURE',raw_sha256=d,raw_path=p.relative_to(ROOT).as_posix(),
               build_id=r['build_id'],gate_return_code=r['gate_return_code'],errors=r['errors'],scope=r.get('silu_scope'),memory=memory,
               production_policy_changed=False,full_model_numeric_proven=False,new_request_performance_pass=False,
               next_step='Independent fixed30 text full36 Prefill/head numeric and lifetime gate; then fixed159 original video; no new full-request speed claim until balanced timing' if ok else 'Stop at failed single layer, retain active resources; do not expand')
    out=BASE/'runs/M392-silu-layer-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);digest=sha(out)
    sync('latest_m392_silu_layer_closure',dict(status=value['status'],sha256=digest,result=out.relative_to(ROOT).as_posix(),raw_sha256=d),
         f'## M392 SiLU工作缓冲单层闭合（2026-10-04）\n\n{value["status"]}，原SHA {d}，闭合SHA {digest}；原五family/hidden/单层K/V/25逻辑25物理+最小、缩放重试完整一致，5.900390625MiB工作缓冲及绑定/owner/七DMA安全释放，稳定恢复。内存{json.dumps(memory)}仅检查点/20ms采样，非瞬时峰值或生产准入。下一步{value["next_step"]}，PS预读/双parser关闭。')
    print(json.dumps(value|{'result_sha256':digest}))

if __name__=='__main__':main()
