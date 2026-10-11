"""Strict single candidate recovery, then independent full-trace attribution."""
import json
import base64
import copy
import hashlib
from pathlib import Path
import sys
import types
import m351_workflow as w
from m371_profile_summary import unpack,summarize,pack

PKG=w.BASE/'candidates/M371-candidate-prefill-profile-01'


def prior_validator():
    source=(w.HERE/'m369_collect.py').read_text(encoding='utf-8')
    source=source[:source.index('\ndef collect(')]
    source=source.replace('M369','M371').replace('m369','m371')
    source=source.replace('M371-light-video-01','M371-candidate-prefill-profile-01')
    source=source.replace('balanced-fixed159-video-light-performance','candidate-fixed159-prefill-cost-diagnostic')
    source=source.replace('PASS_M371_LIGHT_VIDEO_MEASUREMENTS','PASS_M371_CANDIDATE_PROFILE')
    source=source.replace('ABBABAAB','B').replace("len(r['samples'])!=8","len(r['samples'])!=1").replace("r['model_forward_calls']!=8","r['model_forward_calls']!=1").replace("r['vision_forward_calls']!=9","r['vision_forward_calls']!=2")
    source=source.replace('all8_requests_completed','bounded_request_completed')
    env=dict(__name__='m371_prior_single_validator');exec(compile(source,'<pinned-m369-single-collector>','exec'),env)
    return env


def decode(log):
    digest,raw,r=prior_validator()['decode'](log)
    if r['status']=='PASS_M371_CANDIDATE_PROFILE':
        report,trace_raw=unpack(r['packed_prefill_trace'])
        summary=summarize(report)
        if summary!=r['candidate_prefill_profile']:raise RuntimeError('Recomputed profile differs')
        sample=r['samples'][0];c=summary['counter_delta']
        if r['build_id']!='0x4D333537' or r['worker_started']:raise RuntimeError('Candidate/prefetch scope')
        for source,target in [('host_calls','host_calls'),('logical_calls','logical_calls'),('stage_bytes','stage_bytes'),('scale_retry_count','retry_count')]:
            if c[source]!=sample['counts'][target]:raise RuntimeError('Profile counter closure differs')
        if len(summary['language_families'])!=154 or r['fpga_transactions_total']!=782:raise RuntimeError('Fixed159 profile coverage')
        if summary['prefill_s']*1000>sample['timing']['stages_ms']['prefill']+.01:raise RuntimeError('Nested Prefill timer escapes')
    return digest,raw,r


def self_test():
    env=prior_validator();n=env['self_test']()
    r=json.loads((w.BASE/'runs/M369-light-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    s=copy.deepcopy(r['samples'][1]);s['index']=1
    r.update(status='PASS_M371_CANDIDATE_PROFILE',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),
        gate_level='candidate-fixed159-prefill-cost-diagnostic',build_id='0x4D333537',order='B',samples=[s],
        model_forward_calls=1,vision_forward_calls=2,bounded_request_completed=True,fpga_transactions_total=782)
    rows=[dict(id=0,name='prefill_call',thread=1,parent=None,metadata={},start_ns=0,end_ns=155000000,
               inclusive_ns=155000000,exclusive_ns=1000000,failed=False)]
    for i in range(154):rows.append(dict(id=i+1,name='language_family',thread=1,parent=0,
        metadata=dict(layer=i//5,family='explicit-collector-test',input_shape=[159,2560]),
        start_ns=i*1000000,end_ns=(i+1)*1000000,inclusive_ns=1000000,exclusive_ns=1000000,failed=False))
    report=dict(status='RECORDED',input_shape=[159,2560],trace=dict(events=rows),phase_ms_delta={},
        counter_delta=dict(host_calls=781,logical_calls=778,stage_bytes=s['counts']['stage_bytes'],scale_retry_count=3))
    r['packed_prefill_trace']=pack(report);r['candidate_prefill_profile']=summarize(report)
    def export(value):
        raw=w.encoded(value);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M371_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM371_SAVED_GATE_RC=0\n'+''.join(f'M371_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+'M371_DONE case=B1 gate_rc=0 export_rc=0\n'
    assert decode(export(r))[2]==r
    bad=[]
    for key,value in [('build_id','0x4D395832'),('worker_started',True),('fpga_transactions_total',781)]:
        x=copy.deepcopy(r);x[key]=value;bad.append(x)
    x=copy.deepcopy(r);x['candidate_prefill_profile']['main_thread_closure_error_ns']=1;bad.append(x)
    x=copy.deepcopy(r);x['packed_prefill_trace']['raw_sha256']='0'*64;bad.append(x)
    x=copy.deepcopy(r);report2=copy.deepcopy(report);report2['counter_delta']['stage_bytes']-=1
    x['packed_prefill_trace']=pack(report2);x['candidate_prefill_profile']=summarize(report2);bad.append(x)
    for value in bad:
        try:decode(export(value))
        except (RuntimeError,ValueError):pass
        else:raise AssertionError('Invalid candidate PASS accepted')
    return n+len(bad)


def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M371-candidate-profile-board-01'
    w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    if r['status']=='PASS_M371_CANDIDATE_PROFILE':
        report,trace_raw=unpack(r['packed_prefill_trace'])
        w.atomic(out/'PREFILL_TRACE.json',trace_raw,immutable=True)
        s=summarize(report);w.atomic(out/'PROFILE_SUMMARY.json',w.encoded(s),immutable=True)
        text='# M371 候选0x4D333537固定159 Prefill耗时诊断\n\n此为一次带观测的候选请求，不是新的性能对照。设备完成等待包含DMA、DDR、计算与背压；后台各项不得与主线程墙钟直接相加。\n\n| 主线程独占项 | 秒 | Prefill占比 |\n|---|---:|---:|\n'
        for k,v in s['main_exclusive_s'].items():text+=f'|{k}|{v:.6f}|{100*v/s["prefill_s"]:.2f}%|\n'
        text+='\n后台独占耗时（不可相加为请求延迟）：\n\n'+json.dumps(s['background_exclusive_s_do_not_add'],indent=2)+'\n\n完整trace原SHA：`'+r['packed_prefill_trace']['raw_sha256']+'`；BOARD raw：`'+digest+'`。\n\n下一步按候选暴露瓶颈裁决；不默认开启既有预取，不沿用旧稳定占比，不降低准入。\n'
    else:text=f'# M371 候选诊断未完成\n\n状态 {r["status"]}，原rc{r["gate_return_code"]}；只保存原证据，不作耗时裁决。\n\n{json.dumps(r["errors"],ensure_ascii=False)}\n'
    w.atomic(out/'REPORT.md',text.encode('utf-8'),immutable=True)
    w.sync('latest_m371_candidate_profile_board',dict(status=r['status'],sha256=digest,result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),numerical_pass=r['numerical_pass'],performance_pass=False),
        f'## M371 候选版耗时诊断原证据\n\n状态{r["status"]}，原rc{r["gate_return_code"]}，原SHA `{digest}`。一次候选0x4D333537固定159画像，全部输出/事务/释放沿前级门禁；逐线程独占完整trace校验，不是新性能对照。下一步只解释候选暴露成本，已有M369净收益保持，预取/服务/门槛未改变。')
    print(json.dumps(dict(status=r['status'],sha256=digest,profile=r.get('candidate_prefill_profile'),errors=r['errors'])))


if __name__=='__main__':
    if sys.argv[1]=='SelfTest':print(self_test())
    else:collect(sys.argv[1])
