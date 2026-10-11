"""Independent actual assembly/control and strict saved-byte negative checks.

Collection metadata are explicitly synthetic; only control flow is exercised.
No UART, Overlay or hardware call occurs here.
"""
import base64
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m390_collect import decode,PKG,LEVEL

OLD=BASE/'candidates/M387-ps-video-01'
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def envelope(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return ('M390_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM390_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+
            ''.join(f'M390_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+
            f'M390_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n')

def collection_tests():
    r=json.loads((BASE/'runs/M387-ps-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    e=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    r.update(status='PASS_M390_ACTUAL_GATE_UP_CAPTURE',gate_level=LEVEL,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
             numerical_pass=False,memory_capacity_proven=False,ps_prefetch_enabled=False,boundary_reached=True,
             capture_pass=True,attempted_after_boundary=[],host_calls=20,logical_calls=20,fpga_transactions=21,
             transactions=r['transactions'][:20],events=r['events'][:3],captured_families=e['families'][:4],input=e['input'],
             partial_call_contract=dict(scale_attempts=e['scale_attempts'][:20],scale_retry_count=0,pipeline_retry_launches=0,fused_nonfinite_detections=0),
             actual_gate_up_fixtures={n:dict(tensor=e['families'][3]['output']['model.language_model.layers.0.mlp.'+n+'_proj'],
                                          path='/home/ubuntu/m390_gate_up_capture_01/B1/'+n+'.npy',file_sha256='a'*64,file_bytes=6187136) for n in ('gate','up')})
    assert decode(envelope(r))[2]==r
    failure=dict(r,status='FAIL',gate_return_code=1,errors=['EXPLICIT_SYNTHETIC_FAILURE'])
    assert decode(envelope(failure))[2]==failure
    bad=[]
    for k,v in [('case','A1'),('build_id','0'),('manifest_sha256','0'*64),('numerical_pass',True),('performance_pass',True),
                ('formal_promotion_allowed',True),('memory_capacity_proven',True),('gate_return_code',True),('errors',['error']),
                ('captured_families',e['families'][:5]),('input',{}),('visual_features',{}),('boundary_reached',False),
                ('capture_pass',False),('attempted_after_boundary',['mlp_down']),('model_forward_calls',2),('vision_forward_calls',0),
                ('ps_prefetch_enabled',True),('original_parser_workers',2),('extra_pynq_allocations',1),('host_calls',21),
                ('logical_calls',19),('fpga_transactions',20),('released_buffers',r['allocated_buffers']),('safe_buffers_released',False),
                ('unsafe_buffers_retained',True),('blocked_inference_attempts',['head']),('patch_registry_cleared',False),
                ('stable_overlay_reloaded',False),('boot_unchanged',False),('cmdline_unchanged',False)]:
        q=copy.deepcopy(r);q[k]=v;bad.append(envelope(q))
    for kind in ('transaction','retry','fixture_shape','fixture_path','fixture_sha','fixture_size','extra_event','alloc','final_busy','monitor'):
        q=copy.deepcopy(r)
        if kind=='transaction':q['transactions'][0]['family']='mlp_down'
        elif kind=='retry':q['partial_call_contract']['scale_retry_count']=1
        elif kind=='fixture_shape':q['actual_gate_up_fixtures']['gate']['tensor']['shape']=[30,9728]
        elif kind=='fixture_path':q['actual_gate_up_fixtures']['gate']['path']='/tmp/gate.npy'
        elif kind=='fixture_sha':q['actual_gate_up_fixtures']['gate']['file_sha256']='bad'
        elif kind=='fixture_size':q['actual_gate_up_fixtures']['gate']['file_bytes']=6187008
        elif kind=='extra_event':q['events'].append(['complete',{}])
        elif kind=='alloc':q['allocated_buffers'][0]['bytes']=1
        elif kind=='final_busy':q['final_snapshot']['mm2s_idle']=False
        elif kind=='monitor':q['sampled_memory']['observer_stopped']=False
        bad.append(envelope(q))
    log=envelope(r);lines=log.splitlines(True);chunk_lines=[x for x in lines if 'RESULT_CHUNK=' in x]
    bad.extend([log.replace(chunk_lines[1],''),log+chunk_lines[0],log.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),
                log.replace('M390_RESULT_SHA256=','M390_RESULT_SHA256='+'0'),log.replace('export_rc=0','export_rc=1')])
    for text in bad:
        try:decode(text)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid saved metadata accepted')
    return len(bad)

def assembly_tests():
    spec=importlib.util.spec_from_file_location('actual_m390_assembly',PKG/'m390_assemble.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));prior={r['path']:r for r in old['files']}
    delta=[r['path'] for r in manifest['files'] if prior.get(r['path'])!=r]
    root=ROOT/'tmp/m390/assembly-tests';root.mkdir(parents=True,exist_ok=True)
    cases=['good','old_manifest','source','missing','extra','count','bytes','traversal']
    for case in cases:
        with tempfile.TemporaryDirectory(dir=root) as d:
            base=Path(d).resolve();assert base.parent==root.resolve()
            source=base/'source';target=base/'target';source.mkdir();target.mkdir()
            for p in OLD.iterdir():
                if p.is_file():(source/p.name).write_bytes(p.read_bytes())
            for name in ['PACKAGE_MANIFEST.json']+delta:(target/name).write_bytes((PKG/name).read_bytes())
            m=copy.deepcopy(manifest)
            if case=='old_manifest':(source/'PACKAGE_MANIFEST.json').write_bytes(b'bad')
            elif case=='source':
                name=next(r['path'] for r in manifest['files'] if r['path'] not in delta);(source/name).write_bytes(b'bad')
            elif case=='missing':(target/delta[0]).unlink()
            elif case=='extra':(target/'EXTRA').write_bytes(b'x')
            elif case=='count':m['file_count']+=1
            elif case=='bytes':m['total_bytes']+=1
            elif case=='traversal':m['files'][0]['path']='../escape'
            if m!=manifest:(target/'PACKAGE_MANIFEST.json').write_bytes(encoded(m))
            module.HERE=target;module.OLD=source
            try:module.main(sha(target/'PACKAGE_MANIFEST.json'))
            except RuntimeError:
                if case=='good':raise
            else:
                if case!='good':raise AssertionError('Assembly fault accepted '+case)
                assert all(sha(target/r['path'])==r['sha256'] for r in manifest['files'])
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m390_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    return len(cases)

def main():
    # Actual frozen prefill/stream control and failure boundaries, math/MMIO are explicit substitutes.
    p=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m390_capture.py')],capture_output=True,text=True,encoding='utf-8')
    log=ROOT/'tmp/m390/capture_support_tests.log';atomic(log,(p.stdout+p.stderr).encode('utf-8'),immutable=True)
    assert p.returncode==0 and 'Ran 8 tests' in p.stderr and p.stderr.rstrip().endswith('OK')
    negative=collection_tests();assembly=assembly_tests()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m390_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M390_CONTROL_SELF_TEST_PASS' in p.stdout
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
    assert all(sha(PKG/r['path'])==r['sha256'] and (PKG/r['path']).stat().st_size==r['bytes'] for r in m['files'])
    recovery={n:dict(sha256=sha(ROOT/n),lines=len((ROOT/n).read_text(encoding='utf-8-sig').splitlines())) for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    sources=['m390_support.py','m390_control.ps1','m390_collect.py','m390_workflow.py','test_m390_capture.py','m390_capture_boundary.py']
    value=dict(status='PASS_OFFLINE_M390_CAPTURE_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),capture_control_checks=8,
               collector_negative_checks=negative,actual_assembly_checks=assembly,actual_PS_file_selection=True,failure_always_collected=True,
               test_log_sha256=sha(log),source_sha256={n:sha(HERE/n) for n in sources},recovery=recovery,
               synthetic_metadata_math_MMIO_explicit=True,board_run=False,performance_pass=False,
               rejected_draft_control='List argument array concatenation required parentheses; rejected before upload; frozen package unchanged',
               rejected_test_environment='First default-temp fixture writes refused; tests moved to verified workspace temp; frozen package unchanged')
    out=BASE/'runs/M390-capture-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m390_capture_support',dict(status=value['status'],sha256=d,result=out.relative_to(ROOT).as_posix(),manifest_sha256=value['manifest_sha256']),
         f'## M390 有界捕获控制/回收支持（2026-10-04）\n\n实际冻结prefill/stream退出及8边界检查、{negative}回收负例、{assembly}真实assembly/路径/源SHA检查与实际PS选择/故意失败仍收集通过；SHA {d}。数学/MMIO与回收元数据明确替身，不是新数值/性能。草稿List括号与默认temp权限拒绝均发生在上传前，冻结包不改。人工恢复后同COM3 sudo02为0；下一步仅一次原layer0 gate/up捕获，已有原result/runlog只能Collect。')
    print(json.dumps(value|{'result_sha256':d},ensure_ascii=True))

if __name__=='__main__':main()
