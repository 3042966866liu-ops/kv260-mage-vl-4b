"""Record the actual-source inference separately from unproved causality."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

raw=w.BASE/'runs/M441-complete-request-performance-board-09/BOARD_RESULT.json'
src=w.BASE/'runs/M441-cma-source-only-12/RESULT.json'
r=json.loads(raw.read_bytes());s=json.loads(src.read_bytes())
initial=r['stage_memory'][-1]['cma_counts']
current={}
for row in s['counters']:
    p=row['path'].split('/');current[p[-2]+':'+p[-1]]=int(row['text'].strip())
delta={k:current[k]-initial[k] for k in initial}
bits=[w.BASE/'candidates/M441-record-load-01'/p for p in ('baseline/overlay/m120_m89x2_t32.bit','overlay/m120_m89x2_t32.bit')]
rows=[dict(path=str(p),bytes=p.stat().st_size,sha256=w.sha(p),page_ceiling=(p.stat().st_size+4095)//4096) for p in bits]
value=dict(status='M441_CMA_SOURCE_INFERENCE_NOT_CAUSAL_PROOF14',raw_sha256=w.sha(raw),source_raw_sha256=w.sha(src),initial_counts=initial,later_counts=current,later_counter_delta=delta,
           bits=rows,page_size=s['page_size'],observed_known_post_seal_programs=['first A switch','stable M9 restore'],
           inference='3808 successful allocated pages equals two 1904-page configuration buffers; cumulative count is not live ownership or a leak',
           causal_proof=False,missing='Original after-switch counter and actual kernel allocation/release call stack',
           primary_mechanism_source='https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/fpga/zynqmp-fpga.c',
           primary_source_exact_installed_kernel_identity_proven=False,
           test_gap='Original fake adapter policy.capture was a no-op; actual parent CMA guard was absent from that test',
           original09_not_rerunnable=True,old_correctness_unchanged=True,whole_request_performance_proven=False,next_step='One new14 zero-request trace after sudo renewal')
out=w.BASE/'runs/M441-CMA-source-analysis-14/RESULT.json'
atomic(out,w.encoded(value),immutable=True);sha=w.sha(out)
w.sync('latest_m441_CMA_source_analysis',dict(status=value['status'],result=out.relative_to(w.ROOT).as_posix(),sha256=sha,causal_proof=False),
       f'## M441 CMA入口缺口与源码推断14（2026-10-09）\n\nSHA {sha}；累计申请增3808页恰为两次各1904页编程缓冲，实际PYNQ走FPGA firmware配置。官方Xilinx5.15驱动有dma_alloc_coherent/dma_free_coherent，但不是板端旧失败调用栈证明；旧变化后计数未保存。旧fake adapter未接真实capture造成检查遗漏。原FAIL和0请求保持；新14单次追踪申请/释放/PFN与driver stack，未知申请拒绝及原七owner不放宽。')
npath=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json'
n=json.loads(npath.read_bytes());n.setdefault('stages',{})['cma_diagnostic_authorization_blocked13']=dict(sha256=w.sha(w.BASE/'runs/M441-CMA-authorization-13/RESULT.json'),notified_in_current_chat=True)
atomic(npath,w.encoded(n))
print(sha,delta,rows)
