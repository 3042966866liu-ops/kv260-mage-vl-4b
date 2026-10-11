"""Close raw single-layer evidence; do not infer model/video performance."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m374_wait_validation import validate
from m374_collect import decode

def main():
    out=BASE/'runs/M374-layer-wait-board-01';raw=out/'BOARD_RESULT.json'
    r=json.loads(raw.read_text(encoding='utf-8'));digest=sha(raw)
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m374_layer_wait_board']['sha256']==digest
    assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    passed=r['status']=='PASS_M374_SINGLE_LAYER_DIAGNOSTIC'
    attribution=validate(r['future_wait'],r['transactions']) if passed else None
    if passed:assert attribution==r['future_wait_summary']
    result=dict(status='PASS_SINGLE_LAYER_ACTUAL_WAIT_OBSERVED' if passed else 'FAIL_SINGLE_LAYER_WAIT_DIAGNOSTIC_CLOSED',
        build_id='0x4D333537',raw_sha256=digest,gate_return_code=r['gate_return_code'],errors=r['errors'],
        exact_single_layer_numerical_pass=bool(passed and r['numerical_pass']),wait_attribution=attribution,
        logical_calls=r.get('logical_calls'),physical_calls=r.get('host_calls'),total_physical_including_minimal=r.get('fpga_transactions'),
        seven_buffers_bytes=sum(x['bytes'] for x in r['allocated_buffers']),released_buffers=len(r['released_buffers']),
        safe_buffers_released=r.get('safe_buffers_released',False),stable_overlay_reloaded=r.get('stable_overlay_reloaded',False),
        stable_restore_transaction_submitted=r.get('stable_restore_transaction_submitted'),
        sampled_memory=r.get('sampled_memory'),initial_loaded_capacity=r.get('loaded_capacity'),
        ps_prefetch_enabled=False,extra_cma_allocations=0,production_policy_changed=False,memory_capacity_proven=False,
        performance_pass=False,formal_promotion_allowed=False,
        scope='Original layer0 on159 repeated fixed-text embeddings, complete runtime retained. Diagnostic memory/trace overhead included. Not159-video and not ordinary request latency.',
        rejected_attempts=['Offline validator initially required ascending parse tail; actual frozen slot drain128 then96. Corrected validation only before upload; original schedule untouched.'],
        next_step='After successful closure prepare one separate narrow fixed159-video Future wait probe; reuse full numeric reference, avoid M371 broad profile repeat. PS slot admission remains independent.' if passed else 'Remain at single-layer failed level; collect/diagnose existing evidence only before any retry.')
    closure=BASE/'runs/M374-layer-wait-closure-01'
    atomic(closure/'RESULT.json',encoded(result),immutable=True);closed=sha(closure/'RESULT.json')
    if passed:
        summary=attribution['summary'];pack=summary['pack'];parse=summary['parse']
        line=f'诊断层调用{attribution["layer_instrumented_s"]:.6f}s；pack真正等待{pack["condition_wait_s"]:.6f}s/{pack["condition_wait_calls"]}次，parse真正等待{parse["condition_wait_s"]:.6f}s/{parse["condition_wait_calls"]}次；result各25次，主线程trace闭合误差0。'
        table='| family | parse result 总时间/s | 真正 wait/s | 复用边界 wait/s | 结尾 wait/s |\n|---|---:|---:|---:|---:|\n'+''.join(f'| {f} | {v["parse_result_s"]:.6f} | {v["parse_wait_s"]:.6f} | {v["reuse_wait_s"]:.6f} | {v["tail_wait_s"]:.6f} |\n' for f,v in attribution['by_family'].items())
    else:line='本级失败；未解锁后级。'+str(r['errors']);table=''
    note=f'## M374 单层实际等待诊断闭合（2026-10-03）\n\nBuild0x4D333537，{result["status"]}；{line}原25逻辑/物理（另1合法最小）及完整family/hidden/KV数值、七缓冲释放/稳定重载仅以本级原结果为准。生产64MiB、PS预读关闭保持。原SHA {digest}；闭合SHA {closed}。159重复文本embedding层0不是原视频；含观察/内存检查开销，Condition.wait含唤醒调度，result/worker与wait不能叠加，不是新增提速。下一步通过时仅准备原固定159视频窄等待观察，失败留本级。'
    sync('latest_m374_layer_wait_closure',dict(status=result['status'],result=(closure/'RESULT.json').relative_to(ROOT).as_posix(),sha256=closed,raw_sha256=digest,numerical_pass=passed,performance_pass=False),note)
    report='# M374 单层实际解析等待诊断\n\n'+line+'\n\n'+table+'\n'+note+'\n'
    atomic(closure/'REPORT.md',report.encode('utf-8'),immutable=True)
    print(json.dumps(dict(status=result['status'],sha256=closed,attribution=attribution,errors=r['errors'])))

if __name__=='__main__':main()
