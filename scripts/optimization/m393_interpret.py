"""Saved-only fixed-text closure."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m393_collect import decode

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m393_silu_text_board'];p=ROOT/prior['result']
    assert sha(p)==prior['sha256'] and all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    d,raw,r=decode((ROOT/'tmp/m393/component_uart.log').read_text(encoding='utf-8-sig'));assert raw==p.read_bytes()
    ok=r['status']=='PASS_M393_SILU_TEXT_NUMERICAL' and not r['gate_return_code']
    points=[x for x in r.get('stage_memory',[]) if x['admission'] is not None]
    memory=dict(min_CmaFree_MiB=min((x['memory']['system_bytes']['CmaFree'] for x in points),default=0)/2**20,
                min_MemAvailable_MiB=min((x['memory']['system_bytes']['MemAvailable'] for x in points),default=0)/2**20,
                max_observed_RSS_growth_MiB=max((x['admission']['observed_rss_growth_bytes'] for x in points),default=0)/2**20,
                diagnostic_stop_budget_MiB=256,workspace_MiB=1167360/2**20,sampled_memory=r.get('sampled_memory'))
    value=dict(status='PASS_FIXED_TEXT_SILU_SCOPE_ONLY' if ok else 'CLOSED_SILU_TEXT_FAILURE',raw_sha256=d,raw_path=p.relative_to(ROOT).as_posix(),
               build_id=r['build_id'],gate_return_code=r['gate_return_code'],errors=r['errors'],scope=r.get('silu_scope'),memory=memory,
               production_policy_changed=False,video_numeric_proven=False,new_request_performance_pass=False,
               next_step='Freeze original fixed159 video numeric gate with same Prefill scope and full video1GiB ordinary stop budget; no performance until full video outputs/lifetime exact' if ok else 'Stop at failed fixed text; no video expansion')
    out=BASE/'runs/M393-silu-text-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);digest=sha(out)
    sync('latest_m393_silu_text_closure',dict(status=value['status'],sha256=digest,result=out.relative_to(ROOT).as_posix(),raw_sha256=d),
         f'## M393 SiLU固定文本闭合（2026-10-04）\n\n{value["status"]}，原SHA {d}，闭合SHA {digest}；原30Token/36层/完整head/logits/72KV及162逻辑/165物理+最小/3语言保护重试，36次SiLU scope及owner/绑定/七DMA释放、稳定恢复。内存{json.dumps(memory)}仅检查点/采样，非瞬时峰值或准入。下一步{value["next_step"]}；PS预读/双parser关闭，旧硬件收益独立保持。')
    print(json.dumps(value|{'result_sha256':digest}))

if __name__=='__main__':main()
