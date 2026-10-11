"""Strict saved-byte recovery and independent narrow wait attribution only."""
import json
from pathlib import Path
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m371_profile_summary import unpack
from m375_wait_validation import validate

PKG=BASE/'candidates/M375-video-future-wait-01'

def prior_validator():
    source=(HERE/'m369_collect.py').read_text(encoding='utf-8')
    source=source[:source.index('\ndef collect(')]
    source=source.replace('M369','M375').replace('m369','m375')
    source=source.replace('M375-light-video-01','M375-video-future-wait-01')
    source=source.replace('balanced-fixed159-video-light-performance','fixed159-video-narrow-future-wait')
    source=source.replace('PASS_M375_LIGHT_VIDEO_MEASUREMENTS','PASS_M375_FIXED_VIDEO_WAIT')
    source=source.replace('ABBABAAB','B').replace("len(r['samples'])!=8","len(r['samples'])!=1")
    source=source.replace("r['model_forward_calls']!=8","r['model_forward_calls']!=1").replace("r['vision_forward_calls']!=9","r['vision_forward_calls']!=2")
    source=source.replace('all8_requests_completed','bounded_request_completed')
    env=dict(__name__='m375_prior_single_validator')
    exec(compile(source,'<pinned-m369-single-numeric-collector>','exec'),env)
    return env

def decode(log):
    digest,raw,r=prior_validator()['decode'](log)
    if r['status']=='PASS_M375_FIXED_VIDEO_WAIT':
        # The copied gate declares both overlays at report level.  The pinned
        # prior validator independently requires candidate Build on sample B
        # and on its completed physical transaction; retain all those checks.
        if ('M375_DONE case=B1 gate_rc=0 export_rc=0' not in log or r['build_id']!='0x4D395832/0x4D333537'
            or r['worker_started'] or r.get('ps_prefetch_enabled') is not False or r.get('wait_recovery_error')
            or not r['wait_bindings_restored'] or r['fpga_transactions_total']!=782
            or r['wait_prerequisite_sha256']!='031cf6e2e506f5296998e6e8dfbeba0e87480f41fc07f023aaf3fc6fc79147a2'):
            raise ValueError('Wait scope/prerequisite/final marker differs')
        contract=json.loads((PKG/'WAIT_CONTRACT.json').read_text(encoding='utf-8'))['families']
        report,trace_raw=unpack(r['packed_wait_trace'])
        summary=validate(report,contract)
        if summary!=r['video_wait_summary']:raise ValueError('Recomputed wait summary differs')
        if summary['prefill_instrumented_s']*1000>r['samples'][0]['timing']['stages_ms']['prefill']+.01:
            raise ValueError('Observed Prefill escapes original outer timer')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M375-video-wait-board-01'
    atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    if r['status']=='PASS_M375_FIXED_VIDEO_WAIT':
        report,trace_raw=unpack(r['packed_wait_trace'])
        summary=validate(report,json.loads((PKG/'WAIT_CONTRACT.json').read_text(encoding='utf-8'))['families'])
        atomic(out/'WAIT_TRACE.json',trace_raw,immutable=True)
        atomic(out/'WAIT_SUMMARY.json',encoded(summary),immutable=True)
        total=summary['summary']['parse']['condition_wait_s']
        gate=summary['by_family']['gate_up']['actual_wait_s']
        text=(f'# M375 原固定视频实际解析等待\n\n解析实际等待 {total:.6f}s；gate_up {gate:.6f}s，占解析等待 {100*gate/total if total else 0:.2f}%。缓冲复用 {summary["parse_reuse_wait_s"]:.6f}s，family收尾 {summary["parse_tail_wait_s"]:.6f}s。\n\n'
              '| family | 实际解析等待/s | 复用等待/s | 收尾等待/s |\n|---|---:|---:|---:|\n')
        for name,value in summary['by_family'].items():
            text+=f'|{name}|{value["actual_wait_s"]:.6f}|{value["reuse_wait_s"]:.6f}|{value["tail_wait_s"]:.6f}|\n'
        text+='\nCondition.wait包含唤醒调度，嵌套于result墙钟；同步重试解析及LM head不在此钩子覆盖范围。此次仅诊断，不是新增性能结论。原完整数值、778逻辑/781物理另1minimal、七缓冲释放和稳定恢复均按原collector核对。\n'
    else:
        text=f'# M375 窄等待诊断未通过\n\n原状态{r["status"]}/rc{r["gate_return_code"]}；只保留原字节，不能解读缺失或异常的等待。\n\n{json.dumps(r["errors"],ensure_ascii=False)}\n'
    atomic(out/'REPORT.md',text.encode('utf-8'),immutable=True)
    sync('latest_m375_video_wait_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,
        numerical_pass=r['numerical_pass'],performance_pass=False),
        f'## M375 固定159视频窄等待原证据\n\n候选0x4D333537，状态{r["status"]}/原rc{r["gate_return_code"]}；原字节SHA {digest}。仅一次原视频窄Future观察，完整数值/事务/释放按原门禁；0新增DMA/worker/预读，不重复单层、大画像或旧八次性能。下一步先裁决解析总等待、gate_up来源及复用/收尾；未自动改调度或晋级。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],wait=r.get('video_wait_summary')),ensure_ascii=False))

if __name__=='__main__':collect(sys.argv[1])
