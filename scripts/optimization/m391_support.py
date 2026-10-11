"""Freeze CPU runner/control/recovery checks; synthetic metadata, no board."""
import base64
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m391_collect import PKG,decode,statistics
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def envelope(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M391_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM391_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M391_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M391_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'

def collector_tests():
    e=json.loads((PKG/'INPUT_IDENTITY.json').read_text(encoding='utf-8'))
    rows=[dict(round=r,position=i,variant=k,calls=6,total_ns=600 if k=='A' else 300,ns_per_call=100.0 if k=='A' else 50.0) for r in range(6) for i,k in enumerate('ABBABAAB')]
    groups,criteria,passed=statistics(rows)
    r=dict(status='PASS_M391_CPU_MEASUREMENTS',gate_level='CPU-only-real159-SiLU-workspace',build_id='0x4D333537',gate_return_code=0,errors=[],
           manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),numerical_pass=True,workspace_object_and_buffer_released=True,
           capture_raw_sha256=e['capture_raw_sha256'],input_tensors={n:e['fixtures'][n]['tensor'] for n in ('gate','up')},
           input_file_identities={n:[1,2,e['fixtures'][n]['file_bytes'],4,5,6,1] for n in ('gate','up')},
           warmup_calls_each=4,planned_rounds=6,calls_per_batch=6,planned_order='ABBABAAB',workspace_bytes=6187008,
           elapsed_s=1,environment=dict(euid=0,uname=['Linux']),output_sha256='a'*64,batches=rows,groups=groups,
           performance_criteria=criteria,component_performance_pass=passed,memory=[{}]*9,workspace_create_ns=1,workspace_close_ns=1)
    scope=('overlay_loaded','model_forward_calls','fpga_transactions','production_changed','full_request_performance_pass','formal_promotion_allowed','memory_capacity_proven','default_enabled','cache_eviction')
    for k in scope:r[k]=False
    assert decode(envelope(r))[2]==r
    failure=dict(r,status='FAIL_M391_CPU_COMPONENT',gate_return_code=1,errors=['SYNTHETIC_FAULT'])
    assert decode(envelope(failure))[2]==failure
    bad=[]
    edits=[(k,True) for k in scope]+[('gate_level','wrong'),('manifest_sha256','0'*64),('build_id','0'),('gate_return_code',True),('errors',['bad']),('numerical_pass',False),('workspace_object_and_buffer_released',False),('capture_raw_sha256','0'*64),('input_tensors',{}),('input_file_identities',{}),('warmup_calls_each',3),('planned_rounds',5),('calls_per_batch',5),('planned_order','ABABABAB'),('workspace_bytes',1),('elapsed_s',61),('environment',dict(euid=0,uname=['Windows'])),('output_sha256','bad'),('batches',rows[:-1]),('groups',groups[:-1]),('performance_criteria',{}),('component_performance_pass',False),('memory',[]),('workspace_create_ns',-1)]
    for k,v in edits:q=copy.deepcopy(r);q[k]=v;bad.append(envelope(q))
    for name in ('order','duration','call_average','identity','false_gain'):
        q=copy.deepcopy(r)
        if name=='order':q['batches'][0]['position']=1
        elif name=='duration':q['batches'][0]['total_ns']=0
        elif name=='call_average':q['batches'][0]['ns_per_call']=1
        elif name=='identity':q['input_file_identities']['gate'][2]=1
        elif name=='false_gain':q['groups'][0]['gain_ns']+=1
        bad.append(envelope(q))
    text=envelope(r);chunks=[l for l in text.splitlines(True) if 'RESULT_CHUNK=' in l]
    bad.extend([text.replace(chunks[1],''),text+chunks[0],text.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),text.replace('export_rc=0','export_rc=1'),text+'M391_RESULT_SHA256='+'0'*64])
    for text in bad:
        try:decode(text)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid recovery accepted')
    return len(bad)

def main():
    assert sha(HERE/'m391_silu_gate.py')==sha(PKG/'m391_silu_gate.py')
    p=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m391_gate.py')],capture_output=True,text=True,encoding='utf-8')
    log=ROOT/'tmp/m391/support_tests.log';atomic(log,(p.stdout+p.stderr).encode('utf-8'),immutable=True)
    assert p.returncode==0 and 'Ran 6 tests' in p.stderr and p.stderr.rstrip().endswith('OK')
    count=collector_tests()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m391_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M391_CONTROL_SELF_TEST_PASS' in p.stdout
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m391_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files']]
    assert all(sha(PKG/r['path'])==r['sha256'] for r in m['files'])
    names=['m391_support.py','m391_control.ps1','m391_collect.py','m391_workflow.py','test_m391_gate.py']
    value=dict(status='PASS_OFFLINE_M391_ACTUAL_RUNNER_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_runner_tests=6,
               collector_negative_checks=count,control_failure_collection=True,actual_PS_list=True,
               source_sha256={n:sha(HERE/n) for n in names},test_log_sha256=sha(log),
               synthetic_arrays_memory_platform_MMIO_explicit=True,board_run=False,performance_pass=False,
               rejected_draft_tests='Windows geteuid outside mock and fixture negative reached earlier capture-scope check; test harness repaired before package freeze; runner unchanged')
    out=BASE/'runs/M391-cpu-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m391_silu_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=d),
         f'## M391 CPU实际入口/回收支持（2026-10-04）\n\n6项真实冻结入口/数学/48批次/释放/默认关闭/文件拒绝检查、{count}严格回收负例、真实PS选择与故意失败仍收集；SHA {d}。Windows自有合成数组及平台/内存替身明确，无板端或真实输入性能证据。首次测试两处测试适配错误保留说明，runner未改变；下一步一次CPU-only真实gate/up测量，已有result只能收集。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
