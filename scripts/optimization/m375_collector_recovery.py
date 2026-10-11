"""Validate a host-only report-identity correction against saved bytes."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m375_collect import decode,prior_validator

def main():
    out=BASE/'runs/M375-collector-recovery-01'
    original=out/'ORIGINAL_COLLECTOR.py'
    expected='bcae560e98409c39e8a5d6bc99661336a6af8efe49ea5cb3007e5f3999c7e4e5'
    assert sha(original)==expected
    log=(ROOT/'tmp/m375/component_uart.log').read_text(encoding='utf-8-sig')
    digest,raw,r=prior_validator()['decode'](log)
    oldenv={'__name__':'original_collector'}
    exec(compile(original.read_text(encoding='utf-8'),str(original),'exec'),oldenv)
    try:oldenv['decode'](log)
    except ValueError as exc:assert str(exc)=='Wait scope/prerequisite/final marker differs'
    else:raise AssertionError('Original rejection not reproduced')
    assert decode(log)==(digest,raw,r)
    def export(value):
        blob=encoded(value);parts=[blob[i:i+900] for i in range(0,len(blob),900)]
        return ('M375_RESULT_SHA256='+hashlib.sha256(blob).hexdigest()+'\nM375_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+
                ''.join(f'M375_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+
                f'M375_DONE case=B1 gate_rc={value["gate_return_code"]} export_rc=0\n')
    bad=[]
    mutations={
        'single candidate top identity':lambda x:x.update(build_id='0x4D333537'),
        'stable top identity':lambda x:x.update(build_id='0x4D395832'),
        'wrong sample Build':lambda x:x['samples'][0].update(build_id='0x4D395832'),
        'wrong completed hardware Build':lambda x:x['samples'][0]['final_snapshot'].update(ap_return=0x4D395832),
        'wrong numerical logits':lambda x:x['samples'][0]['numeric_sha_after_timer']['logits'].update(sha256='0'*64),
        'wrong prerequisite':lambda x:x.update(wait_prerequisite_sha256='0'*64),
        'extra worker':lambda x:x.update(worker_started=True),
        'PS prefetch':lambda x:x.update(ps_prefetch_enabled=True),
        'bindings retained':lambda x:x.update(wait_bindings_restored=False),
        'missing release':lambda x:x['samples'][0]['released_buffers'].pop(),
        'trace corrupt':lambda x:x['packed_wait_trace'].update(raw_sha256='0'*64),
        'summary fabricated':lambda x:x['video_wait_summary']['by_family']['gate_up'].update(actual_wait_s=999),
        'performance promotion':lambda x:x.update(performance_pass=True),
        'physical count missing':lambda x:x.update(fpga_transactions_total=781),
    }
    for label,mutation in mutations.items():
        value=copy.deepcopy(r);mutation(value)
        try:decode(export(value))
        except (RuntimeError,ValueError):bad.append(label)
        else:raise AssertionError('Invalid recovery accepted: '+label)
    for label,value in [('missing chunk',log.replace('M375_RESULT_CHUNK=0/','M375_MISSING=0/')),
                        ('missing DONE',log.replace('M375_DONE case=B1 gate_rc=0 export_rc=0','M375_DONE_REMOVED')),
                        ('export rc',log.replace('M375_DONE case=B1 gate_rc=0 export_rc=0','M375_DONE case=B1 gate_rc=0 export_rc=1'))]:
        try:decode(value)
        except (RuntimeError,ValueError):bad.append(label)
        else:raise AssertionError('Transport failure accepted: '+label)
    ast.parse((HERE/'m375_collect.py').read_text(encoding='utf-8'),feature_version=(3,10))
    result=dict(status='PASS_HOST_ONLY_COLLECTOR_IDENTITY_RECOVERY',original_collector_sha256=expected,
        corrected_collector_sha256=sha(HERE/'m375_collect.py'),original_log_sha256=sha(ROOT/'tmp/m375/component_uart.log'),
        raw_sha256=digest,original_rejection_reproduced=True,negative_checks=bad,
        hardware_reruns=0,serial_commands=0,board_or_package_changes=0,
        reason='Pinned copied runner reports combined stable/candidate Build; single B sample and completed AP_RETURN remain independently strict',
        historical_support_receipt_unchanged=True)
    atomic(out/'RESULT.json',encoded(result),immutable=True);receipt=sha(out/'RESULT.json')
    sync('latest_m375_collector_recovery',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=receipt,raw_sha256=digest),
        f'## M375 本地回收身份修复（2026-10-03）\n\n原collector错误要求顶层单候选Build，实际冻结runner顶层为稳定/候选组合0x4D395832/0x4D333537。原拒绝离线重现；只改顶层为精确组合，保留样本B候选Build、完成AP_RETURN、原数值/事务/释放/等待检查。原collector SHA {expected}已封存，新SHA {result["corrected_collector_sha256"]}；{len(bad)}项负例通过；原日志SHA {result["original_log_sha256"]}，原结果SHA {digest}，修复证据SHA {receipt}。0硬件重跑/串口命令/板端或包改动，历史support冻结记录保留。下一步仅从原日志回收、同步并裁决等待。')
    print(json.dumps(dict(status=result['status'],sha256=receipt,negative_checks=len(bad),raw_sha256=digest)))

if __name__=='__main__':main()
