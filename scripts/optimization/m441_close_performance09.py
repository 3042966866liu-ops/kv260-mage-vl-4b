"""Adjudicate only synchronized saved M437 bytes, no board I/O or extra runs."""
import json,statistics
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_performance_collect09 import check
from m437_sequence import adjudicate

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m441_complete_request_board'];path=ROOT/e['result']
    assert sha(path)==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=check(json.loads(path.read_bytes()));samples=r.get('samples',[])
    if r['status']=='PASS_M441P_NATURAL_IO_MEASUREMENTS_COLLECTED':
        verdict=adjudicate(r['formal_samples'])
    else:
        verdict=dict(status='CLOSED_M437_EXPERIMENT_CONDITIONS_NOT_ESTABLISHED' if r.get('experiment_stop') else 'CLOSED_M437_ORIGINAL_GATE_FAILURE',performance_pass=False,experiment_stop=r.get('experiment_stop'),errors=r['errors'],additional_samples_allowed=False)
    group_stages={}
    for variant in ('A','B'):
        rows=[s for s in r.get('formal_samples',[]) if s['variant']==variant]
        if rows:group_stages[variant]={k:dict(mean_ms=statistics.mean(s['timing']['stages_ms'][k] for s in rows),range_ms=max(s['timing']['stages_ms'][k] for s in rows)-min(s['timing']['stages_ms'][k] for s in rows)) for k in ('preprocess','vision','prefill','head')}
    result=dict(raw_result=e['result'],raw_sha256=e['sha256'],build_id='0x4D343431',temperature_measurement_enabled=False,completed_requests=len(samples),formal_requests=len(r.get('formal_samples',[])),stage_summary=group_stages,
                numerical_pass=r.get('numerical_pass',False),safe_buffers_released=r.get('safe_buffers_released',False),stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),
                performance_scope='Fixed159 last-frame two-view resident-runtime requests including natural I/O; both accepted MLP13..23 PL visual; A original M357 vs B new M441 kernel, single parser.',
                semantic_accuracy_proven=False,expanded_layers=False,production_promoted=False,source_sha256=sha(HERE/'m441_close_performance09.py'))
    result.update(verdict)
    folder=BASE/'runs/M441-complete-request-closure-09';out=folder/'RESULT.json';atomic(out,encoded(result),immutable=True)
    report='# M441 同视觉路径的新旧核完整请求对照\n\n'+result['status']+'。原始SHA：'+e['sha256']+'。\n\n'
    report+='A为原M357；B为新M441，两边均将第13–23层的两个MLP Linear放在对应PL核。核切换和合法最小证明在请求计时外。两版同输入、提示、原语言路径和七块驻留DMA；无新增层/预读/双解析/末层跳批。温度不读取、不用作判据。原计时内包含候选暂存、传输、解析和绑定关闭；全特征、logits、72份KV和事务哈希在计时后核对。\n\n'
    report+='| 阶段序号 | 版 | 完整请求s | 视觉s | 语言Prefill s | LM head s（包含在Prefill） | 读盘MiB | major faults | RSS前/后MiB |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for s in samples:
        t=s['timing'];stage=t['stages_ms'];mem=[]
        for side in ('before_memory','after_memory'):mem.append(s.get(side,{}).get('process_bytes',{}).get('VmRSS',0)/(1<<20))
        report+=f'| {s.get("phase", "completed")} {s.get("phase_index",s["index"])} | {s["variant"]} | {t["total_ms"]/1000:.6f} | {stage["vision"]/1000:.6f} | {stage["prefill"]/1000:.6f} | {stage["head"]/1000:.6f} | {s["io_delta"]["read_bytes"]/(1<<20):.6f} | {s["major_fault_delta"]} | {mem[0]:.2f}/{mem[1]:.2f} |\n'
    if 'blocks' in verdict:
        report+='\n| 顺序 | A平均s | B平均s | 净差s | 下降比例 | A组内极差s | B组内极差s |\n|---|---:|---:|---:|---:|---:|---:|\n'
        for v in verdict['blocks']:report+=f'| {v["order"]} | {v["A_mean_ms"]/1000:.6f} | {v["B_mean_ms"]/1000:.6f} | {v["gain_ms"]/1000:.6f} | {v["gain_percent"]:.4f}% | {v["A_range_ms"]/1000:.6f} | {v["B_range_ms"]/1000:.6f} |\n'
        ci=verdict['paired_95percent_CI_ms']
        report+=f'\n八次总体均值：A {verdict["A_mean_ms"]/1000:.6f}s，B {verdict["B_mean_ms"]/1000:.6f}s，下降 {verdict["gain_percent"]:.4f}%。四对A−B的95%配对t区间（df=3）：[{ci[0]/1000:.6f}, {ci[1]/1000:.6f}]s。\n'
        report+='\n预定通过条件：ABBA、BAAB两组均为正收益，并且四对差值95%区间下界>0。固定次数/次序，读盘不排除样本，不删样本、不追加。'+('本轮通过。' if verdict['performance_pass'] else '本轮未可靠测出净收益，关闭这次变体的性能实验；保留数值证据，不追加测试。')+'\n'
    else:report+='\n原失败/停止原因：\n```json\n'+json.dumps(verdict,ensure_ascii=False,indent=2)+'\n```\n未进入预定八次有效预定对照，不能据此评价提速。保留原失败，不补跑请求。\n'
    report+='\n普通PS与原七DMA安全释放、稳定Overlay恢复：'+str(r.get('safe_buffers_released'))+'/'+str(r.get('stable_overlay_reloaded'))+'。稳定恢复未提交PL事务，初始DMASR0不是已完成DMA空闲证明。\n\n这是该固定输入包含自然I/O的请求结论，不证明独立标注准确率、24层适用性或生产服务准入。旧性能结论保持，本轮只评价M441增量收益，不相加。\n'
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_complete_request_closure',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],build_id='0x4D343431',performance_pass=result['performance_pass'],temperature_measurement_enabled=False,production_promoted=False),f'## M441 同视觉完整请求裁决（2026-10-09）\n\nSHA {sha(out)}，raw {e["sha256"]}保留；{result["status"]}，完成{len(samples)}次/正式{result["formal_requests"]}次，不测温。完整请求收益{result["performance_pass"]}；原完整数值证据及七DMA释放/稳定恢复核对，不新增样本、层或生产晋级。详见同目录REPORT。')
    print('M437_CLOSURE_SYNC',sha(out),result['status']);print(json.dumps(verdict,ensure_ascii=False))
if __name__=='__main__':main()
