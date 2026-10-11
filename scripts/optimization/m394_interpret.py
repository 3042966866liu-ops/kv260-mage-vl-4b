"""Saved-only full fixed159 video numerical and resource adjudication."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m394_collect import decode

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));e=b['latest_m394_silu_video_board'];p=ROOT/e['result']
    assert sha(p)==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    d,raw,r=decode((ROOT/'tmp/m394/component_uart.log').read_text(encoding='utf-8-sig'));assert p.read_bytes()==raw
    ok=r['status']=='PASS_M394_SILU_VIDEO_NUMERICAL' and r['gate_return_code']==0
    points=[x for x in r.get('stage_memory',[]) if x['admission'] is not None]
    memory=dict(min_checkpoint_CmaFree_MiB=min((x['memory']['system_bytes']['CmaFree'] for x in points),default=0)/2**20,
                min_checkpoint_MemAvailable_MiB=min((x['memory']['system_bytes']['MemAvailable'] for x in points),default=0)/2**20,
                max_checkpoint_RSS_growth_MiB=max((x['admission']['observed_rss_growth_bytes'] for x in points),default=0)/2**20,
                ordinary_budget_MiB=1024,ordinary_margin_MiB=64,workspace_MiB=6187008/2**20,sampled=r.get('sampled_memory'),exact_peak_proven=False)
    value=dict(status='PASS_FIXED159_VIDEO_SILU_SCOPE_ONLY' if ok else 'CLOSED_SILU_VIDEO_FAILURE',raw_sha256=d,raw_path=p.relative_to(ROOT).as_posix(),
               build_id=r['build_id'],gate_return_code=r['gate_return_code'],errors=r['errors'],scope=r.get('silu_scope'),memory=memory,
               numerical_pass=ok,new_request_performance_pass=False,production_admission_changed=False,
               next_step='Prepare lightweight balanced original expression A/workspace B full requests; preserve same input, parallel Build and one parser; no hash/export in timing; include workspace create/close' if ok else 'Stop at video failure; saved recovery only if collection fails')
    out=BASE/'runs/M394-silu-video-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m394_silu_video_closure',dict(status=value['status'],sha256=h,result=out.relative_to(ROOT).as_posix(),raw_sha256=d),
         f'## M394 SiLU固定159视频闭合（2026-10-04）\n\n{value["status"]}，原SHA {d}，闭合SHA {h}。原视觉/159输入/154family/72KV/151936logits/受限判断/778逻辑与实际物理重试、36次workspace借用/绑定/owner/七DMA释放及稳定恢复。内存{json.dumps(memory)}仅检查点与采样、非瞬时峰值/生产准入。下一步{value["next_step"]}；PS预读和双parser关闭，原硬件收益独立不变。')
    print(json.dumps(value|{'sha256':h}))

if __name__=='__main__':main()
