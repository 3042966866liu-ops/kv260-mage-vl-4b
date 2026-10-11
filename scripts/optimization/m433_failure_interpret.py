"""Interpret the existing warm-condition failure; no board calls or extra runs."""
import hashlib,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m433_workflow import check
from board_safety import safe_to_release

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    entry=board['latest_m433_warm_board'];raw=ROOT/entry['result']
    closure=board['latest_m433_warm_closure'];closure_path=ROOT/closure['result']
    assert sha(raw)==entry['sha256'] and sha(closure_path)==closure['sha256']
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        text=(ROOT/name).read_text(encoding='utf-8-sig')
        assert entry['sha256'] in text and closure['sha256'] in text
    r=check(json.loads(raw.read_bytes()))
    assert r['status']=='FAIL' and r['errors']==['WarmConditionsNotEstablished: warm read_bytes limit']
    assert r['experiment_stop']==dict(status='WARM_CONDITIONS_NOT_ESTABLISHED',issues=['warm read_bytes limit'])
    assert len(r['samples'])==3 and not r['formal_samples']
    source=board['latest_m428_saved_language_board'];reference=ROOT/source['result']
    assert sha(reference)==source['sha256'];refs=json.loads(reference.read_bytes())
    rows=[]
    for i,s in enumerate(r['samples']):
        variant=0 if s['variant']=='A' else 1;ref=refs['samples'][variant]
        assert s['index']==i+1 and s['phase']=='warmup' and s['variant']=='ABB'[i]
        assert s['numerical_SHA_after_timer']=={k:ref[k] for k in ('input','visual','token','logits','keys','values')}
        assert all(s['exact_saved_reference'].values()) and s['counts']==ref['counts']
        transactions=refs['transactions'][variant*781:(variant+1)*781]
        digest=hashlib.sha256(json.dumps(transactions,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert digest==s['physical_record_SHA_after_timer']
        assert s['language_physical_observed']==781 and s['visual_physical_observed']==(286 if variant else 0)
        assert safe_to_release(s['final_snapshot']) and s['sampled_memory']['observer_stopped'] is True
        assert s['sampled_memory']['stop_reason'] is None
        assert s['all_visual_bindings_restored'] and s['original_seven_DMA_still_resident']
        rows.append(dict(index=i+1,variant=s['variant'],phase='warmup',total_s=s['timing']['total_ms']/1000,stages_s={k:v/1000 for k,v in s['timing']['stages_ms'].items()},read_bytes=s['io_delta']['read_bytes'],read_MiB=s['io_delta']['read_bytes']/(1<<20),major_faults=s['major_fault_delta'],language_logical=778,language_physical=781,language_retries=3,visual_physical=s['visual_physical_observed'],complete_saved_endpoint_exact=True,language_physical_sequence_exact=True,cache_entries=s['after_cache']['cache_entries'],cache_bytes=s['after_cache']['cache_bytes'],rss_before_MiB=s['before_memory']['process_bytes']['VmRSS']/(1<<20),rss_after_MiB=s['after_memory']['process_bytes']['VmRSS']/(1<<20)))
    assert rows[2]['read_bytes']==52277248 and rows[2]['major_faults']==0
    assert r['fpga_transactions']==2916==1+2343+572
    assert r['allocated_buffers']==list(reversed(r['released_buffers'])) and len(r['released_buffers'])==7
    assert sum(b['bytes'] for b in r['allocated_buffers'])==33484832
    assert safe_to_release(r['final_snapshot']) and r['safe_buffers_released'] and r['stable_overlay_reloaded']
    assert r['unsafe_buffers_retained'] is False and r['stable_restore_transaction_submitted'] is False
    out=BASE/'runs/M433-warm-failure-interpretation-01/RESULT.json'
    result=dict(status='CLOSED_M433_WARM_READ_LIMIT_FAILURE_INTERPRETED',raw_sha256=entry['sha256'],closure_sha256=closure['sha256'],reference_sha256=source['sha256'],source_sha256=sha(HERE/'m433_failure_interpret.py'),samples=rows,formal_requests=0,stopping_request=3,read_limit_bytes=1048576,excess_read_bytes=51228672,completed_three_requests_endpoint_exact=True,overall_numerical_pass=r['numerical_pass'],overall_performance_pass=False,additional_samples_allowed=False,additional_board_calls=0,safe_original_DMA_released=7,stable_overlay_reloaded=True,fpga_transactions=2916,interpretation='Warm-cache eligibility failed after three completed requests, not a numerical or DMA failure. No complete-request gain can be inferred from the three warmups.',missing_metrics=['Per-stage/per-file physical read_bytes attribution','Explicit provider.dispose completion flag on failed path','Post-success boot/cmdline identity flags on failed path'],scope='Original fixed159 input; original CPU visual vs selected13..23 visual MLP PL. Prior M430 visual-only and M432 numerical evidence remain independent.',next_step='Keep M433 closed with no extra samples. Use saved I/O and exact staged-source paths to design a new bounded cache-comparability protocol before any new board run; do not change the M433 limit or delete samples after observing them.',temperature_measurement_enabled=False,production_promoted=False)
    atomic(out,encoded(result),immutable=True)
    report='# M433 暖请求条件失败闭合说明\n\n完整原字节 SHA '+entry['sha256']+'；1105 个有序≤900B分块精确回收。gate_rc=1，export_rc=0。原裁决保持 `CLOSED_M433_WARM_CONDITIONS_NOT_ESTABLISHED`。\n\n'
    report+='|预热|版本|完整请求 s|视觉 s|语言 Prefill s|LM head s（包含于Prefill）|读盘 MiB|major faults|\n|---|---|---:|---:|---:|---:|---:|---:|\n'
    for s in rows:
        t=s['stages_s'];report+=f'|{s["index"]}|{s["variant"]}|{s["total_s"]:.6f}|{t["vision"]:.6f}|{t["prefill"]:.6f}|{t["head"]:.6f}|{s["read_MiB"]:.6f}|{s["major_faults"]}|\n'
    report+='\n第三条预热 B 仍实际读盘 52,277,248 B（49.855469 MiB），超过预先冻结的 1 MiB 上限；major faults 为0，26项66,699,264B视觉缓存和其他暖条件未报错。第四条预热与八条正式请求均未执行。不能把157.76s到110.88s的下降解释成候选提速，也不能据此证明候选无收益。\n\n'
    report+='三条已完成请求的完整视觉特征、语言输入、151936 logits、72份KV和最终判断各自逐位匹配接受的M428参考；全部语言物理序列SHA相同，每条778逻辑/781物理/3重试，两个B各286视觉事务。总2916物理=最小事务1+语言2343+视觉572。整体numerical_pass仍为False，因为整轮未完成；保留既有M432完整数值PASS，不将本次失败改成PASS。\n\n'
    report+='七块原DMA共33,484,832B按原所有者逆序释放；缓冲身份、解析绑定恢复、视觉寄存器缓存失效和完成状态核对，无活动DMA保留。稳定Overlay恢复且没有提交恢复后事务；其初始DMASR0不能称为已完成事务空闲证明。失败发生在正常provider.dispose调用之前，该明确完成标志未记录；最终资源释放由原engine.close负责，不能补写dispose PASS。成功路径末尾的boot/cmdline复核也未执行，注明缺项而不推定为PASS。\n\n'
    report+='本轮只记录进程级完整请求read_bytes，没有按阶段/文件的实际读盘归因。候选每条22次视觉权重暂存合计49,020,928B是逻辑暂存量，不能直接等同第三条52,277,248B实际读盘量；原语言每条暂存2,034,890,752B也不能视为实际磁盘读取。现有记录不足以确认残留读盘属于哪项资产或是否持续发生。\n\n'
    report+='结束M433，不增加预热、正式请求或放宽原判据。若继续完整请求性能，应先根据保存的I/O和真实读取路径冻结新的有界缓存可比性协议，独立编号；不能从本次三条预热拟合阈值。既有M430视觉7.6866%收益和语言40.81%收益保留为各自结论，不相加。没有新增生产准入或扩层；未读取温度。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m433_warm_failure_interpretation',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=entry['sha256'],formal_requests=0,performance_pass=False,additional_samples_allowed=False),f'## M433 暖条件失败细读与资源闭合（2026-10-07）\n\nSHA {sha(out)}，原raw {entry["sha256"]}及裁决{closure["sha256"]}保留。仅预热ABB3条157.763/151.133/110.879s；第3条49.855469MiB实际读盘超过冻结1MiB，未正式对照，不能评价全请求净收益。三条各自完整端点/物理序列接受参考精确，整体未完成不改PASS。2916物理、七原DMA逆序安全释放、稳定Overlay恢复；失败路径dispose与成功后boot/cmdline复核未记录，明确不补造。仅保存字节分析0板端调用，不补样本/改阈值。下一步若继续先冻结新的有界缓存可比性协议，原M430视觉/语言收益独立。详见同目录REPORT。')
    print('M433_FAILURE_INTERPRETATION_SYNC',sha(out))

if __name__=='__main__':main()
