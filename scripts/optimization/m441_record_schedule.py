"""Inspect actual generated schedule and queues. Not a behavioral RTL test."""
import json
import re
import xml.etree.ElementTree as ET
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    ev=BASE/'runs/M441-record-pipeline-hls-02/RESULT.json';hr=json.loads(ev.read_bytes())
    assert hr['status']=='PASS_M441_HLS_RESOURCE_AND_MAC_GUARD'
    reports=ROOT/'tmp/m441_hls_project_02/hls/syn/report'
    syn=reports.parent/'verilog'
    mac=[]
    for xml in sorted(reports.glob('m441_compute*Pipeline_VITIS_LOOP_106_7_csynth.xml')):
        r=ET.parse(xml).getroot();loop=r.find('PerformanceEstimates/SummaryOfLoopLatency/VITIS_LOOP_106_7')
        assert loop is not None and loop.findtext('TripCount')=='16' and loop.findtext('PipelineII')=='1'
        mac.append(dict(path=xml.relative_to(ROOT).as_posix(),sha256=sha(xml),trip_count=16,II=1,
                        DSP=int(r.findtext('AreaEstimates/Resources/DSP')),pipeline_depth=int(loop.findtext('PipelineDepth')),
                        iteration_process_latency=int(r.findtext('PerformanceEstimates/SummaryOfOverallLatency/Worst-caseLatency'))))
    assert len(mac)==4 and all(r['DSP']==288 for r in mac)
    queues=[]
    for v in sorted(syn.glob('m89x_runtime_kernel_fifo_w128_d34_A*.v')):
        s=v.read_text(encoding='utf-8-sig')
        assert re.search(r'DATA_WIDTH\s*=\s*128',s) and re.search(r'DEPTH\s*=\s*34\)',s)
        queues.append(dict(path=v.relative_to(ROOT).as_posix(),sha256=sha(v),width=128,depth=34))
    assert len(queues)==4
    wrappers=[]
    for v in sorted(syn.glob('m89x_runtime_kernel_m89x_shard*.v')):
        s=v.read_text(encoding='utf-8-sig')
        loaders=re.findall(r'^m89x_runtime_kernel_m441_load_records(?:_\d+)? (m441_load_records(?:_\d+)?_U0)\(',s,re.M)
        consumers=re.findall(r'^m89x_runtime_kernel_m441_compute(?:_\d+)? (m441_compute(?:_\d+)?_U0)\(',s,re.M)
        assert s.count(' records_U(')==1 and len(loaders)==len(consumers)==1
        assert f'assign ap_idle = ({loaders[0]}_ap_idle & {consumers[0]}_ap_idle);' in s
        wrappers.append(dict(path=v.relative_to(ROOT).as_posix(),sha256=sha(v),loader_instance=loaders[0],compute_instance=consumers[0]))
    assert len(wrappers)==4
    old=ROOT/'tmp/m439_hls_project_02/hls/syn/report/m89x_runtime_kernel_csynth.xml'
    oldr=ET.parse(old).getroot();old_resources={r.tag:int(r.text) for r in oldr.find('AreaEstimates/Resources')}
    delta={k:hr['resources'][k]-old_resources[k] for k in hr['resources']}
    assert delta['BRAM_18K']==32 and delta['DSP']==4
    producer=reports/'m441_load_records_csynth.rpt';text=producer.read_text(encoding='utf-8-sig')
    assert 'm441_load_records_Pipeline_VITIS_LOOP_51_3' in text
    r=dict(status='PASS_M441_ACTUAL_MAC_AND_BOUNDED_QUEUE_STATIC_GUARD',build_id=hr['build_id'],
           hls_sha256=sha(ev),mac=mac,queues=queues,wrappers=wrappers,resources=hr['resources'],
           original_M439_resources=old_resources,original_report_sha256=sha(old),resource_delta_vs_M439=delta,
           producer_report_sha256=sha(producer),queue_BRAM_18K_all_shards=32,
           queue_logical_bytes_all_shards=2176,consumer_local_bytes_all_shards=1088,
           static_DATAFLOW_generation=True,RTL_simulated=False,queue_occupancy_proven=False,
           read_compute_overlap_proven=False,burst_observed=False,routed_timing=False,board=False,performance=False,promoted=False,
           next_step='Complete full-size numerical closure, then behavioral RTL prove FIFO34 bounded backpressure/drain and actual AXI/MAC overlap; unchanged source. No shell or board yet.')
    report='''# M441 综合调度与队列静态核对

四个MAC过程均保持16次、II=1、pipeline depth34、288 DSP；只读合成产物检查不是RTL行为证明。

实际生成四个34×128bit FIFO，producer与consumer为独立RTL过程，idle要求二者均idle。四队列逻辑容量2176B、consumer本地记录1088B；HLS映射每队列8个BRAM_18K，共32个。逻辑字节数不能代替物理成本。

本核资源估计188 BRAM_18K、1184 DSP、96430 FF、102762 LUT、64 URAM；相对M439增加32 BRAM、4 DSP、762 FF、732 LUT。DSP增量来自供给组织，并未添加或减少MAC。器件容量内不等于完整shell可布线或满足相同约束，仍需后续路由时序。

尚未证明真实ARLEN、AXI读与MAC同时握手、队列满背压与最终排空，也没有RTL周期或板端收益。下一步在完整真实尺寸数值闭合后做有界RTL观察；不凭DATAFLOW源码或HLS估计推进整壳。
'''
    folder=BASE/'runs/M441-actual-schedule-queue-guard-01'
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True);r['report_sha256']=sha(folder/'REPORT.md')
    dest=folder/'RESULT.json';atomic(dest,encoded(r),immutable=True)
    sync('latest_m441_actual_schedule_queue_guard',dict(status=r['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),build_id=r['build_id'],board=False),
         f'## M441 实际综合调度/队列静态核对（2026-10-07）\n\nSHA {sha(dest)}；四MAC均16次II1/288DSP、实际4个34x128bit队列与读算独立过程。队列占32 BRAM_18K而非按逻辑小容量推测；核188BRAM/1184DSP/102762LUT/64URAM，非整壳时序。尚无队列行为/读算重叠/真实burst/性能，0板端。下一步完整尺寸数值闭合及有界RTL，原M439FAIL不改。')
    print(r['status'],sha(dest),delta)


if __name__=='__main__': main()
