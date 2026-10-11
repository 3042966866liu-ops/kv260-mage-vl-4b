"""Adjudicate one completed CPU component, never reruns hardware/timing."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m391_collect import decode

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m391_silu_board']
    p=ROOT/prior['result'];assert sha(p)==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    d,raw,r=decode((ROOT/'tmp/m391/component_uart.log').read_text(encoding='utf-8-sig'));assert raw==p.read_bytes()
    ok=r['gate_return_code']==0 and r['numerical_pass'] and r['component_performance_pass']
    status='PASS_SILU_COMPONENT_ONLY_INTEGRATION_NOT_PROVEN' if ok else 'CLOSED_SILU_COMPONENT_STABLE_BENEFIT_UNPROVEN'
    a=[x['ns_per_call'] for x in r['batches'] if x['variant']=='A'];b=[x['ns_per_call'] for x in r['batches'] if x['variant']=='B']
    means=dict(A_ms=sum(a)/len(a)/1e6,B_ms=sum(b)/len(b)/1e6) if a and b else {}
    if means:means['gain_pct']=(means['A_ms']-means['B_ms'])/means['A_ms']*100
    value=dict(status=status,raw_sha256=d,raw_path=p.relative_to(ROOT).as_posix(),numerical_pass=r['numerical_pass'],
               component_performance_pass=r['component_performance_pass'],means=means,groups=r.get('groups',[]),
               criteria=r.get('performance_criteria',{}),errors=r['errors'],environment=r['environment'],
               create_ms=r.get('workspace_create_ns',0)/1e6,close_ms=r.get('workspace_close_ns',0)/1e6,memory=r['memory'],
               workspace_released=r['workspace_object_and_buffer_released'],workspace_MiB=6187008/1024**2,
               model_integrated=False,full_request_performance_pass=False,formal_promotion_allowed=False,
               next_step='Prepare independent original mlp_down lifetime barrier and single-layer numeric/capacity gate; do not infer full request improvement' if ok else 'Close workspace variant at CPU component; do not expand to model or video performance')
    out=BASE/'runs/M391-silu-component-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);digest=sha(out)
    rows='\n'.join(f'| {g["round"]+1} | {g["order"]} | {g["A_ns"]/1e6:.6f} | {g["B_ns"]/1e6:.6f} | {g["gain_pct"]:.3f}% | {g["A_range_ns"]/1e6:.6f} | {g["B_range_ns"]/1e6:.6f} |' for g in value['groups'])
    report=f'''# M391 真实SiLU×up CPU组件裁决

裁决：**{status}**。这是固定159视频第一层真实gate/up上的CPU算子比较；未接入模型，不能当作完整请求提速或生产准入证据。

- 原结果SHA：`{d}`。
- 捕获来自M390原四family，当前并行Build0x4D333537，原单parser；本门禁0Overlay/模型/FPGA事务。
- 真实FP32输入159×9728，前后逐位比较与文件/张量SHA、输入不可写和身份不变核对：{r['numerical_pass']}。
- 相同各4次预热，六轮ABBA+BAAB，各批6调用；两组各144次。自然现有缓存，没有清缓存；文件加载和哈希在计时外。
- A含原astype、申请和删除；B含lease及五次ufunc out、借用释放。单工作缓冲5.900390625MiB，建立{value['create_ms']:.6f}ms、关闭{value['close_ms']:.6f}ms，另计。
- 平均单调用：{json.dumps(means,ensure_ascii=False)}。
- 严格判据：{json.dumps(value['criteria'],ensure_ascii=False)}。
- 工作缓冲对象/数组释放：{value['workspace_released']}。RSS/HWM是进程级记录，不能据此证明完整runtime峰值或内存准入；采样见RESULT。
- Python/NumPy/平台：{json.dumps(value['environment'],ensure_ascii=False)}。

| 轮次 | 顺序 | A平均ms | B平均ms | 收益 | A组内范围ms | B组内范围ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
{rows}

下一步：{value['next_step']}。

原硬件完整请求40.81%收益独立保持；PS预读和双parser关闭。原服务/准入/稳定回滚/boot/DTB/CMA不变。组件覆盖第一层这一对真实输入，不能直接外推所有36层或完整请求收益。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m391_silu_closure',dict(status=status,result=out.relative_to(ROOT).as_posix(),sha256=digest,raw_sha256=d,component_performance_pass=ok),
         f'## M391 SiLU×up真实CPU组件裁决（2026-10-04）\n\n{status}，原SHA {d}，闭合SHA {digest}，均值{json.dumps(means)}。真实数组前后逐位/48批次/12顺序组及创建/关闭/对象释放核对；仅组件，不是完整模型/视频收益或准入。下一步{value["next_step"]}。旧硬件40.81%保持，PS预读/双parser关闭，原生产源/服务/回滚不变。')
    print(json.dumps(dict(status=status,means=means,criteria=value['criteria'],result_sha256=digest,report=(out.parent/'REPORT.md').relative_to(ROOT).as_posix())))

if __name__=='__main__':main()
