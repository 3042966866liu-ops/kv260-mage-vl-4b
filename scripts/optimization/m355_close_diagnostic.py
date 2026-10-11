"""Interpret the saved diagnostic and synchronize the completed/pause record."""
import json
import re
import sys
sys.dont_write_bytecode=True
import m351_workflow as w
from m355_workflow import RUN
from board_safety import safe_to_release

RAW='34f9dd66a79474f4bdef00dd3d484a4667cba79c57651ad4c1e02c3114cc3765'

def main():
    target=RUN/'INTERPRETATION.json'
    if target.exists():raise RuntimeError('Existing closure; inspect only')
    assert w.sha(RUN/'BOARD_RESULT.json')==RAW
    b=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert b['latest_m355_device_phase_board']['sha256']==RAW
    assert all(RAW in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads((RUN/'BOARD_RESULT.json').read_text(encoding='utf-8'))
    log=(w.ROOT/'tmp/m355/device_phase_uart.log').read_text(encoding='utf-8-sig')
    assert 'M355_DONE gate_rc=0 export_rc=0' in log and '__M355_PHASE_RC_0__' in log
    assert len(re.findall(r'M355_RESULT_CHUNK=\d+/9:',log))==9
    assert not any(x in log for x in ('Exception ignored in:','Traceback (most recent call last):'))
    assert r['status']=='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC' and r['gate_return_code']==0 and not r['errors']
    assert safe_to_release(r['final_snapshot']) and r['final_snapshot']['ap_return']==0x4D395832
    assert r['allocated_buffers'][::-1]==r['released_buffers'] and len(r['released_buffers'])==6
    automation=(__import__('pathlib').Path('D:/CodexHome/automations/kv260/automation.toml')).read_text(encoding='utf-8')
    assert re.search(r'^status\s*=\s*"PAUSED"',automation,re.M)
    rows=[]
    for t in r['transactions']:
        o=t['observation'];start=o['submitted_ns'];events=o['events']
        def interval(k):return [(events[k]['lower_ns']-start)/1e6,(events[k]['upper_ns']-start)/1e6]
        assert t['full_output_exact'] and not o['dma_timing_unresolved']
        rows.append(dict(chain=t['label'],input_completion_interval_ms=interval('mm2s'),kernel_done_interval_ms=interval('ap_done'),output_completion_interval_ms=interval('s2mm'),
            composite_completion_observed_ms=o['wait_ns']/1e6,polls=o['polls'],max_poll_gap_ms=o['max_poll_gap_ns']/1e6,
            done_and_output_same_observation_interval=interval('ap_done')==interval('s2mm'),full_output_sha256=t['output_sha256']))
    result=dict(status='PASS_DEVICE_PHASE_DIAGNOSTIC_CLOSED_PAUSED',build_id='0x4D395832',raw_sha256=RAW,raw_chunks=9,gate_rc=0,export_rc=0,
        transactions=rows,all_full_outputs_exact=True,physical_transactions=4,allocated_bytes=sum(x['bytes'] for x in r['allocated_buffers']),
        buffers_released_once=6,final_snapshot=r['final_snapshot'],minimum_diagnostic_cma_free_bytes=min(x['cma_free_bytes'] for x in r['memory']),
        full_runtime_capacity_proven=False,ps_preread_video_unlocked=False,pure_compute_time_proven=False,performance_pass=False,promoted=False,
        observation='In these four standalone original chains, input DMA completion was observed by 0.408ms; kernel done and output completion were observed together in the final polling interval. Their actual relative order is unresolved; remaining wait includes weight DDR access, arithmetic, merging, output backpressure and polling.',
        automation_status='PAUSED',next_step='Wait for user to resume; no further board run, full model retry or circuit change.')
    w.atomic(target,w.encoded(result),immutable=True);sha=w.sha(target)
    times='、'.join(f"{x['chain']} {x['composite_completion_observed_ms']:.3f}ms" for x in rows)
    note='## M355 设备分段测试完成并暂停（2026-10-02）\n\n稳定Build0x4D395832；四条代表性原chain各一次，'+times+'，4,128,768B完整输出全部匹配原FTZ参考。输入DMA完成观察区间上界均小于0.408ms；AP_DONE与输出DMA均在同一最终轮询区间被观察，真实先后未分辨。其后等待包含权重DDR访问、计算、合并、输出背压和轮询，不能归为纯计算或整视频收益。原rc0/export0，9块严格回收，六块缓冲各安全释放一次，末态AP4/Build返回/两DMA4098无错，无析构异常。仅独立chain诊断，完整runtime未加载；此时CMA不能证明PS预读容量已解决，M352失败及视频数值/性能未解锁。闭合证据 `'+target.relative_to(w.ROOT).as_posix()+'` SHA `'+sha+'`，原始SHA `'+RAW+'`。用户要求测完暂停，kv260实际状态PAUSED已复核；下一步等待用户恢复，不再上板或改电路。稳定源/服务/回滚/boot/DTB/CMA保持。\n\n'
    w.sync('latest_m355_device_phase_closure',dict(status=result['status'],result=target.relative_to(w.ROOT).as_posix(),sha256=sha,raw_sha256=RAW,performance_pass=False,promoted=False,automation_status='PAUSED'),note)
    report=RUN/'REPORT.md';old=report.read_text(encoding='utf-8');w.atomic(report,(old+'\n'+note).encode('utf-8'))
    summary=w.ROOT/'KV260_本轮优化完整工作记录_2026-10-01.md';old=summary.read_text(encoding='utf-8-sig');title,rest=old.split('\n',1)
    table='| 原chain | 输入DMA完成区间/ms | AP_DONE与输出完成观察区间/ms |\n|---|---|---|\n'
    for x in rows:
        a=x['input_completion_interval_ms'];d=x['kernel_done_interval_ms'];table+=f"| {x['chain']} | {a[0]:.3f}–{a[1]:.3f} | {d[0]:.3f}–{d[1]:.3f} |\n"
    w.atomic(summary,(title+'\n\n'+note+table+'\n以下为历史快照；本节更新本次状态。\n\n'+rest.lstrip('\n')).encode('utf-8'))
    assert w.sha(RUN/'BOARD_RESULT.json')==RAW
    print(json.dumps(dict(status=result['status'],raw_sha256=RAW,closure_sha256=sha,transactions=4,automation_status='PAUSED')))

if __name__=='__main__':main()
