"""Interpret immutable narrow I/O evidence; no board actions or performance verdict."""
import json
from collections import defaultdict

from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m435_io_observer import residency_change
from m436_workflow02 import check


def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    source=board['latest_m436_IO_board']
    path=ROOT/source['result']
    assert sha(path)==source['sha256']
    r=check(json.loads(path.read_bytes()))
    obs=r.get('read_observation',{})
    request_ids=sorted({x['request'] for x in obs.get('reads',[])}|{x['request'] for x in obs.get('snapshots',[])})
    samples={x['index']:x for x in r.get('samples',[])}
    requests=[]
    for n in request_ids:
        sample=samples.get(n,{})
        groups={}
        files={}
        for row in (x for x in obs.get('reads',[]) if x['request']==n):
            for target,key in ((groups,row['group']),(files,row['path'])):
                total=target.setdefault(key,dict(calls=0,returned_bytes=0,process_read_bytes=0,elapsed_ns_diagnostic=0,major_faults=0))
                total['calls']+=1
                total['returned_bytes']+=row['returned_bytes']
                total['process_read_bytes']+=row['io']['read_bytes']
                total['elapsed_ns_diagnostic']+=row['elapsed_ns_diagnostic']
                total['major_faults']+=row['major']
        for table in (groups,files):
            for value in table.values():
                value['returned_MiB']=value['returned_bytes']/(1<<20)
                value['process_read_MiB']=value['process_read_bytes']/(1<<20)
                value['elapsed_s_diagnostic']=value['elapsed_ns_diagnostic']/1e9
        snaps=[x for x in obs.get('snapshots',[]) if x['request']==n]
        residency=[]
        transitions=[]
        for snap in snaps:
            totals={}
            for f in snap['files']:
                value=totals.setdefault(f['group'],dict(resident_pages=0,total_pages=0))
                value['resident_pages']+=f['resident_pages'];value['total_pages']+=f['pages']
            residency.append(dict(label=snap['label'],groups=totals,counters=snap['counters']))
        for a,b in zip(snaps,snaps[1:]):
            assert [f['path'] for f in a['files']]==[f['path'] for f in b['files']]
            totals={}
            for x,y in zip(a['files'],b['files']):
                changed=residency_change(x,y)
                value=totals.setdefault(x['group'],dict(lost_pages=0,gained_pages=0,page_bytes=changed['page_bytes']))
                value['lost_pages']+=changed['lost_pages'];value['gained_pages']+=changed['gained_pages']
            transitions.append(dict(before=a['label'],after=b['label'],groups=totals))
        staging=sample.get('visual_staging',[])
        requests.append(dict(request=n,completed_and_reference_verified=n in samples,groups=groups,per_file=files,
            complete_stream_io_delta=sample.get('io_delta'),phase_IO=sample.get('phase_IO'),
            major_fault_delta=sample.get('major_fault_delta'),residency=residency,transitions=transitions,
            before_cache=sample.get('before_cache'),after_cache=sample.get('after_cache'),
            before_memory=sample.get('before_memory'),after_memory=sample.get('after_memory'),
            visual_staging_bytes=sum(x['bytes'] for x in staging),visual_staging_elapsed_s_diagnostic=sum(x['elapsed_ns'] for x in staging)/1e9,
            timing_diagnostic_not_performance=sample.get('timing')))
    between_requests=[]
    snapshots=obs.get('snapshots',[])
    prior=next((s for s in snapshots if s['request']==1 and s['label']=='after-language'),None)
    following=next((s for s in snapshots if s['request']==2 and s['label']=='before-request'),None)
    if prior is not None and following is not None:
        assert [f['path'] for f in prior['files']]==[f['path'] for f in following['files']]
        for a,b in zip(prior['files'],following['files']):
            between_requests.append(dict(group=a['group'],path=a['path'],**residency_change(a,b)))
    passed=r['gate_return_code']==0 and r['numerical_pass'] and len(samples)==2
    second=next((x for x in requests if x['request']==2),None)
    second_weight_read=bool(second and any(x['process_read_bytes']>0 for k,x in second['groups'].items() if k in ('language','head')))
    visual_zero=bool(passed and all(x['groups']['visual']['process_read_bytes']==0 for x in requests))
    if not passed:
        conclusion='未闭合两次完整请求，只解读保留的观察；停在实际失败级。'
        next_step='根据原始失败排查本级；回收问题只补取保存字节，不重跑硬件。'
    elif second_weight_read:
        conclusion='同一完整 runtime 驻留时，第二请求的语言／LM head 读取窗口仍出现进程 read_bytes。这两次观察不支持“读盘仅发生在首次校验”的解释；不能外推无限期稳态，也不能证明具体磁盘扇区或驱逐原因。'
        next_step='事先冻结一项有固定终点的完整请求对照，正式样本全部保留并包含自然请求 I/O；新协议取消全缓存准入假设，旧 M433 裁决不改。'
    else:
        conclusion='第二请求的语言／LM head 观察窗口未出现正的进程 read_bytes。只有两次请求证据，不能证明长期保持全缓存。'
        next_step='根据这两次观察，先规定固定预热条件，再准备新性能对照；旧裁决不改。'
    interpretation=dict(status='CLOSED_M436_TWO_REQUEST_IO_DIAGNOSTIC_PASS' if passed else 'CLOSED_M436_FAILED_IO_DIAGNOSTIC',
        source_result=source['result'],source_sha256=source['sha256'],manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],
        observed_requests=len(requests),verified_requests=len(samples),numerical_pass=bool(passed),performance_pass=False,
        temperature_measurement_enabled=False,requests=requests,between_requests_residency=between_requests,second_request_language_head_storage_read_observed=second_weight_read,
        visual_staging_windows_zero_storage_read_bytes_in_both=visual_zero,conclusion=conclusion,next_step=next_step,
        lifecycle=dict(original_dma_allocations=len(r['allocated_buffers']),original_dma_releases=len(r['released_buffers']),
                       additional_dma=r.get('borrowed_extra_DMA'),safe_buffers_released=r.get('safe_buffers_released'),
                       visual_provider_disposed=r.get('visual_provider_disposed'),io_hooks_restored=r.get('io_observer_hooks_restored'),
                       stable_overlay_reloaded=r.get('stable_overlay_reloaded'),unsafe_buffers_retained=r.get('unsafe_buffers_retained')),
        limits=['All timings include the diagnostic observer and are not performance samples.',
                'Process read_bytes can include filesystem readahead; per-window attribution is not a storage-sector trace.',
                'Unlocked mincore snapshots show residency changes and temporal correlation, not the identity of an eviction cause.',
                'Only two fixed requests in one runtime were prescribed; no extra requests or hardware reruns were added.'])
    output=path.with_name('INTERPRETATION.json');atomic(output,encoded(interpretation),immutable=True)
    report=['# M436 两次固定视频请求的窄 I/O 诊断','',f'原始结果 SHA：`{source["sha256"]}`。',
            f'两次完成并逐位核对：{len(samples)}/2；数值门禁：{passed}。所有计时含观察器开销，不作性能裁决。','',
            '| 请求 | 读取组 | 窗口次数 | 返回字节 MiB | 窗口进程 read_bytes MiB | 观察耗时秒 |',
            '| --- | --- | ---: | ---: | ---: | ---: |']
    for request in requests:
        for group,value in request['groups'].items():
            report.append(f'| {request["request"]} | {group} | {value["calls"]} | {value["returned_MiB"]:.6f} | {value["process_read_MiB"]:.6f} | {value["elapsed_s_diagnostic"]:.6f} |')
    report+=['', '| 请求 | 完整流 read_bytes MiB | 请求前语言驻留页 | 视觉后语言驻留页 | 语言后语言驻留页 |',
             '| --- | ---: | --- | --- | --- |']
    for request in requests:
        delta=request['complete_stream_io_delta'];total='未记录' if delta is None else f'{delta["read_bytes"]/(1<<20):.6f}'
        pages=[]
        for snapshot in request['residency']:
            v=snapshot['groups']['language'];pages.append(f'{v["resident_pages"]}/{v["total_pages"]}')
        report.append(f'| {request["request"]} | {total} | '+ ' | '.join(pages)+' |')
    report+=['','| 请求 | 实际文件 | 窗口进程 read_bytes MiB |','| --- | --- | ---: |']
    for request in requests:
        for name,value in request['per_file'].items():
            report.append(f'| {request["request"]} | {name} | {value["process_read_MiB"]:.6f} |')
    report+=['',conclusion,'',next_step,'',
             f'退出资源：原 DMA 分配/释放 {len(r["allocated_buffers"])}/{len(r["released_buffers"])}；安全释放 {r.get("safe_buffers_released")}；稳定 Overlay 恢复 {r.get("stable_overlay_reloaded")}。',
             '', '完整窗口、逐文件计数、驻留增减、缓存和内存前后数据保存在 `INTERPRETATION.json`。进程 I/O 与快照不能证明扇区来源或具体驱逐原因；未测温。','']
    atomic(path.with_name('IO_REPORT.md'),'\n'.join(report).encode('utf-8'),immutable=True)
    sync('latest_m436_IO_interpretation',dict(status=interpretation['status'],result=output.relative_to(ROOT).as_posix(),sha256=sha(output),raw_sha256=source['sha256'],performance_pass=False),
         f'## M436 两请求窄读盘诊断闭合（2026-10-07）\n\n解释SHA {sha(output)}，raw {source["sha256"]}，实际完整并核对{len(samples)}/2；数值PASS={passed}，性能False。第二请求语言/head窗口仍观察到read_bytes={second_weight_read}，两次视觉暂存窗口read_bytes均0={visual_zero}。固定两次后结束；完整逐文件/驻留/缓存/内存数据见同目录IO_REPORT/INTERPRETATION。原七DMA/稳定恢复与主机严格回收依raw核对，不改旧M433裁决、不测温。下一步：{next_step}')
    print('M436_INTERPRETATION_SYNC',sha(output))
    print(json.dumps(dict(status=interpretation['status'],verified_requests=len(samples),second_request_language_head_read=second_weight_read,requests=[dict(request=x['request'],groups=x['groups'],complete_io=x['complete_stream_io_delta']) for x in requests]),ensure_ascii=False))


if __name__=='__main__':main()
