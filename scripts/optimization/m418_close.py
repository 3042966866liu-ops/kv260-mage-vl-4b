"""Close two successful visual lower gates without replaying hardware."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());records=[]
    for mode in ('descriptor','chain'):
        e=board['latest_m418_visual_'+mode];p=ROOT/e['result'];assert sha(p)==e['sha256'];r=json.loads(p.read_bytes())
        assert r['status']=='PASS_M418_'+mode.upper() and r['gate_return_code']==0 and r['numerical_pass'] and r['safe_buffers_released'] and r['stable_restored']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        records.append(dict(mode=mode,raw_sha256=e['sha256'],result=e['result'],input_bytes=r['transactions'][1]['input_bytes'],full_output_bytes=r['transactions'][1]['output_bytes'],device_observation_ms_diagnostic_only=r['transactions'][1]['wait_ns']/1e6,allocations=len(r['allocations']),releases=len(r['releases']),minimum_actual_CmaFree_MiB=min(x['CmaFree'] for x in r['memory'])/(1<<20)))
    p=BASE/'runs/M418-visual-lower-gates-closure-01/RESULT.json';v=dict(status='CLOSED_M418_VISUAL_DESCRIPTOR_AND_CHAIN_PASS',build_id='0x4D333537',stable_restored_build='0x4D395832',records=records,complete_MLP_performance_proven=False,semantic_quality_proven=False,expanded_24_layers=False,next_step='One full saved-input MLP numerical check, then predeclared CPU/PL warmup and ABBABAAB8 complete-segment comparison; no24 until both quality/net-time/release/sync.')
    atomic(p,encoded(v),immutable=True)
    report='# M418 视觉最小硬件门禁闭合\n\n两门禁完整wire输出与M417精确软件参考逐字节一致；仅第13层首32行，非完整MLP或性能结论。每门禁先在同Overlay合法minimal，再视觉事务，末尾稳定恢复。每门禁18块分配逆序18块释放。\n\n'+json.dumps(records,ensure_ascii=False,indent=2)+'\n\n下一步只准备完整392行fc1→原GELU→fc2数值与包括所有PS/PL开销的完整段比较，不扩大24层。\n'
    atomic(p.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m418_visual_lower_closure',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=v['build_id']),
        f'## M418 视觉两级最小门禁闭合（2026-10-06）\n\nSHA {sha(p)}；fc2单descriptor raw {records[0]["raw_sha256"]}及fc1双descriptor链raw {records[1]["raw_sha256"]}完整wire一致，两个门禁各18块安全释放、稳定恢复。只首32行局部硬件数值，不是完整MLP/性能/语义或24层。下一步原392行完整MLP数值后预定warmup+ABBABAAB8完整段净耗时，含权重准备/量化/传输/解析/GELU/bias。')
    print('M418_CLOSED',sha(p))
if __name__=='__main__':main()
